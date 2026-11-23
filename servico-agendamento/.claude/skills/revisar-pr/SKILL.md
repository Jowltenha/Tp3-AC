---
name: revisar-pr
description: >-
  Portão de revisão antes do merge. Roda o subagente revisor-codigo em contexto isolado sobre
  o diff da branch indicada contra a main.
argument-hint: "[branch]"
arguments: [branch]
# == Delegação EXPLÍCITA (Ex. 9) ==
# disable-model-invocation: true => só o desenvolvedor abre o portão de revisão, com /revisar-pr.
# context: fork + agent: revisor-codigo => o corpo abaixo vira a TAREFA de um subagente
#   revisor-codigo novo, sem o histórico da conversa principal (mesmo isolamento do Ex. 8).
# background: false => o desenvolvedor espera o parecer no mesmo turno.
disable-model-invocation: true
context: fork
agent: revisor-codigo
background: false
allowed-tools: Bash(git diff *) Bash(git log *)
---

Revise a branch `$branch` antes do merge na `main`.

Commits da branch:

!`git log --oneline main..$branch`

Arquivos alterados:

!`git diff --stat main...$branch`

Siga o seu procedimento de revisão sobre `git diff main...$branch` e devolva o parecer no
formato padrão, com o veredito final.
