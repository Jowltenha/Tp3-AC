#!/usr/bin/env python3
"""Exporta pacientes com consulta num período, com dados pessoais MASCARADOS por padrão (LGPD).

Lê dados-sensiveis/pacientes.csv e db/agendamento.sqlite e grava
exportacoes/pacientes_<inicio>_<fim>.csv. Imprime APENAS um resumo (contagens e caminho):
nenhum nome, CPF ou telefone vai para a saída padrão, que é o que o modelo vê.

Mascaramento: nome -> primeiro nome + iniciais; CPF -> ***.XXX.***-**; telefone -> (**) *****-XXXX.

Uso: exportar.py --inicio AAAA-MM-DD --fim AAAA-MM-DD
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sqlite3
from datetime import date
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[4]
ORIGEM = PROJETO / "dados-sensiveis/pacientes.csv"
BANCO = PROJETO / "db/agendamento.sqlite"
DESTINO = PROJETO / "exportacoes"


def mascarar_nome(nome: str) -> str:
    partes = nome.split()
    return " ".join([partes[0], *(p[0] + "." for p in partes[1:])])


def mascarar_cpf(cpf: str) -> str:
    return f"***.{cpf[4:7]}.***-**"


def mascarar_tel(tel: str) -> str:
    return f"(**) *****-{tel[-4:]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True)
    parser.add_argument("--fim", required=True)
    args = parser.parse_args()
    inicio, fim = date.fromisoformat(args.inicio), date.fromisoformat(args.fim)
    if inicio > fim:
        raise SystemExit(f"período inválido: {inicio} > {fim}")

    with sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True) as conn:
        ids = {r[0] for r in conn.execute(
            "SELECT DISTINCT paciente_id FROM consultas "
            "WHERE date(inicio) BETWEEN ? AND ? AND status <> 'cancelada'",
            [inicio.isoformat(), fim.isoformat()])}
    with ORIGEM.open(encoding="utf-8") as arq:
        pacientes = [p for p in csv.DictReader(arq, delimiter=";") if int(p["id"]) in ids]

    DESTINO.mkdir(exist_ok=True)
    saida = DESTINO / f"pacientes_{inicio}_{fim}.csv"
    with saida.open("w", newline="", encoding="utf-8") as arq:
        w = csv.writer(arq, delimiter=";")
        w.writerow(["id", "nome", "cpf", "telefone", "convenio"])
        for p in pacientes:
            w.writerow([p["id"], mascarar_nome(p["nome"]), mascarar_cpf(p["cpf"]),
                        mascarar_tel(p["telefone"]), p["convenio"]])
    digest = hashlib.sha256(saida.read_bytes()).hexdigest()[:16]
    print(f"Exportação concluída: {len(pacientes)} pacientes com consulta entre {inicio} e {fim}.")
    print(f"Arquivo: {saida.relative_to(PROJETO)} (sha256 {digest}…)")
    print("Campos: id, nome (mascarado), cpf (mascarado), telefone (mascarado), convenio.")


if __name__ == "__main__":
    main()
