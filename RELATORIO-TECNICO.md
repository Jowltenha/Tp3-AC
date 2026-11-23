# Relatório Técnico: TP3, Skills e subagentes como contratos de instruções reutilizáveis

**Projeto:** Serviço de Agendamento de Consultas Médicas
**Autor:** João Pedro Barboza
**Ambiente:** Claude Code 2.1.330 (Linux, WSL2), Python 3.14, ruff 0.17.6, pytest
**Data:** 23/11/2026

## Visão geral

Todo o trabalho foi feito sobre **o mesmo serviço de agendamento do TP2**
(`servico-agendamento/`), trazido para este repositório com o código (`agendamento/`), os
testes e as migrations originais. O TP3 acrescentou:

| Tipo | Artefato | Exercícios |
|---|---|---|
| Skill | [`relatorio-ocupacao`](servico-agendamento/.claude/skills/relatorio-ocupacao/SKILL.md) + `variacoes/` + `scripts/` | 1, 2, 3, 4 |
| Skill sensível | [`exportar-pacientes`](servico-agendamento/.claude/skills/exportar-pacientes/SKILL.md) | 5 |
| Skill de delegação | [`revisar-pr`](servico-agendamento/.claude/skills/revisar-pr/SKILL.md) (`context: fork`, `agent: revisor-codigo`) | 9 |
| Subagente | [`revisor-codigo`](servico-agendamento/.claude/agents/revisor-codigo.md) | 6, 7, 8, 9 |
| Subagente | [`gerador-relatorios`](servico-agendamento/.claude/agents/gerador-relatorios.md) | 7, 9 |
| Subagente (modelo de escopo managed) | [`conformidade-seguranca-infnet`](escopos/managed/agents/conformidade-seguranca-infnet.md) | 9 |
| Subagente (modelo de escopo user) | [`explicador-codigo`](escopos/user/agents/explicador-codigo.md) | 9 |
| Dados | 833 consultas sintéticas (semente fixa) em SQLite, montado pelas migrations reais | 4 |
| Recurso restrito | Servidor MCP [`banco-producao`](servico-agendamento/ops/mcp_banco_producao.py) + credencial `.env.producao` | 8 |

**Evidências.** Toda demonstração vem de uma **sessão real** do Claude Code em modo headless
(`claude -p --output-format stream-json --verbose`), conduzida por
[`docs/evidencias/rodar_cenario.py`](docs/evidencias/rodar_cenario.py). Para cada cenário, o
script grava:

- o `.jsonl` bruto do Claude Code;
- um `.md` legível, **gerado** a partir dos brutos e nunca editado à mão. Ele inclui o que o
  próprio Claude Code registra em `~/.claude/projects/...`:
  - a lista de skills visíveis ao modelo (`skill_listing`);
  - o **conteúdo renderizado** de cada skill invocada (argumentos substituídos e saída da
    injeção);
  - as ferramentas pré-aprovadas (`command_permissions`);
  - as **ferramentas entregues** ao agente principal e a cada subagente (`api-request-shape`);
  - a transcrição própria de cada subagente (`subagents/agent-*.jsonl`).

As execuções que revelaram problemas foram **mantidas** em
[`docs/evidencias/execucoes-anteriores/`](docs/evidencias/execucoes-anteriores/), porque elas
justificam decisões (Ex. 4, 6 e 7).

---

## Ex. 1: Controle de invocação ([`docs/ex01-controle-invocacao.md`](docs/ex01-controle-invocacao.md))

**Solução:** `relatorio-ocupacao` com `disable-model-invocation: true`. A justificativa fica em
comentário YAML ao lado do campo. O relatório é um artefato de processo, cujo *momento* é parte
do contrato. A descrição seria um gatilho aproximado demais ("a agenda está cheia?"), e o campo
é aplicado pelo próprio Claude Code, não depende de o modelo seguir uma instrução.
`user-invocable: false` seria o oposto do pedido.

**Cenário do problema:** um pedido de depuração às 10h de sexta dispararia o relatório da
semana parcial. Os números circulariam como oficiais, e a dermatologia, que fecha a semana
lotada, ficaria sem turno extra.

**Evidência:** [`ex01`](docs/evidencias/sessoes/ex01-modelo-nao-dispara-relatorio.md). Com um
pedido em linguagem natural quase idêntico à descrição, a skill **não aparece** no
`skill_listing` e **não há** chamada à ferramenta `Skill`.

## Ex. 2: Progressive disclosure ([`docs/ex02-progressive-disclosure.md`](docs/ex02-progressive-disclosure.md))

**Solução:** três níveis.

1. A descrição, que aqui sai do contexto do modelo por causa do Ex. 1.
2. O `SKILL.md`: regras gerais, relatório básico completo e um roteamento explícito pela linha
   "Variação".
3. `variacoes/por-profissional.md` e `variacoes/por-especialidade.md`, lidas sob demanda.

O script de cerca de 12 mil caracteres é **executado, nunca lido**.

**Evidência:**

- [`basico`](docs/evidencias/sessoes/ex02-a-basico-sem-variacoes.md): **nenhum `Read`**, 1 turno,
  29,4 mil tokens de entrada.
- [`especialidade`](docs/evidencias/sessoes/ex02-b-especialidade-carrega-variacao.md): **um
  `Read`, só de `por-especialidade.md`**, 2 turnos, 59,7 mil tokens.

**Por quê:** o conteúdo da skill entra uma vez e **permanece** no contexto, que é reenviado a
cada turno. O que não se aplica ao pedido custa tokens e compete pela atenção do modelo.

## Ex. 3: Argumentos e injeção dinâmica ([`docs/ex03-argumentos-injecao.md`](docs/ex03-argumentos-injecao.md))

**Solução:** `arguments: [variacao, alvo, inicio, fim]` e a linha
`` !`python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py --variacao "$variacao" --alvo "$alvo" --inicio "$inicio" --fim "$fim"` ``.
O script aplica o período **no SQL** (`WHERE dia BETWEEN :inicio AND :fim`, a consulta
versionada do TP2), então registros fora do intervalo não chegam ao contexto.

**Evidência:**

| Comando | Período aplicado | Registros considerados | Ocupação da Dra. Helena Prado |
|---|---|---|---|
| [`profissional "Helena Prado"`](docs/evidencias/sessoes/ex03-a-so-profissional.md) | 23 a 27/11 (padrão) | 78 | 81,1% |
| [`profissional "Helena Prado" 2026-11-16 2026-11-18`](docs/evidencias/sessoes/ex03-b-profissional-e-periodo.md) | 16 a 18/11 | 45 | 79,6% |

## Ex. 4: Implementação funcional ([`docs/ex04-implementacao.md`](docs/ex04-implementacao.md))

**Solução:** a skill roda sobre o projeto real.

- Usa `agendamento/turnos.py` para calcular a capacidade e o SQL do TP2 para a ocupação.
- A `migration_005` cria a view `vw_ocupacao_diaria`, que o SQL do TP2 usava mas que nenhuma
  migration criava.
- O banco SQLite tem 833 consultas sintéticas, montado pelas migrations reais.

**Evidência:**

- [`basico 2026-11-30 2026-12-04`](docs/evidencias/sessoes/ex04-a-basico-periodo-informado.md):
  284 consultas, 64,6%.
- [`especialidade Dermatologia 2026-11-16 2026-11-20`](docs/evidencias/sessoes/ex04-b-especialidade-alvo-periodo.md):
  55,7%, 9 cancelamentos.
- [`especialidade Neurologia`](docs/evidencias/sessoes/ex04-c-parametro-invalido.md): erro
  repassado, nenhum número inventado.

**Ajuste justificado:** os cabeçalhos de comentário `# --- seção ---` da especificação foram
trocados por `# == seção ==`. O YAML era válido, mas o Claude Code 2.1.330 encerra o
frontmatter na primeira linha que contém `---`. Os campos seguintes (`allowed-tools`, e em outra
ordem o próprio `disable-model-invocation`) eram descartados **sem aviso**, e a injeção abortava
com *"This command requires approval"*. A causa foi isolada por bisseção com skills mínimas
([experimentos](docs/evidencias/execucoes-anteriores/)).

Lição: uma especificação de skill só está validada quando executada.

## Ex. 5: Skill sensível ([`docs/ex05-skill-sensivel.md`](docs/ex05-skill-sensivel.md))

**Solução:** `exportar-pacientes` com `disable-model-invocation: true` e `user-invocable: true`
(explícito). `allowed-tools` lista exatamente três regras: o script de exportação, `wc -l` e
`head -n 3`, as duas últimas presas a `exportacoes/`. O `deny: Read(./dados-sensiveis/**)` do
projeto continua valendo, e o script só imprime contagens; o CSV sai mascarado.

**Evidência:**

- [O modelo, autorizado pelo usuário, não dispara a skill](docs/evidencias/sessoes/ex05-a-modelo-tenta-exportar.md).
- [O modelo forçado a chamar a ferramenta `Skill` é recusado pelo Claude Code](docs/evidencias/sessoes/ex05-b-modelo-forca-skill-tool.md):
  `Skill exportar-pacientes cannot be used with Skill tool due to disable-model-invocation`.
- [A invocação explícita passa](docs/evidencias/sessoes/ex05-c-invocacao-explicita.md): 3
  chamadas, todas pré-aprovadas, `permission_denials: []`.
- [Controle](docs/evidencias/sessoes/ex05-d-controle-sem-allowed-tools.md): a mesma skill sem
  `allowed-tools` é bloqueada na primeira chamada (*"This command requires approval"*).

## Ex. 6: Subagente revisor ([`docs/ex06-subagente-revisor.md`](docs/ex06-subagente-revisor.md))

**Solução:** `revisor-codigo` com `model: sonnet` e `effort: medium`, `tools: Read, Grep, Glob,
Bash`, sem ferramentas de escrita.

**Modelo:** a revisão é delimitada (um diff e um checklist) e frequente (todo PR), então
custo e latência pesam mais. O Sonnet 5.5 custa metade do Opus 5.5 do agente principal
(US$ 2/10 contra US$ 4/20 por 1M tokens) e revisou em cerca de 13 s. O Haiku foi descartado
porque a revisão exige raciocinar sobre regras que estão fora do diff.

**Evidência:** [`@agent-revisor-codigo`](docs/evidencias/sessoes/ex06-revisor-explicito.md)
sobre a branch `feature/encaixe-horarios`, código real que **passa no ruff e no pytest**. O
revisor encontrou 3 problemas críticos (CPF em `print`, slots às 12:00 e 18:00, sobreposição
e consultas canceladas ignoradas) e deu **MUDANÇAS NECESSÁRIAS**. Os achados foram conferidos
linha a linha no arquivo.

## Ex. 7: Seleção automática ([`docs/ex07-selecao-automatica.md`](docs/ex07-selecao-automatica.md))

**Solução:** cada descrição tem gatilho por intenção, objeto concreto, momento, saída e
**exclusão que aponta o vizinho**. O `revisor-codigo` cuida de *código* ("NÃO use para ... SQL
ou relatórios"). O `gerador-relatorios` (`haiku`) cuida de *dados* ("NÃO revisa nem escreve
código ... e NÃO gera o relatório semanal oficial").

**Evidência**, sem nomear subagente:

- [*"dá uma olhada se está pronta para ir pra main?"*](docs/evidencias/sessoes/ex07-a-selecao-auto-revisao.md)
  → `revisor-codigo` ✅
- [*"qual especialidade teve mais cancelamentos ...?"*](docs/evidencias/sessoes/ex07-b-selecao-auto-dados.md)
  → `gerador-relatorios` ✅. Respondeu Dermatologia, 9, o mesmo número do relatório do Ex. 4,
  obtido por um caminho independente.

## Ex. 8: Isolamento ([`docs/ex08-isolamento.md`](docs/ex08-isolamento.md))

**Solução:**

- **Contexto:** subagente não-fork, com `omitClaudeMd: true` e `Agent` negado, para que ele não
  abra forks.
- **Ferramentas:** `disallowedTools: mcp__banco-producao__*, Write, Edit, ...`, uma barreira
  aplicada pelo Claude Code em qualquer modo de permissão.
- **Modo:** `permissionMode: dontAsk`, que nega todo Bash fora do que o `settings.json` libera.

**Evidência na mesma sessão** ([`ex08-b`](docs/evidencias/sessoes/ex08-b-mesma-ferramenta-principal-vs-subagente.md)):

- O agente principal chama `consultar_producao` e recebe `833 [conectado em ...prod-db...]`.
- O subagente recebe `['Read', 'Bash']`, com **nenhuma ferramenta MCP**.
- O Bash do subagente para subir o servidor de produção é **negado** duas vezes (*"denied
  because Claude Code is running in don't ask mode"*), e as negações aparecem em
  `permission_denials`.
- A primeira mensagem do subagente é só a delegação: nada do histórico, nem o resultado `833`.

## Ex. 9: Escopos e delegação ([`docs/ex09-escopos-delegacao.md`](docs/ex09-escopos-delegacao.md))

**Escopo:**

- `revisor-codigo` e `gerador-relatorios` → **project**: acoplados ao repositório, iguais para
  toda a squad, evoluem por PR.
- `conformidade-seguranca-infnet` → **managed**: PSI da instituição, maior precedência, não pode
  ser sobrescrito nem desligado por uma squad, e com `omitClaudeMd` não é influenciado por
  instruções locais.
- `explicador-codigo` → **user**: preferência pessoal.

**Delegação:** automática quando o efeito é só leitura e errar custa pouco (revisão consultiva,
perguntas sobre dados, conformidade). Explícita quando há efeito no processo ou dados sensíveis
(`/revisar-pr` como portão formal, `/relatorio-ocupacao`, `/exportar-pacientes`), e aí a trava é
aplicada pelo Claude Code com `disable-model-invocation: true`.

**Coerência:** quanto mais pessoas dependem de um gatilho automático ser previsível, mais alto o
escopo precisa estar. O que só pode ser explícito nunca depende de escopo nem de descrição.

**Evidência da delegação explícita formal:**
[`/revisar-pr feature/encaixe-horarios`](docs/evidencias/sessoes/ex09-revisar-pr-delegacao-explicita.md).

---

## Decisões transversais

| Decisão | Onde | Motivo |
|---|---|---|
| Nenhum `---` em comentários de frontmatter | todas as skills | O Claude Code encerra o frontmatter ali e descarta os campos seguintes sem aviso (Ex. 4) |
| Toda conta vem de script, nunca do modelo | `dados_ocupacao.py`, `consultar_local.py` | Números reproduzíveis. O modelo só formata e interpreta |
| Scripts de injeção sempre saem com código 0 | `dados_ocupacao.py` | Código diferente de zero aborta a skill e esconde o erro do desenvolvedor |
| Caminho sancionado em vez de afrouxar permissões | `scripts/checar_branch.py` | O revisor precisava rodar testes na branch. Ganhou um comando estreito, e não um `acceptEdits` |
| Dados pessoais nunca na saída padrão | `exportar.py` | O que o script imprime entra no contexto do modelo |
| Dados sintéticos com semente fixa | `gerar_dados_sinteticos.py` | Qualquer pessoa reproduz exatamente os números das evidências |
