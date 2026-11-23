# Ex. 1: Skill `relatorio-ocupacao` e o controle de invocação

**Artefato:** [`servico-agendamento/.claude/skills/relatorio-ocupacao/SKILL.md`](../servico-agendamento/.claude/skills/relatorio-ocupacao/SKILL.md)

## 1. Frontmatter

```yaml
---
name: relatorio-ocupacao
description: >-
  Gera o relatório semanal de ocupação de horários do serviço de agendamento (básico, por
  profissional ou por especialidade), a partir das consultas do banco local. Somente leitura.
argument-hint: "[basico|profissional|especialidade] [profissional-ou-especialidade] [inicio AAAA-MM-DD] [fim AAAA-MM-DD]"
arguments: [variacao, alvo, inicio, fim]
# == Controle de invocação (Ex. 1) ==
# disable-model-invocation: true => só o desenvolvedor dispara a skill, digitando /relatorio-ocupacao.
#   * A descrição NÃO entra no contexto do modelo, que nem sabe que a skill existe.
#   * Se o modelo tentar a ferramenta Skill, o Claude Code recusa ("cannot be used with Skill tool
#     due to disable-model-invocation").
# Por que não deixar o modelo decidir: o relatório é um ARTEFATO DE PROCESSO. ...
disable-model-invocation: true
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py *)
---
```

O arquivo real tem mais campos (`arguments` e `allowed-tools`), que entram nos Ex. 3 e 4. A
justificativa completa está em comentário YAML ao lado do campo, como o enunciado pede.

| Campo | Valor | Função |
|---|---|---|
| `name` | `relatorio-ocupacao` | Vira o comando `/relatorio-ocupacao` |
| `description` | o que a skill faz | Aparece no menu `/` para o desenvolvedor. Como a invocação pelo modelo está desligada, **não** entra no contexto do modelo |
| `disable-model-invocation` | `true` | **Controle de invocação**: só o desenvolvedor dispara a skill |
| `user-invocable` | omitido (padrão `true`) | A skill continua no menu `/` |

## 2. Por que `disable-model-invocation: true` e não deixar o modelo decidir

O Claude Code tem três regimes de invocação para uma skill:

| Frontmatter | Dev invoca | Modelo invoca | Descrição no contexto do modelo |
|---|---|---|---|
| padrão | sim | sim | sim |
| `disable-model-invocation: true` | **sim** | **não** | **não** |
| `user-invocable: false` | não | sim | sim |

O pedido da liderança ("apenas quando explicitamente solicitada, nunca de forma automática")
corresponde à segunda linha. Três motivos técnicos justificam a escolha:

1. **O relatório é um artefato de processo, não uma resposta.** Ele fotografa a agenda no
   fechamento da semana e vai para a coordenação. *Quando* ele é gerado faz parte do contrato,
   e só o desenvolvedor sabe que a semana fechou.
2. **A descrição é um gatilho aproximado.** No modo padrão, o modelo compara cada pedido com a
   descrição e decide sozinho. Perguntas como "a agenda da Dra. Helena está cheia?" ou "quantas
   consultas temos amanhã?" ficam semanticamente perto de "relatório de ocupação", mas não pedem o
   relatório. Com `disable-model-invocation: true` a descrição sai do contexto do modelo, e essa
   ambiguidade deixa de existir.
3. **A garantia é aplicada pelo Claude Code, não pelo prompt.** Uma frase como "só rode quando
   pedirem" no corpo da skill seria uma instrução que o modelo pode interpretar mal. O campo do
   frontmatter é aplicado pelo próprio Claude Code: a chamada `Skill(relatorio-ocupacao)` vinda
   do modelo é recusada antes de executar (evidência no Ex. 5, que usa o mesmo mecanismo).

`user-invocable: false` seria o **oposto** do desejado: esconderia a skill do desenvolvedor e a
deixaria só para o modelo.

## 3. Cenário: o mesmo relatório com invocação automática

Sexta-feira, 27/11, 15h. A squad fecha a semana às 18h, e o relatório semanal vai para a
coordenação clínica, que decide os encaixes e os turnos extras da semana seguinte.

1. Às 10h, o desenvolvedor Lucas está corrigindo um bug em `agendamento/encaixe.py` e pergunta
   ao Claude Code: *"por que a agenda de dermatologia aparece tão ocupada nos testes?"*
2. Com invocação automática, o modelo associa "agenda" + "ocupada" à descrição da skill e
   **dispara `/relatorio-ocupacao` sozinho**, gerando um relatório completo da semana parcial
   (sexta às 10h, sem os agendamentos da tarde).
3. Efeitos:
   - **O fluxo de depuração é interrompido.** Lucas queria entender um teste e recebeu tabelas de
     ocupação. O contexto da sessão agora carrega cerca de 2,5 mil caracteres do relatório, mais
     as variações lidas, que não têm nada a ver com o bug.
   - **Números parciais circulam como oficiais.** O relatório gerado às 10h diz "Dermatologia
     60,7%, normal". Lucas cola o resultado no canal da squad e a coordenação usa esse número.
     Às 18h a dermatologia fecha em 88%, LOTADO, e nenhum turno extra foi aberto para a semana
     seguinte.
   - **Desperdício recorrente.** Toda pergunta sobre agenda vira uma execução do script com
     leitura do banco. Multiplicado pela squad inteira ao longo do dia, isso gasta tokens e
     tempo sem necessidade.

Com `disable-model-invocation: true`, o passo 2 não acontece. O modelo não vê a skill e responde
à pergunta sobre o teste. O relatório só sai quando alguém digita `/relatorio-ocupacao` às 18h.

## 4. Evidência real

**Sessão:** [`ex01-modelo-nao-dispara-relatorio.md`](evidencias/sessoes/ex01-modelo-nao-dispara-relatorio.md)

Prompt em linguagem natural, o mais próximo possível da descrição da skill: *"Fechamos a semana.
Gere o relatório semanal de ocupação de horários da agenda."*

- A seção **"Skills que o MODELO recebeu no contexto (`skill_listing`)"** lista só as skills
  embutidas do Claude Code. `relatorio-ocupacao` **não está lá**: a descrição foi retirada do
  contexto.
- A linha do tempo **não tem nenhuma chamada à ferramenta `Skill`**, e nenhum relatório foi
  gerado.
- O modelo respondeu orientando o desenvolvedor a digitar `/relatorio-ocupacao`. Ele sabia o
  nome pelo `CLAUDE.md` do projeto, que documenta as skills da squad, e não pela listagem de
  skills.

A invocação explícita do mesmo relatório funciona: ver
[`ex02-a-basico-sem-variacoes.md`](evidencias/sessoes/ex02-a-basico-sem-variacoes.md).
