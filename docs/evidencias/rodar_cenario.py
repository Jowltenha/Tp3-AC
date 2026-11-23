#!/usr/bin/env python3
"""Executa um cenário REAL do Claude Code em modo headless e grava a evidência.

Uso:
  python3 -I docs/evidencias/rodar_cenario.py <nome> "<prompt>" [-- <args extras do claude>]

O cenário roda em servico-agendamento/ (o projeto). Ficam gravados em docs/evidencias/sessoes/:
  <nome>.jsonl             saída stream-json bruta do Claude Code
  <nome>.md                transcrição legível gerada a partir dos arquivos brutos, nunca editada à mão
  <nome>.subagente-N.jsonl transcrição bruta de cada subagente, copiada de
                           ~/.claude/projects/<projeto>/<sessão>/subagents/agent-*.jsonl

O .md também traz, tirados da transcrição de sessão que o próprio Claude Code grava:
  * a lista de skills que o modelo recebeu no contexto (attachment skill_listing);
  * o conteúdo RENDERIZADO da skill (argumentos substituídos e saída da injeção dinâmica);
  * para cada subagente: modelo, a primeira mensagem recebida (prova de que não herdou o
    histórico) e cada chamada de ferramenta e resultado.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROJETO = RAIZ / "servico-agendamento"
SAIDA = Path(__file__).resolve().parent / "sessoes"
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
PASTA_SESSOES = Path.home() / ".claude/projects" / str(PROJETO).replace("/", "-")


def resumir(valor, limite: int = 900) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    return texto if len(texto) <= limite else texto[:limite] + " …[truncado]"


def texto_resultado(bloco: dict) -> str:
    c = bloco.get("content")
    if isinstance(c, list):
        c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
    return str(c)


def bloco_citado(texto: str) -> list[str]:
    return ["````text", texto.rstrip(), "````"]


def eventos(caminho: Path):
    for bruto in caminho.read_text(encoding="utf-8").splitlines():
        try:
            yield json.loads(bruto)
        except json.JSONDecodeError:
            continue


def ferramentas_enviadas(caminho: Path) -> tuple[list[str], list[str]]:
    """Ferramentas que o Claude Code REALMENTE enviou ao modelo na 1ª requisição à API.

    Devolve (ferramentas carregadas, ferramentas adiadas/deferred disponíveis via ToolSearch).
    """
    carregadas: list[str] = []
    adiadas: list[str] = []
    for ev in eventos(caminho):
        if ev.get("type") == "api-request-shape" and not carregadas:
            carregadas = [t.get("name") for t in ev.get("shape", {}).get("tools") or []]
        anexo = ev.get("attachment") or {}
        if anexo.get("type") == "deferred_tools_delta":
            adiadas += anexo.get("addedNames", [])
    return carregadas, adiadas


def secao_ferramentas(rotulo: str, caminho: Path) -> list[str]:
    carregadas, adiadas = ferramentas_enviadas(caminho)
    mcp = [n for n in carregadas + adiadas if n.startswith("mcp__")]
    return [f"**Ferramentas que o Claude Code entregou {rotulo}** (1ª requisição à API):", "",
            f"- carregadas: `{carregadas}`",
            f"- adiadas (disponíveis via ToolSearch): `{adiadas}`",
            f"- ferramentas MCP ao alcance: `{mcp or 'NENHUMA'}`", ""]


def secao_sessao(sessao: Path) -> list[str]:
    linhas: list[str] = secao_ferramentas("ao AGENTE PRINCIPAL", sessao)
    for ev in eventos(sessao):
        anexo = ev.get("attachment") or {}
        if anexo.get("type") == "skill_listing":
            nomes = [l[2:].split(":")[0] for l in anexo.get("content", "").splitlines()
                     if l.startswith("- ")]
            linhas += ["## Skills que o MODELO recebeu no contexto (`skill_listing`)", "",
                       "Somente estas skills tinham a descrição visível ao modelo:", "",
                       ", ".join(f"`{n}`" for n in nomes) or "(nenhuma)", ""]
            break
    for ev in eventos(sessao):
        msg = ev.get("message") or {}
        conteudo = msg.get("content")
        if ev.get("type") == "user" and ev.get("isMeta") and isinstance(conteudo, list):
            texto = "\n".join(b.get("text", "") for b in conteudo if b.get("type") == "text")
            if texto.startswith("Base directory for this skill"):
                linhas += ["## Conteúdo da skill que ENTROU no contexto (renderizado)", "",
                           "Texto exato inserido na conversa depois da substituição dos "
                           "argumentos e da injeção dinâmica:", "", *bloco_citado(texto), ""]
        if ev.get("attachment", {}).get("type") == "command_permissions":
            linhas += [f"- Ferramentas pré-aprovadas pela skill (`command_permissions`): "
                       f"`{ev['attachment'].get('allowedTools')}`", ""]
    return linhas


def secao_subagentes(nome: str, sessao_id: str) -> list[str]:
    pasta = PASTA_SESSOES / sessao_id / "subagents"
    if not pasta.exists():
        return []
    linhas = ["## Subagentes (transcrições próprias, em sessão isolada)", ""]
    for i, arq in enumerate(sorted(pasta.glob("agent-*.jsonl"), key=os.path.getmtime), 1):
        copia = SAIDA / f"{nome}.subagente-{i}.jsonl"
        shutil.copy(arq, copia)
        meta = pasta / arq.name.replace(".jsonl", ".meta.json")
        info = json.loads(meta.read_text()) if meta.exists() else {}
        evs = list(eventos(arq))
        modelos = sorted({(e.get("message") or {}).get("model") for e in evs
                          if e.get("type") == "assistant"} - {None})
        linhas += [f"### Subagente {i}: `{info.get('agentType', '?')}`", "",
                   f"- Transcrição bruta: [`{copia.name}`]({copia.name})",
                   f"- Modelo usado nas respostas: `{', '.join(modelos)}`", "",
                   *secao_ferramentas(f"a este SUBAGENTE ({info.get('agentType', '?')})", arq)]
        primeira = next((e for e in evs if e.get("type") == "user"), None)
        if primeira:
            c = primeira["message"]["content"]
            c = c if isinstance(c, str) else "\n".join(
                b.get("text", "") for b in c if isinstance(b, dict))
            linhas += ["**Primeira (e única) mensagem que o subagente recebeu:** é a mensagem "
                       "de delegação, sem histórico da conversa principal.", "",
                       *bloco_citado(c), ""]
        linhas.append("**Linha do tempo do subagente:**\n")
        for e in evs:
            conteudo = (e.get("message") or {}).get("content")
            if not isinstance(conteudo, list):
                continue
            for b in conteudo:
                if b.get("type") == "tool_use":
                    linhas.append(f"- **chama `{b['name']}`**: `{resumir(b.get('input'), 400)}`")
                elif b.get("type") == "tool_result":
                    rot = "ERRO/BLOQUEIO" if b.get("is_error") else "resultado"
                    linhas.append(f"  - ↳ {rot}: `{resumir(texto_resultado(b), 500)}`")
        linhas.append("")
    return linhas


def main() -> None:
    """Modo normal: roda o cenário. Com --regerar <nome>, só regera o .md a partir dos brutos."""
    if sys.argv[1] == "--regerar":
        nome = sys.argv[2]
        meta = json.loads((SAIDA / f"{nome}.cmd.json").read_text(encoding="utf-8"))
        gerar_md(nome, meta["prompt"], meta["extras"], meta["inicio"], meta["versao"],
                 meta.get("rc", 0), "")
        return
    nome, prompt, *resto = sys.argv[1:]
    extras = resto[1:] if resto[:1] == ["--"] else resto
    SAIDA.mkdir(parents=True, exist_ok=True)
    cmd = [CLAUDE, "-p", prompt, "--output-format", "stream-json", "--verbose", *extras]
    inicio = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    proc = subprocess.run(cmd, cwd=PROJETO, capture_output=True, text=True, timeout=900)
    (SAIDA / f"{nome}.jsonl").write_text(proc.stdout, encoding="utf-8")
    versao = subprocess.run([CLAUDE, "--version"], capture_output=True, text=True).stdout.strip()
    (SAIDA / f"{nome}.cmd.json").write_text(json.dumps(
        {"prompt": prompt, "extras": extras, "inicio": inicio, "versao": versao,
         "rc": proc.returncode}, ensure_ascii=False, indent=2), encoding="utf-8")
    gerar_md(nome, prompt, extras, inicio, versao, proc.returncode, proc.stderr)


def gerar_md(nome, prompt, extras, inicio, versao, rc, stderr) -> None:
    bruto = SAIDA / f"{nome}.jsonl"
    linhas = [
        f"# Sessão `{nome}`", "",
        f"- Data: {inicio}",
        f"- Diretório: `{PROJETO}`",
        f"- Comando: `claude -p \"<prompt>\" --output-format stream-json --verbose {' '.join(extras)}`",
        f"- Claude Code: {versao}",
        f"- Log bruto: [`{nome}.jsonl`]({nome}.jsonl)", "",
        "## Prompt do desenvolvedor", "", *[f"> {l}" for l in prompt.splitlines()], "",
        "## Linha do tempo (sessão principal)", "",
    ]
    final: dict = {}
    for ev in eventos(bruto):
        tipo, sub = ev.get("type"), ev.get("subtype")
        pai = ev.get("parent_tool_use_id")
        prefixo = "  - [subagente] " if pai else "- "
        if tipo == "system" and sub == "init":
            linhas.append(f"- **init**: permissionMode=`{ev.get('permissionMode')}`, "
                          f"model=`{ev.get('model')}`, agents=`{ev.get('agents')}`, "
                          f"mcp_servers=`{ev.get('mcp_servers')}`")
        elif tipo == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    linhas.append(f"{prefixo}**Claude chama `{b['name']}`**: "
                                  f"`{resumir(b.get('input'), 500)}`")
                elif b.get("type") == "text" and b.get("text", "").strip() and not pai:
                    linhas.append(f"{prefixo}**Claude (texto)**: {resumir(b['text'], 500)}")
        elif tipo == "user":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    rot = "ERRO/BLOQUEIO" if b.get("is_error") else "resultado"
                    linhas.append(f"{prefixo}  ↳ {rot}: `{resumir(texto_resultado(b), 600)}`")
        elif tipo == "result":
            final = ev
    sessao_id = final.get("session_id", "")
    sessao = PASTA_SESSOES / f"{sessao_id}.jsonl"
    linhas += ["", *(secao_sessao(sessao) if sessao.exists() else [])]
    linhas += secao_subagentes(nome, sessao_id)
    uso = final.get("usage", {})
    linhas += [
        "## Resposta final do Claude Code", "", final.get("result", "(sem resposta)"), "",
        "## Métricas e negações de permissão", "",
        f"- Turnos: {final.get('num_turns')} | custo: US$ {final.get('total_cost_usd', 0):.4f} | "
        f"tokens de entrada (novos+cache): "
        f"{uso.get('input_tokens', 0) + uso.get('cache_read_input_tokens', 0) + uso.get('cache_creation_input_tokens', 0)}",
        f"- Modelos usados: `{list((final.get('modelUsage') or {}).keys())}`", "",
        "`permission_denials`:", "", "```json",
        json.dumps(final.get("permission_denials", []), ensure_ascii=False, indent=2), "```", "",
    ]
    if rc != 0 and stderr.strip():
        linhas += ["## stderr", "", "```", stderr.strip()[-2000:], "```", ""]
    (SAIDA / f"{nome}.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"{nome}: rc={rc} sessao={sessao_id} "
          f"denials={len(final.get('permission_denials', []))}")


if __name__ == "__main__":
    main()
