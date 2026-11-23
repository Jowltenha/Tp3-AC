---
name: exportar-pacientes
description: >-
  Exporta para CSV, com mascaramento LGPD, os pacientes que têm consulta num período. Manipula
  dados pessoais sensíveis (nome, CPF, telefone): uso restrito e só por comando explícito.
argument-hint: "[inicio AAAA-MM-DD] [fim AAAA-MM-DD]"
arguments: [inicio, fim]
# ATENÇÃO: sem linhas com três hifens seguidos aqui; ver o aviso em relatorio-ocupacao/SKILL.md.
#
# == Controle de invocação (Ex. 5) ==
# disable-model-invocation: true => o modelo NUNCA dispara esta skill. A descrição sai do contexto
#   (o modelo não sabe que ela existe), e uma chamada à ferramenta Skill é recusada pelo próprio
#   Claude Code, não por instrução no prompt. Só `/exportar-pacientes` digitado pelo
#   desenvolvedor executa a skill.
# user-invocable: true => explícito (é o padrão). Mantém a skill no menu "/" e invocável pelo
#   desenvolvedor. Com false, a skill ficaria visível SÓ para o modelo, o oposto do desejado. Com
#   as duas travas (disable-model-invocation: true + user-invocable: false), ninguém a invocaria.
disable-model-invocation: true
user-invocable: true
#
# == Ferramentas pré-aprovadas (Ex. 5) ==
# Exatamente o necessário, nada mais. Durante o turno da invocação estas regras não pedem
# confirmação. Qualquer outra ferramenta segue as regras normais do settings.json.
#   1. Bash do script de exportação, que só imprime contagens e grava o CSV mascarado.
#   2. Bash(wc -l ...) e Bash(head -n 3 ...) restritos ao diretório exportacoes/, para conferir a
#      quantidade de linhas e o cabeçalho do arquivo gerado (dados já mascarados).
# Leitura direta de dados-sensiveis/ NÃO entra aqui e continua negada pelo settings.json.
allowed-tools:
  - Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/exportar.py *)
  - Bash(wc -l exportacoes/*)
  - Bash(head -n 3 exportacoes/*)
---

# Exportação de pacientes (dados sensíveis)

Período solicitado: início `$inicio`, fim `$fim`.

Se início ou fim estiverem vazios, **não exporte nada**. Responda apenas com o uso correto,
`/exportar-pacientes AAAA-MM-DD AAAA-MM-DD`, e pare.

Caso contrário:

1. Rode exatamente `python3 ${CLAUDE_SKILL_DIR}/scripts/exportar.py --inicio $inicio --fim $fim`.
2. Confira o arquivo gerado com `wc -l exportacoes/<arquivo>` e `head -n 3 exportacoes/<arquivo>`.
3. Responda com: quantidade de pacientes, caminho do arquivo, hash, e as 2 primeiras linhas de
   dados **como saíram do `head`** (já mascaradas).

Regras:

- Nunca leia `dados-sensiveis/` diretamente, nem tente desmascarar dados.
- Não use nenhuma ferramenta além das três pré-aprovadas.
- Não copie o CSV para outro lugar nem o envie a serviços externos.
