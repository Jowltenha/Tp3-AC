---
name: zz-teste
description: teste
arguments: [variacao, alvo, inicio, fim]
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/x.py *)
# --- secao ---
disable-model-invocation: true
---
!`python3 ${CLAUDE_SKILL_DIR}/scripts/x.py --variacao "$variacao" --alvo "$alvo" --inicio "$inicio" --fim "$fim"`

Copie o texto acima literalmente.
