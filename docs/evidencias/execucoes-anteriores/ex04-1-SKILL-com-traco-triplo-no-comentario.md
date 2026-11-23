---
name: relatorio-ocupacao
description: >-
  Gera o relatório semanal de ocupação de horários do serviço de agendamento (básico, por
  profissional ou por especialidade), a partir das consultas do banco local. Somente leitura.
argument-hint: "[basico|profissional|especialidade] [profissional-ou-especialidade] [inicio AAAA-MM-DD] [fim AAAA-MM-DD]"
arguments: [variacao, alvo, inicio, fim]
# --- Controle de invocação (Ex. 1) -------------------------------------------------------------
# disable-model-invocation: true -> só o desenvolvedor dispara a skill, digitando /relatorio-ocupacao.
#   * A descrição NÃO entra no contexto do modelo, que nem sabe que a skill existe.
#   * Se o modelo tentar a ferramenta Skill, o Claude Code recusa ("cannot be used with Skill tool
#     due to disable-model-invocation").
# Por que não deixar o modelo decidir: o relatório é um ARTEFATO DE PROCESSO. Ele fotografa a
# agenda num momento escolhido pela squad (fechamento da semana) e é repassado à coordenação.
# Pedidos como "a agenda da Dra. Helena está cheia?" são parecidos com o gatilho, mas não pedem o
# relatório. Gerá-lo nessas horas gasta contexto e tempo, e solta números parciais como se
# fossem os oficiais. user-invocable fica no padrão (true): a skill aparece no menu "/".
disable-model-invocation: true
# --- Pré-aprovação (Ex. 4) ---------------------------------------------------------------------
# A injeção dinâmica (linha com exclamação + crase) passa pela checagem de permissões ANTES de o modelo ver a skill. Sem esta
# linha, a invocação era abortada com "Shell command permission check failed ... This command
# requires approval" (ver docs/evidencias/execucoes-anteriores/). A regra cobre só o script de
# leitura da própria skill. Read cobre os arquivos de variação (progressive disclosure).
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py *) Read(${CLAUDE_SKILL_DIR}/variacoes/*)
---

# Relatório de ocupação de horários

Você está gerando o relatório de ocupação de horários da squad de agendamento de consultas.
O relatório é **somente leitura**: não altere a agenda, o banco ou qualquer arquivo do projeto.

## Dados já calculados (injeção dinâmica)

O bloco abaixo foi gerado pelo script `scripts/dados_ocupacao.py` no momento da invocação. Ele
aplica os argumentos (`variacao=$variacao`, `alvo=$alvo`, `inicio=$inicio`, `fim=$fim`) e
filtra no SQL apenas as consultas do período. **Use exclusivamente esses números.** Não recalcule,
não estime e não consulte o banco por outros meios.

!`python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py --variacao "$variacao" --alvo "$alvo" --inicio "$inicio" --fim "$fim"`

## Qual variação seguir

Olhe a linha **Variação** do bloco acima:

- `basico`: siga apenas a seção "Relatório básico" abaixo. **Não leia** os arquivos de
  `variacoes/`. Eles não são necessários para o relatório básico.
- `profissional`: leia **antes de escrever** o arquivo
  [variacoes/por-profissional.md](variacoes/por-profissional.md) e siga o formato dele.
- `especialidade`: leia **antes de escrever** o arquivo
  [variacoes/por-especialidade.md](variacoes/por-especialidade.md) e siga o formato dele.
- Se o bloco começar com `ERRO DE PARÂMETRO` ou `ERRO INTERNO`, não gere relatório. Repasse a
  mensagem ao desenvolvedor e mostre o uso correto:
  `/relatorio-ocupacao [basico|profissional|especialidade] [alvo] [inicio] [fim]`.

## Relatório básico

Responda em português, em Markdown, nesta ordem:

1. **Título**: `Relatório de ocupação: <período>`.
2. **Escopo**: período, origem do período (informado ou padrão), registros considerados.
3. **Tabela de ocupação por dia**: copie a tabela do bloco de dados sem alterar números.
4. **Destaques**: no máximo 3 itens: dia de maior e de menor ocupação, e qualquer dia `LOTADO`
   (>= 85%) ou `OCIOSO` (< 50%).
5. **Próximo passo sugerido**: uma frase. Exemplo: abrir encaixes no dia mais livre, ou rodar
   `/relatorio-ocupacao especialidade` para achar a origem da ociosidade.

Regras gerais (todas as variações):

- Não exponha dados de pacientes. O relatório trabalha só com contagens.
- Cite sempre o período exato. Um relatório sem período é inválido.
- Se "Registros considerados" for 0, diga que não há consultas no período e pare.
