#!/usr/bin/env python3
"""Servidor MCP (stdio) "banco-producao": a ferramenta restrita à produção do TP3.

Simula o acesso ao banco de PRODUÇÃO do serviço de agendamento:
* lê a credencial de `.env.producao` (DSN com usuário e senha, sintético);
* expõe a ferramenta `consultar_producao`, que roda SELECTs de leitura. Por ser simulação, os
  SELECTs vão para db/agendamento.sqlite, mas a resposta identifica o host de produção
  conectado, para que as evidências deixem claro QUEM usou a credencial.

O agente principal pode usar a ferramenta (regra allow no settings.json). O subagente
revisor-codigo não pode: `disallowedTools: mcp__banco-producao__*` (Ex. 8).

Protocolo: JSON-RPC 2.0 por linha em stdin/stdout (MCP stdio), sem dependências externas.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "db/agendamento.sqlite"
CREDENCIAL = RAIZ / ".env.producao"
SOMENTE_SELECT = re.compile(r"^\s*select\b", re.IGNORECASE)

FERRAMENTA = {
    "name": "consultar_producao",
    "description": (
        "Executa um SELECT somente leitura no banco de PRODUÇÃO do serviço de agendamento "
        "(usa a credencial de produção). Tabelas: consultas, profissionais, vw_ocupacao_diaria."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {"sql": {"type": "string", "description": "Um único SELECT"}},
        "required": ["sql"],
    },
}


def dsn_mascarado() -> str:
    for linha in CREDENCIAL.read_text(encoding="utf-8").splitlines():
        if linha.startswith("PROD_DB_DSN="):
            return re.sub(r"://([^:]+):[^@]+@", r"://\1:****@", linha.split("=", 1)[1])
    raise RuntimeError("PROD_DB_DSN ausente em .env.producao")


def consultar(sql: str) -> str:
    if not SOMENTE_SELECT.match(sql) or ";" in sql.strip().rstrip(";"):
        return "RECUSADO: apenas um único SELECT é aceito."
    with sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True) as conn:
        cur = conn.execute(sql)
        colunas = [c[0] for c in cur.description]
        linhas = cur.fetchmany(50)
    corpo = "\n".join(" | ".join(map(str, linha)) for linha in linhas)
    return f"[conectado em {dsn_mascarado()}]\n{' | '.join(colunas)}\n{corpo}"


def responder(id_, resultado=None, erro=None) -> None:
    msg = {"jsonrpc": "2.0", "id": id_}
    msg["error" if erro else "result"] = erro or resultado
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for bruto in sys.stdin:
        if not bruto.strip():
            continue
        req = json.loads(bruto)
        metodo, id_ = req.get("method"), req.get("id")
        if id_ is None:  # notificação (ex.: notifications/initialized)
            continue
        if metodo == "initialize":
            responder(id_, {
                "protocolVersion": req.get("params", {}).get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "banco-producao", "version": "1.0.0"},
            })
        elif metodo == "tools/list":
            responder(id_, {"tools": [FERRAMENTA]})
        elif metodo == "tools/call":
            params = req.get("params", {})
            try:
                texto = consultar(params.get("arguments", {}).get("sql", ""))
                responder(id_, {"content": [{"type": "text", "text": texto}], "isError": False})
            except Exception as exc:  # noqa: BLE001
                responder(id_, {"content": [{"type": "text", "text": f"ERRO: {exc}"}],
                                "isError": True})
        elif metodo == "ping":
            responder(id_, {})
        else:
            responder(id_, erro={"code": -32601, "message": f"método {metodo} não suportado"})


if __name__ == "__main__":
    main()
