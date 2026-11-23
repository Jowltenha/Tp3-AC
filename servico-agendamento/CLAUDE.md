# Serviço de agendamento de consultas médicas

Python 3.11+, sem framework. Pacote em `agendamento/`, testes em `tests/` e colocalizados (`agendamento/test_*.py`).

- Testes: `.venv/bin/pytest -q`. Lint: `.venv/bin/ruff check agendamento tests`.
- Banco local (sintético): `python3 scripts/gerar_dados_sinteticos.py && python3 scripts/montar_banco.py` gera `db/agendamento.sqlite` a partir de `db/migrations/`.
- Turnos: `manha` 08h-12h, `tarde` 13h-18h (`agendamento/turnos.py`). Consultas de 30 min.
- `dados-sensiveis/` contém dados pessoais de pacientes. Nunca leia essa pasta diretamente; a exportação só passa pela skill `/exportar-pacientes`, invocada pelo desenvolvedor.
- O servidor MCP `banco-producao` usa a credencial de produção (`.env.producao`). Uso exclusivo do agente principal.

## Skills e subagentes

| Artefato | Tipo | Invocação |
|---|---|---|
| `relatorio-ocupacao` | skill | só pelo desenvolvedor: `/relatorio-ocupacao` |
| `exportar-pacientes` | skill sensível | só pelo desenvolvedor: `/exportar-pacientes` |
| `revisar-pr` | skill | só pelo desenvolvedor: `/revisar-pr`, que delega ao `revisor-codigo` |
| `revisor-codigo` | subagente | automática (pela descrição) ou explícita (`@agent-revisor-codigo`) |
| `gerador-relatorios` | subagente | automática (pela descrição) ou explícita (`@agent-gerador-relatorios`) |
