# Ex. 6: Subagente `revisor-codigo`

**Artefato:** [`servico-agendamento/.claude/agents/revisor-codigo.md`](../servico-agendamento/.claude/agents/revisor-codigo.md)

## 1. Frontmatter

```yaml
---
name: revisor-codigo
description: >-
  Revisor de código Python do serviço de agendamento. Use PROATIVAMENTE sempre que o
  desenvolvedor pedir para revisar, auditar ou aprovar código Python (diff, branch, PR, commit
  ou arquivo .py em agendamento/, tests/ ou scripts/) antes de um merge, e logo depois de
  escrever ou alterar código Python. Devolve um parecer com achados por severidade e um
  veredito APROVADO ou MUDANÇAS NECESSÁRIAS. NÃO use para perguntas sobre dados, números de
  ocupação, consultas SQL ou relatórios: isso é do gerador-relatorios.
model: sonnet
effort: medium
tools: Read, Grep, Glob, Bash
disallowedTools: mcp__banco-producao__*, Write, Edit, NotebookEdit, WebFetch, WebSearch, Agent
permissionMode: dontAsk
omitClaudeMd: true
maxTurns: 20
color: orange
---
```

O corpo do arquivo é o system prompt do subagente: o procedimento de revisão, as regras de
negócio do projeto (turnos, conflito `[inicio, fim)`, 24 h de antecedência, LGPD), o formato
do parecer com severidades e os limites (não edita, não acessa produção).

| Campo | Valor | Por quê |
|---|---|---|
| `name` | `revisor-codigo` | Identificador usado em `@agent-revisor-codigo`, em `/revisar-pr` (`agent: revisor-codigo`) e no roteamento automático |
| `description` | gatilho + saída + exclusão | Detalhado no Ex. 7 |
| `model` | `sonnet` | Ver seção 2 |
| `effort` | `medium` | Revisão de um diff pequeno não precisa do esforço máximo. `medium` reduz o raciocínio e o número de turnos sem perder os achados de regra de negócio (ver a demonstração) |
| `tools` | `Read, Grep, Glob, Bash` | **Read/Grep/Glob** para ler o diff **e** o código chamado por ele (`consultas.py`, `turnos.py`). **Bash** para rodar o que a squad usa como critério objetivo: `git diff/show/log`, `ruff`, `pytest` e `scripts/checar_branch.py`. Nada além disso |
| `disallowedTools` | produção, escrita, rede, `Agent` | Um revisor que edita deixa de ser revisor: ele aprovaria o próprio código. Detalhes de isolamento no Ex. 8 |
| `permissionMode` | `dontAsk` | O Bash fica limitado ao que o `settings.json` libera explicitamente (Ex. 8) |
| `maxTurns` | `20` | Teto de custo: uma revisão que não converge em 20 turnos para e devolve resultado parcial |

## 2. Justificativa do modelo

**Escolha: `sonnet`** (nesta máquina, resolve para `claude-sonnet-5-5`, como registram as
transcrições), com `effort: medium`. O agente principal usa o `opus`
(`AG-DPS-CLAUDE-OPUS[1m]`).

| | Agente principal (`opus`, Opus 5.5) | **`revisor-codigo` (`sonnet`, Sonnet 5.5)** | Alternativa descartada (`haiku`, Haiku 5.5) |
|---|---|---|---|
| Preço de tabela (entrada / saída por 1M tokens) | US$ 4 / US$ 20 | **US$ 2 / US$ 10** | US$ 0,10 / US$ 0,50 |
| Tipo de tarefa | Aberta: planejar, implementar, decidir entre arquiteturas, conversas longas | **Delimitada e repetitiva**: um diff + 2 ou 3 arquivos, checklist fixo, formato fixo | Recuperação e resumo |
| Frequência | Uma sessão longa por dia | **A cada PR e a cada alteração de `.py`** (delegação proativa, Ex. 7) | n/a |

Por que **não o mesmo modelo do agente principal**:

1. **A tarefa não pede a profundidade máxima.** A revisão trabalha sobre uma entrada pequena e
   bem delimitada (no teste, 44 linhas de diff) e segue um checklist explícito no system prompt.
   O raciocínio necessário (perceber que `c.inicio == atual` ignora sobreposição parcial, que
   `<= limite` gera um slot às 18:00, que um `print` expõe o CPF) é análise local de código, e o
   Sonnet acerta isso, como mostra a demonstração abaixo.
2. **Custo.** O revisor é acionado proativamente, em toda alteração de Python. Pelo preço de
   tabela, cada token custa **metade** do Opus 5.5. Na execução do teste, o subagente consumiu
   cerca de 14 mil tokens de entrada e 1,7 mil de saída, uma revisão completa de alguns
   centavos de dólar.
3. **Latência.** Na sessão de demonstração, a revisão inteira do subagente (ler o diff, rodar
   ruff e pytest num worktree, ler `consultas.py` e `turnos.py` e escrever o parecer) levou
   **cerca de 13 s** (de 18:27:34 a 18:27:47 na transcrição). Um portão de revisão que responde
   em segundos não trava o merge.
4. **Independência.** Um modelo diferente do que escreveu o código também traz uma
   "segunda opinião" de verdade, porque não repete exatamente os mesmos vieses do autor.

Por que **não o `haiku`**, mais barato ainda: o `haiku` serve bem para "rode um SELECT e
resuma" (é o modelo do `gerador-relatorios`, Ex. 7). Já a revisão exige **raciocinar sobre
regras de negócio que não estão no diff**. Para ver que o encaixe viola o conflito
`[inicio, fim)`, é preciso ler `conflita()` em outro arquivo e comparar com a semântica nova.
Um falso "APROVADO" custa muito mais que a diferença de preço entre os modelos. Se um dia for
preciso um revisor mais profundo para uma mudança arriscada, o desenvolvedor pode pedir
explicitamente (o modelo passado por invocação tem precedência sobre o campo `model`), sem
mudar o padrão.

**Observação sobre o ambiente.** Nesta máquina, o Claude Code fala com um proxy local
(`ANTHROPIC_BASE_URL`) que mapeia os apelidos `opus`, `sonnet` e `haiku` para os modelos
`AG-DPS-CLAUDE-*`. Os valores de custo que o proxy devolve têm `costBasis: unknown`, por isso
a comparação acima usa o **preço de tabela oficial** de cada modelo, e não o custo reportado
pela sessão.

## 3. Demonstração em código real do projeto

**Alvo:** a branch [`feature/encaixe-horarios`](../servico-agendamento/agendamento/) (commit
`55fc9c1`), com o módulo novo `agendamento/encaixe.py` e `tests/test_encaixe.py`. É código
Python real, que importa `Consulta` e `TURNOS` do pacote. Ele passa no `ruff` e no `pytest`,
mas foi escrito de propósito com defeitos típicos de um PR apressado.

**Invocação explícita:** [`ex06-revisor-explicito.md`](evidencias/sessoes/ex06-revisor-explicito.md)

```
@agent-revisor-codigo revise o código Python novo da branch feature/encaixe-horarios
(git diff main...feature/encaixe-horarios) antes do merge.
```

O que a transcrição registra:

- O agente principal chamou `Agent {"subagent_type": "revisor-codigo", ...}`.
- O subagente rodou em `claude-sonnet-5-5`, com as ferramentas `['Read', 'Bash']` (Grep e Glob
  vêm embutidos no Bash nesta versão).
- Chamadas do subagente: `git diff main...feature/encaixe-horarios --stat` e
  `python3 scripts/checar_branch.py feature/encaixe-horarios` (ruff **All checks passed**,
  pytest **6 passed**), seguidas de `git diff ...` e da leitura de `consultas.py` e `turnos.py`.
- `permission_denials: []`.

**Parecer devolvido pelo subagente** (texto da transcrição bruta
[`ex06-revisor-explicito.subagente-1.jsonl`](evidencias/sessoes/ex06-revisor-explicito.subagente-1.jsonl)):

```
## Revisão: git diff main...feature/encaixe-horarios (commit 55fc9c1)
Ferramentas: ruff -> All checks passed | pytest -> 6 passed (via scripts/checar_branch.py)

| # | Severidade | Problema |
| 1 | CRÍTICO | LGPD: o print grava o nome completo e o CPF do paciente. A função nem precisa desses dados. |
| 2 | CRÍTICO | while atual <= limite gera horário no fim do turno (12:00 e 18:00). turno_de usa
                inicio <= h < fim. Uma consulta às 18:00 termina às 18:30. |
| 3 | CRÍTICO | ocupação só por c.inicio == atual: (a) consulta cancelada ainda ocupa o horário;
                (b) início desalinhado (08:15) não bloqueia o slot sobreposto. Viola conflita [inicio, fim). |
| 4 | ALTO    | livres[0] levanta IndexError quando o dia não tem horário livre. |
| 5 | MÉDIO   | Faltam type hints nas funções públicas. |
| 6 | MÉDIO   | Só há o teste do caso feliz, e ele passa CPF e nome completo. |
| 7 | BAIXO   | DURACAO = 30 duplica Consulta.duracao_min. |
| 8 | BAIXO   | Funções públicas sem docstring. |

Veredito: MUDANÇAS NECESSÁRIAS: remover o vazamento de CPF e nome no print (LGPD), corrigir o
limite do turno (<= gera 12:00 e 18:00) e respeitar conflita e o status cancelada ao calcular
horários livres. Ruff e pytest passam, mas os testes não cobrem nenhum desses defeitos.
```

**Os achados conferem com o código.** Lendo `encaixe.py` na branch:

| Achado | Código real |
|---|---|
| 1. LGPD | linha 30: `print(f"Encaixe para {paciente_nome} (CPF {paciente_cpf}): ...")` |
| 2. Fim de turno | linha 18: `while atual <= limite:` |
| 3. Sobreposição e cancelada | linhas 19-21: `any(c.medico_id == medico_id and c.inicio == atual for c in agenda)` |
| 4. `IndexError` | linha 31: `return livres[0]` |

O ponto mais importante: **`ruff` e `pytest` passam**. Uma checagem automática teria aprovado o
PR. O revisor achou os três defeitos críticos porque leu `consultas.py` e `turnos.py`, como
manda o passo 2 do prompt, e comparou com as regras de negócio listadas no system prompt.

**Limitação observada.** Os números de linha do parecer acima (`:36`, `:24`, `:25-27`) estão
deslocados em 6. O subagente numerou a **saída do `git diff`** (com `cat -n`), não o arquivo.
O conteúdo de cada achado está correto, e as execuções do Ex. 7 e do `/revisar-pr` (Ex. 9),
com o mesmo revisor e a mesma branch, citaram as linhas certas (`:30`, `:18`, `:19-21`). O prompt já orienta usar
`git show <branch>:<caminho>` para ler o arquivo. Este caso mostra que vale reforçar isso
numa próxima iteração do revisor.

## 4. Execução anterior mantida

Na primeira execução ([`execucoes-anteriores/ex06-revisor-explicito-v1.md`](evidencias/execucoes-anteriores/ex06-revisor-explicito-v1.md)),
o revisor tentou criar um `git worktree` para rodar os testes na branch, e o
`permissionMode: dontAsk` negou o comando, que era o comportamento correto. A revisão saiu só
por leitura, sem ruff nem pytest. O ajuste foi criar
[`scripts/checar_branch.py`](../servico-agendamento/scripts/checar_branch.py) (worktree
temporário destacado, ruff, pytest e remoção do worktree), liberá-lo no `settings.json` e
citá-lo no prompt do revisor (commit `31ce15e`). O isolamento não foi afrouxado: o revisor
ganhou um caminho estreito e auditável.
