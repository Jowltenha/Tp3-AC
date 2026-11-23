# Ex. 4: Implementação funcional da skill `relatorio-ocupacao`

## 1. O que foi implementado

A skill roda de ponta a ponta dentro do projeto real do serviço de agendamento (o mesmo
`servico-agendamento/` do TP2, trazido para este repositório):

| Peça | Arquivo | Papel |
|---|---|---|
| Skill | [`.claude/skills/relatorio-ocupacao/SKILL.md`](../servico-agendamento/.claude/skills/relatorio-ocupacao/SKILL.md) | Contrato: invocação, argumentos, injeção, roteamento e formato |
| Variações | [`variacoes/por-profissional.md`](../servico-agendamento/.claude/skills/relatorio-ocupacao/variacoes/por-profissional.md), [`variacoes/por-especialidade.md`](../servico-agendamento/.claude/skills/relatorio-ocupacao/variacoes/por-especialidade.md) | Carregadas sob demanda (Ex. 2) |
| Coleta | [`scripts/dados_ocupacao.py`](../servico-agendamento/.claude/skills/relatorio-ocupacao/scripts/dados_ocupacao.py) | SQL somente leitura e cálculo da ocupação |
| Regra de turnos | [`agendamento/turnos.py`](../servico-agendamento/agendamento/turnos.py) | `TURNOS` e `duracao_turno()` do TP2 definem a capacidade |
| Consulta SQL | [`db/consultas/ocupacao_por_medico.sql`](../servico-agendamento/db/consultas/ocupacao_por_medico.sql) | A consulta do analista de dados do TP2, reaproveitada |
| Esquema | [`db/migrations/`](../servico-agendamento/db/migrations/) | `001`/`002` do TP2, mais `003` (profissionais), `004` (pacientes) e `005` (a view `vw_ocupacao_diaria`, que o SQL do TP2 já usava mas que não existia) |
| Dados | [`scripts/gerar_dados_sinteticos.py`](../servico-agendamento/scripts/gerar_dados_sinteticos.py), [`scripts/montar_banco.py`](../servico-agendamento/scripts/montar_banco.py) | 6 profissionais, 4 especialidades e 833 consultas sintéticas (de 16/11 a 04/12/2026, semente fixa), carregados num SQLite pelas migrations reais |

**Por que dados sintéticos.** O TP2 tinha só o esquema (`migration_001`) e três pacientes de
exemplo, sem consultas. Para ter um relatório com números, o gerador cria uma agenda plausível
com perfis de ocupação diferentes por profissional (de 32% a 95%) e status realistas
(`realizada` e `falta` antes de 23/11; `agendada` depois; cerca de 7% de `cancelada`). Como a
semente é fixa, quem roda os scripts obtém exatamente os números das evidências.

Para reproduzir:

```bash
cd servico-agendamento
python3 scripts/gerar_dados_sinteticos.py && python3 scripts/montar_banco.py
claude            # aceite "Trust this folder" uma vez
/relatorio-ocupacao basico 2026-11-30 2026-12-04
```

## 2. Execuções reais

Todas as execuções são sessões headless reais (`claude -p`), gravadas por
[`rodar_cenario.py`](evidencias/rodar_cenario.py). Cada `.md` traz o conteúdo renderizado da
skill (com a saída real da injeção), as chamadas de ferramenta e a resposta final.

| # | Comando | Resultado | Sessão |
|---|---|---|---|
| 1 | `/relatorio-ocupacao basico 2026-11-30 2026-12-04` | Semana seguinte: 284 consultas, 64,6% de ocupação, qui 03/12 com o pico (70,7%). Nenhum `Read`: só o nível 2 | [ex04-a](evidencias/sessoes/ex04-a-basico-periodo-informado.md) |
| 2 | `/relatorio-ocupacao especialidade Dermatologia 2026-11-16 2026-11-20` | Só Dermatologia (2 profissionais, 87 registros): 55,7%, 9 cancelamentos. Leu `por-especialidade.md` | [ex04-b](evidencias/sessoes/ex04-b-especialidade-alvo-periodo.md) |
| 3 | `/relatorio-ocupacao especialidade Neurologia` | `ERRO DE PARÂMETRO` repassado com a lista de especialidades válidas. Nenhum relatório inventado | [ex04-c](evidencias/sessoes/ex04-c-parametro-invalido.md) |

As execuções dos Ex. 2 e 3 também são reais e somam mais quatro parametrizações:
[basico](evidencias/sessoes/ex02-a-basico-sem-variacoes.md),
[especialidade](evidencias/sessoes/ex02-b-especialidade-carrega-variacao.md),
[profissional](evidencias/sessoes/ex03-a-so-profissional.md) e
[profissional + período](evidencias/sessoes/ex03-b-profissional-e-periodo.md).

Trecho da saída real da execução 1 (resposta final do Claude Code):

```
# Relatório de ocupação: 30/11/2026 a 04/12/2026
- Período: 30/11/2026 (seg) a 04/12/2026 (sex), 5 dias úteis. Você informou o período nos argumentos.
- Registros considerados: 284 consultas no período, de 833 na base (16/11/2026 a 04/12/2026).

| Dia | Capacidade (slots) | Ocupados | Livres | Ocupação | Situação |
| seg 30/11 | 82 | 54 | 28 | 65.9% | normal |
| ter 01/12 | 82 | 55 | 27 | 67.1% | normal |
| qua 02/12 | 82 | 52 | 30 | 63.4% | normal |
| qui 03/12 | 82 | 58 | 24 | 70.7% | normal |
| sex 04/12 | 82 | 46 | 36 | 56.1% | normal |
| Total     | 410 | 265 | 145 | 64.6% | normal |
```

Na execução 1, a injeção recebeu `alvo=2026-11-30 inicio=2026-12-04 fim=`. Os argumentos
posicionais "deslizaram" uma posição, porque o relatório básico não tem alvo. O script
reconheceu as datas pelo formato e aplicou o período certo (ajuste C, abaixo).

## 3. Justificativa técnica: o ajuste entre a especificação e a implementação

### Ajuste principal: os comentários de seção no frontmatter mudaram de `# --- ... ---` para `# == ... ==`

**Especificação inicial (Ex. 1 a 3).** A justificativa do controle de invocação ficava em
comentários YAML no frontmatter, separados por cabeçalhos no estilo comum de arquivos de
configuração:

```yaml
arguments: [variacao, alvo, inicio, fim]
# --- Controle de invocação (Ex. 1) -----------------------------------
# ...
disable-model-invocation: true
# --- Pré-aprovação (Ex. 4) -------------------------------------------
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py *)
---
```

O YAML é válido: para um parser YAML, `# ---` é só um comentário.

**O que aconteceu na execução real.** Toda invocação abortava antes de chegar ao modelo:

```
Shell command permission check failed for pattern "!`python3 .../dados_ocupacao.py --variacao "basico" ...`": This command requires approval
```

Ou seja, a pré-aprovação de `allowed-tools` era ignorada. Uma bisseção com uma skill mínima
isolou a causa. Os arquivos e as saídas estão em
[`execucoes-anteriores/`](evidencias/execucoes-anteriores/):

| Experimento | Frontmatter | Resultado |
|---|---|---|
| [sem-traco-triplo](evidencias/execucoes-anteriores/ex04-1-experimento-sem-traco-triplo.SKILL.md) | comentário `# == secao ==` antes de `allowed-tools` | injeção executa: `OK [...]` |
| [com-traco-triplo](evidencias/execucoes-anteriores/ex04-1-experimento-com-traco-triplo.SKILL.md) | comentário `# --- secao ---` antes de `allowed-tools` | **abortada**: `This command requires approval` |
| [traco-triplo-depois-do-allowed](evidencias/execucoes-anteriores/ex04-1-experimento-traco-triplo-depois-do-allowed.SKILL.md) | `allowed-tools` **antes** do `# --- secao ---` | injeção executa, mas o texto `secao --- / disable-model-invocation: true / ---` **vaza para o corpo** da skill ([saída](evidencias/execucoes-anteriores/ex04-1-experimento-traco-triplo-depois-do-allowed.jsonl)) |

**Causa.** O Claude Code 2.1.330 não usa um parser YAML para achar o **fim** do frontmatter. Ele
procura a primeira linha que contém `---`. A linha `# --- Pré-aprovação ...` encerra o
frontmatter ali mesmo. Todo campo depois dela é descartado sem aviso e vira texto do corpo. No
terceiro experimento, o próprio `disable-model-invocation: true` foi parar no corpo: a trava de
invocação do Ex. 1 deixaria de existir, também sem aviso.

**Ajuste.** Os cabeçalhos de seção passaram a usar `# == ... ==`, e as duas skills sensíveis
ganharam um aviso no topo do frontmatter:

```yaml
# ATENÇÃO (Ex. 4): nenhuma linha deste frontmatter pode conter três hifens seguidos. ...
# == Controle de invocação (Ex. 1) ==
```

**Por que o ajuste era necessário, e não só estético.** A especificação dos Ex. 1 a 3 estava
correta no papel e passaria em qualquer validador YAML. A falha só aparece quando o arquivo é
lido pelo Claude Code de verdade. O mesmo problema, com a seção em outra ordem, desliga em
silêncio o controle de invocação de uma skill sensível. Daí a regra prática que este TP adota:
**uma especificação de skill só está validada depois de executada**. A forma de provar que um
campo do frontmatter foi aplicado é observar o efeito dele numa sessão real (a injeção rodou, a
skill sumiu do `skill_listing`), não ler o arquivo.

### Outros ajustes da implementação

- **A. `allowed-tools` passou a ser obrigatório para a injeção.** A especificação do Ex. 3 tratava
  a linha `!` como algo que "só roda". Na prática, o comando passa pela checagem de permissões
  antes de o modelo ver a skill, e sem regra de `allow` a invocação inteira é abortada
  ([primeira execução](evidencias/execucoes-anteriores/ex04-0-placeholder-em-comentario.jsonl)).
  A regra ficou o mais estreita possível: só o script da própria skill, via `${CLAUDE_SKILL_DIR}`.
- **B. Nada de `!` + crase em texto da skill, nem em comentários.** A primeira execução abortou
  com o padrão `` !`...` ``. Ele estava num **comentário** que explicava a injeção, e o Claude
  Code tentou executá-lo. O comentário foi reescrito por extenso ("linha que começa com
  exclamação + crase").
- **C. Argumentos posicionais exigem normalização.** `arguments: [variacao, alvo, inicio, fim]`
  é estritamente posicional, e o relatório básico não tem alvo. O script reconhece datas
  `AAAA-MM-DD` em qualquer posição e trata o que sobra como alvo (execução 1).
- **D. O script nunca sai com código diferente de zero.** Um comando injetado que falha aborta a
  skill, e o modelo não vê a mensagem. Erros viram texto (`ERRO DE PARÂMETRO: ...`), que o
  `SKILL.md` manda repassar (execução 3).
- **E. O SQL do TP2 precisou de uma coluna e de uma view.** O `ocupacao_por_medico.sql` dependia
  de `vw_ocupacao_diaria`, que nenhuma migration criava. Entrou a `migration_005`, e o SELECT
  ganhou `minutos_ocupados`.
