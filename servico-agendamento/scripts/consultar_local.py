#!/usr/bin/env python3
"""Executa UM SELECT somente leitura no banco local db/agendamento.sqlite (uso do gerador-relatorios).

Proteções: conexão em mode=ro, um único comando, só SELECT/WITH, e nada que cite a tabela
`pacientes` (dados pessoais ficam fora do alcance do subagente de relatórios).

Uso: python3 scripts/consultar_local.py "SELECT ..."
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

BANCO = Path(__file__).resolve().parents[1] / "db/agendamento.sqlite"


def main() -> None:
    sql = " ".join(sys.argv[1:]).strip().rstrip(";")
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE) or ";" in sql:
        raise SystemExit("RECUSADO: apenas um único SELECT é aceito.")
    if re.search(r"\bpacientes\b", sql, re.IGNORECASE):
        raise SystemExit("RECUSADO: a tabela pacientes contém dados pessoais e não é consultável aqui.")
    with sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True) as conn:
        cur = conn.execute(sql)
        colunas = [c[0] for c in cur.description]
        linhas = cur.fetchmany(200)
    print("| " + " | ".join(colunas) + " |")
    print("|" + "---|" * len(colunas))
    for linha in linhas:
        print("| " + " | ".join(str(v) for v in linha) + " |")
    print(f"\n({len(linhas)} linha(s))")


if __name__ == "__main__":
    main()
