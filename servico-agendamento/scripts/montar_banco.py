#!/usr/bin/env python3
"""Monta o banco local db/agendamento.sqlite a partir das migrations reais e dos CSVs.

Aplica, em ordem, todos os arquivos de db/migrations/ (as mesmas migrations do TP2, mais as
do TP3) e carrega dados/*.csv e dados-sensiveis/pacientes.csv. Recria o arquivo do zero.

Uso: python3 scripts/montar_banco.py
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "db/agendamento.sqlite"

CARGAS = {
    "profissionais": RAIZ / "dados/profissionais.csv",
    "consultas": RAIZ / "dados/consultas.csv",
    "pacientes": RAIZ / "dados-sensiveis/pacientes.csv",
}


def main() -> None:
    BANCO.unlink(missing_ok=True)
    conn = sqlite3.connect(BANCO)
    for migration in sorted((RAIZ / "db/migrations").glob("migration_*.sql")):
        conn.executescript(migration.read_text(encoding="utf-8"))
        print(f"aplicada {migration.name}")
    for tabela, arquivo in CARGAS.items():
        with arquivo.open(encoding="utf-8") as arq:
            linhas = list(csv.reader(arq, delimiter=";"))
        cabecalho, dados = linhas[0], linhas[1:]
        marcadores = ", ".join("?" * len(cabecalho))
        conn.executemany(
            f"INSERT INTO {tabela} ({', '.join(cabecalho)}) VALUES ({marcadores})", dados
        )
        print(f"{tabela}: {len(dados)} linhas")
    conn.commit()
    conn.close()
    print(f"banco gravado em {BANCO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
