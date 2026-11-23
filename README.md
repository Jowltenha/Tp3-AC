# TP3: Skills e subagentes como contratos de instruções reutilizáveis

**Aluno:** João Pedro Barboza · **Disciplina:** DR3

Comece pelo **[RELATORIO-TECNICO.md](RELATORIO-TECNICO.md)**. Ele resume a solução de cada
exercício e aponta para o documento detalhado e para as evidências reais.

| Exercício | Documento | Artefato | Evidência principal |
|---|---|---|---|
| 1. Controle de invocação | [ex01](docs/ex01-controle-invocacao.md) | [relatorio-ocupacao/SKILL.md](servico-agendamento/.claude/skills/relatorio-ocupacao/SKILL.md) | [modelo não dispara](docs/evidencias/sessoes/ex01-modelo-nao-dispara-relatorio.md) |
| 2. Progressive disclosure | [ex02](docs/ex02-progressive-disclosure.md) | [variacoes/](servico-agendamento/.claude/skills/relatorio-ocupacao/variacoes/) | [básico](docs/evidencias/sessoes/ex02-a-basico-sem-variacoes.md), [especialidade](docs/evidencias/sessoes/ex02-b-especialidade-carrega-variacao.md) |
| 3. Argumentos e injeção | [ex03](docs/ex03-argumentos-injecao.md) | [scripts/dados_ocupacao.py](servico-agendamento/.claude/skills/relatorio-ocupacao/scripts/dados_ocupacao.py) | [só nome](docs/evidencias/sessoes/ex03-a-so-profissional.md), [nome + período](docs/evidencias/sessoes/ex03-b-profissional-e-periodo.md) |
| 4. Implementação | [ex04](docs/ex04-implementacao.md) | [db/](servico-agendamento/db/), [scripts/](servico-agendamento/scripts/) | [execução 1](docs/evidencias/sessoes/ex04-a-basico-periodo-informado.md), [execução 2](docs/evidencias/sessoes/ex04-b-especialidade-alvo-periodo.md), [experimentos](docs/evidencias/execucoes-anteriores/) |
| 5. Skill sensível | [ex05](docs/ex05-skill-sensivel.md) | [exportar-pacientes/SKILL.md](servico-agendamento/.claude/skills/exportar-pacientes/SKILL.md) | [bloqueio](docs/evidencias/sessoes/ex05-b-modelo-forca-skill-tool.md), [explícita](docs/evidencias/sessoes/ex05-c-invocacao-explicita.md) |
| 6. Subagente revisor | [ex06](docs/ex06-subagente-revisor.md) | [revisor-codigo.md](servico-agendamento/.claude/agents/revisor-codigo.md) | [revisão](docs/evidencias/sessoes/ex06-revisor-explicito.md) |
| 7. Seleção automática | [ex07](docs/ex07-selecao-automatica.md) | [gerador-relatorios.md](servico-agendamento/.claude/agents/gerador-relatorios.md) | [revisão](docs/evidencias/sessoes/ex07-a-selecao-auto-revisao.md), [dados](docs/evidencias/sessoes/ex07-b-selecao-auto-dados.md) |
| 8. Isolamento | [ex08](docs/ex08-isolamento.md) | [ops/mcp_banco_producao.py](servico-agendamento/ops/mcp_banco_producao.py) | [principal vs subagente](docs/evidencias/sessoes/ex08-b-mesma-ferramenta-principal-vs-subagente.md) |
| 9. Escopos e delegação | [ex09](docs/ex09-escopos-delegacao.md) | [escopos/](escopos/), [revisar-pr/SKILL.md](servico-agendamento/.claude/skills/revisar-pr/SKILL.md) | [/revisar-pr](docs/evidencias/sessoes/ex09-revisar-pr-delegacao-explicita.md) |

## Estrutura

```
Tp3-AC/
├── RELATORIO-TECNICO.md
├── docs/                              um documento por exercício
│   └── evidencias/
│       ├── rodar_cenario.py           executa um cenário real e gera a transcrição
│       ├── sessoes/                   .jsonl bruto + .md gerado de cada cenário
│       └── execucoes-anteriores/      execuções que motivaram ajustes
├── escopos/                           modelos de subagentes de escopo managed e user
└── servico-agendamento/               o projeto (vindo do TP2)
    ├── CLAUDE.md
    ├── .mcp.json                      servidor banco-producao (Ex. 8)
    ├── .claude/
    │   ├── settings.json
    │   ├── skills/{relatorio-ocupacao,exportar-pacientes,revisar-pr}/
    │   └── agents/{revisor-codigo,gerador-relatorios}.md
    ├── agendamento/  tests/  db/  scripts/  ops/
    ├── dados/                         profissionais e consultas sintéticos
    └── dados-sensiveis/               pacientes sintéticos (formato real)
```

## Reproduzir

```bash
cd servico-agendamento
python3 -m venv .venv && .venv/bin/pip install ruff pytest
.venv/bin/pytest -q                                     # 5 passed (main)
python3 scripts/gerar_dados_sinteticos.py && python3 scripts/montar_banco.py
cp .env.producao.exemplo .env.producao                  # credencial sintética (Ex. 8)
claude                                                  # aceite "Trust this folder" uma vez
```

No Claude Code: `/relatorio-ocupacao especialidade`, `/exportar-pacientes 2026-11-23 2026-11-27`,
`/revisar-pr feature/encaixe-horarios`.

Para repetir um cenário headless:
`python3 -I docs/evidencias/rodar_cenario.py <nome> "<prompt>"`. Para regenerar o `.md` a
partir dos brutos: `python3 -I docs/evidencias/rodar_cenario.py --regerar <nome>`.

A branch `feature/encaixe-horarios` contém de propósito o código com defeitos que o
`revisor-codigo` revisa nos Ex. 6, 7 e 9.
