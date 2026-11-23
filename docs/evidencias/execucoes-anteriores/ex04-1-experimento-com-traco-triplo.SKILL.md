---
name: zz-teste
description: teste
arguments: [variacao, alvo, inicio, fim]
disable-model-invocation: true
# --- secao ---
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/x.py *)
---
!`python3 ${CLAUDE_SKILL_DIR}/scripts/x.py --variacao "$variacao" --alvo "$alvo" --inicio "$inicio" --fim "$fim"`

Copie o texto acima literalmente.
