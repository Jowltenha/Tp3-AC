#!/usr/bin/env python3
"""Coleta os números do relatório de ocupação (somente leitura) e imprime em Markdown.

É chamado pela injeção dinâmica do SKILL.md, ANTES de o conteúdo da skill chegar ao modelo:
a saída deste script substitui o placeholder !`...`. Por isso:

* todo número do relatório é calculado aqui (SQL + Python), nunca pelo modelo;
* o filtro de período é aplicado no SQL (WHERE dia BETWEEN :inicio AND :fim): registros fora
  do intervalo nem chegam ao contexto do Claude Code;
* o script SEMPRE termina com código 0. Um código diferente de zero aborta a invocação inteira
  da skill ("Shell command failed for pattern ..."), e o desenvolvedor ficaria sem a explicação.
  Erros de parâmetro são impressos como um bloco "ERRO DE PARÂMETRO" para o modelo repassar.

Uso (normalmente via skill):
  dados_ocupacao.py --variacao basico|profissional|especialidade
                    [--alvo NOME] [--inicio AAAA-MM-DD] [--fim AAAA-MM-DD]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[4]  # .../servico-agendamento
sys.path.insert(0, str(PROJETO))

from agendamento.turnos import TURNOS, duracao_turno  # noqa: E402  (regra real do projeto)

BANCO = PROJETO / "db/agendamento.sqlite"
SQL_OCUPACAO = PROJETO / "db/consultas/ocupacao_por_medico.sql"
DURACAO_CONSULTA_MIN = 30
VARIACOES = ("basico", "profissional", "especialidade")
DATA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIMIAR_LOTADO, LIMIAR_OCIOSO = 0.85, 0.50
DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


class ErroParametro(Exception):
    pass


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def normalizar_argumentos(args: argparse.Namespace) -> argparse.Namespace:
    """Os argumentos da skill são POSICIONAIS ($variacao $alvo $inicio $fim).

    No relatório básico não existe alvo, então `/relatorio-ocupacao basico 2026-11-16 2026-11-20`
    chega aqui como alvo=2026-11-16, inicio=2026-11-20. Este passo reconhece datas pelo formato,
    em qualquer posição, e o que sobra é o alvo.
    """
    tokens = [t for t in (args.alvo, args.inicio, args.fim) if t and t.strip()]
    datas = [t.strip() for t in tokens if DATA_ISO.match(t.strip())]
    outros = [t.strip() for t in tokens if not DATA_ISO.match(t.strip())]
    if len(outros) > 1:
        raise ErroParametro(f"mais de um alvo informado: {outros}")
    if len(datas) not in (0, 2):
        raise ErroParametro(
            f"intervalo de datas incompleto: {datas}. Informe início E fim (AAAA-MM-DD)."
        )
    args.variacao = (args.variacao or "basico").strip().lower() or "basico"
    if args.variacao not in VARIACOES:
        raise ErroParametro(f"variação '{args.variacao}' inválida. Use uma de: {VARIACOES}")
    args.alvo = outros[0] if outros else None
    if args.alvo and args.variacao == "basico":
        raise ErroParametro("o relatório básico não aceita alvo; use 'profissional' ou 'especialidade'")
    if datas:
        try:
            args.inicio, args.fim = (date.fromisoformat(d) for d in datas)
        except ValueError as exc:
            raise ErroParametro(f"data inválida: {exc}") from exc
        if args.inicio > args.fim:
            raise ErroParametro(f"início {args.inicio} é depois do fim {args.fim}")
        args.periodo_origem = "informado nos argumentos"
    else:
        hoje = date.today()
        args.inicio = hoje - timedelta(days=hoje.weekday())
        args.fim = args.inicio + timedelta(days=4)
        args.periodo_origem = "padrão: semana corrente (segunda a sexta)"
    return args


def dias_uteis(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(d) for d in range((fim - inicio).days + 1)
            if (inicio + timedelta(d)).weekday() < 5]


def rotulo(dia: date) -> str:
    return f"{DIAS_SEMANA[dia.weekday()]} {dia:%d/%m}"


def capacidade_diaria(turnos: str) -> int:
    """Slots de 30 min por dia, usando a duração de turno definida em agendamento/turnos.py."""
    return sum(duracao_turno(t) // DURACAO_CONSULTA_MIN for t in turnos.split(",") if t in TURNOS)


def pct(ocupado: int, capacidade: int) -> str:
    return f"{100 * ocupado / capacidade:.1f}%" if capacidade else "n/a"


def situacao(ocupado: int, capacidade: int) -> str:
    if not capacidade:
        return "sem agenda"
    taxa = ocupado / capacidade
    return "LOTADO" if taxa >= LIMIAR_LOTADO else "OCIOSO" if taxa < LIMIAR_OCIOSO else "normal"


def carregar(conn: sqlite3.Connection, args: argparse.Namespace):
    profissionais = {r[0]: r for r in conn.execute(
        "SELECT id, nome, especialidade, turnos FROM profissionais ORDER BY id")}
    if args.variacao == "profissional" and args.alvo:
        alvo = normalizar(args.alvo)
        profissionais = {k: v for k, v in profissionais.items() if alvo in normalizar(v[1])}
        if not profissionais:
            nomes = [r[0] for r in conn.execute("SELECT nome FROM profissionais ORDER BY nome")]
            raise ErroParametro(f"nenhum profissional corresponde a '{args.alvo}'. Disponíveis: {nomes}")
    if args.variacao == "especialidade" and args.alvo:
        alvo = normalizar(args.alvo)
        profissionais = {k: v for k, v in profissionais.items() if alvo == normalizar(v[2])}
        if not profissionais:
            esp = [r[0] for r in conn.execute(
                "SELECT DISTINCT especialidade FROM profissionais ORDER BY 1")]
            raise ErroParametro(f"especialidade '{args.alvo}' não existe. Disponíveis: {esp}")

    # Filtro do período no SQL: a mesma consulta versionada em db/consultas/.
    ocupacao = defaultdict(int)
    for medico_id, dia, consultas, _minutos in conn.execute(
        SQL_OCUPACAO.read_text(encoding="utf-8"),
        {"inicio": args.inicio.isoformat(), "fim": args.fim.isoformat()},
    ):
        if medico_id in profissionais:
            ocupacao[(medico_id, dia)] += consultas

    marcadores = ",".join("?" * len(profissionais))
    status = defaultdict(lambda: defaultdict(int))
    for medico_id, st, n in conn.execute(
        f"SELECT medico_id, status, COUNT(*) FROM consultas "
        f"WHERE date(inicio) BETWEEN ? AND ? AND medico_id IN ({marcadores}) "
        f"GROUP BY medico_id, status",
        [args.inicio.isoformat(), args.fim.isoformat(), *profissionais],
    ):
        status[medico_id][st] += n
    total_periodo = conn.execute(
        f"SELECT COUNT(*), MIN(date(inicio)), MAX(date(inicio)) FROM consultas "
        f"WHERE date(inicio) BETWEEN ? AND ? AND medico_id IN ({marcadores})",
        [args.inicio.isoformat(), args.fim.isoformat(), *profissionais],
    ).fetchone()
    total_base = conn.execute(
        "SELECT COUNT(*), MIN(date(inicio)), MAX(date(inicio)) FROM consultas").fetchone()
    return profissionais, ocupacao, status, total_periodo, total_base


def tabela(cabecalho: list[str], linhas: list[list]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def bloco_basico(profissionais, ocupacao, dias) -> str:
    linhas, cap_total, ocu_total = [], 0, 0
    for dia in dias:
        cap = sum(capacidade_diaria(p[3]) for p in profissionais.values())
        ocu = sum(ocupacao[(pid, dia.isoformat())] for pid in profissionais)
        cap_total, ocu_total = cap_total + cap, ocu_total + ocu
        linhas.append([rotulo(dia), cap, ocu, cap - ocu, pct(ocu, cap), situacao(ocu, cap)])
    linhas.append(["**Total**", cap_total, ocu_total, cap_total - ocu_total,
                   pct(ocu_total, cap_total), situacao(ocu_total, cap_total)])
    return "### Ocupação por dia (todos os profissionais)\n\n" + tabela(
        ["Dia", "Capacidade (slots)", "Ocupados", "Livres", "Ocupação", "Situação"], linhas)


def bloco_profissional(profissionais, ocupacao, status, dias) -> str:
    resumo, detalhe = [], []
    for pid, nome, esp, turnos in profissionais.values():
        cap = capacidade_diaria(turnos) * len(dias)
        ocu = sum(ocupacao[(pid, d.isoformat())] for d in dias)
        st = status[pid]
        resumo.append([nome, esp, turnos, cap, ocu, pct(ocu, cap), situacao(ocu, cap),
                       st["cancelada"], st["falta"]])
        for d in dias:
            c, o = capacidade_diaria(turnos), ocupacao[(pid, d.isoformat())]
            detalhe.append([nome, rotulo(d), c, o, pct(o, c), situacao(o, c)])
    return (
        "### Ocupação por profissional\n\n"
        + tabela(["Profissional", "Especialidade", "Turnos", "Capacidade", "Ocupados", "Ocupação",
                  "Situação", "Cancelamentos", "Faltas"], resumo)
        + "\n\n### Detalhe diário por profissional\n\n"
        + tabela(["Profissional", "Dia", "Capacidade", "Ocupados", "Ocupação", "Situação"], detalhe)
    )


def bloco_especialidade(profissionais, ocupacao, status, dias) -> str:
    grupos = defaultdict(list)
    for p in profissionais.values():
        grupos[p[2]].append(p)
    linhas = []
    for esp, membros in sorted(grupos.items()):
        cap = sum(capacidade_diaria(p[3]) for p in membros) * len(dias)
        ocu = sum(ocupacao[(p[0], d.isoformat())] for p in membros for d in dias)
        canc = sum(status[p[0]]["cancelada"] for p in membros)
        mais = max(membros, key=lambda p: sum(ocupacao[(p[0], d.isoformat())] for d in dias))
        linhas.append([esp, len(membros), cap, ocu, cap - ocu, pct(ocu, cap), situacao(ocu, cap),
                       canc, mais[1]])
    return "### Ocupação por especialidade\n\n" + tabela(
        ["Especialidade", "Profissionais", "Capacidade", "Ocupados", "Livres", "Ocupação",
         "Situação", "Cancelamentos", "Mais demandado"], linhas)


def main() -> None:
    parser = argparse.ArgumentParser()
    for nome in ("variacao", "alvo", "inicio", "fim"):
        parser.add_argument(f"--{nome}", default="")
    args = parser.parse_args()
    recebido = f"variacao=`{args.variacao}` alvo=`{args.alvo}` inicio=`{args.inicio}` fim=`{args.fim}`"
    print(f"**Argumentos recebidos pela injeção:** {recebido}\n")
    try:
        args = normalizar_argumentos(args)
        if not BANCO.exists():
            raise ErroParametro(f"banco {BANCO.name} não encontrado: rode scripts/montar_banco.py")
        with sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True) as conn:  # somente leitura
            profissionais, ocupacao, status, periodo, base = carregar(conn, args)
    except ErroParametro as exc:
        print(f"ERRO DE PARÂMETRO: {exc}")
        return

    dias = dias_uteis(args.inicio, args.fim)
    print(f"- **Variação:** {args.variacao}")
    print(f"- **Alvo:** {args.alvo or '(todos)'}")
    print(f"- **Período:** {args.inicio:%d/%m/%Y} a {args.fim:%d/%m/%Y} ({args.periodo_origem}), "
          f"{len(dias)} dia(s) úteis")
    print(f"- **Registros na base:** {base[0]} consultas de {base[1]} a {base[2]}")
    print(f"- **Registros considerados (período + recorte):** {periodo[0]} consultas"
          + (f" de {periodo[1]} a {periodo[2]}" if periodo[0] else ""))
    print(f"- **Profissionais no recorte:** {', '.join(p[1] for p in profissionais.values())}")
    print(f"- **Regra:** capacidade = slots de {DURACAO_CONSULTA_MIN} min dos turnos "
          f"(agendamento/turnos.py); 'cancelada' libera o slot; LOTADO >= "
          f"{LIMIAR_LOTADO:.0%}, OCIOSO < {LIMIAR_OCIOSO:.0%}\n")
    if args.variacao == "basico":
        print(bloco_basico(profissionais, ocupacao, dias))
    elif args.variacao == "profissional":
        print(bloco_profissional(profissionais, ocupacao, status, dias))
    else:
        print(bloco_especialidade(profissionais, ocupacao, status, dias))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # nunca derrubar a invocação da skill
        print(f"ERRO INTERNO DO SCRIPT: {type(exc).__name__}: {exc}")
