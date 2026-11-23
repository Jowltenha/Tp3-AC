# Ex. 3: Argumentos e injeção dinâmica de contexto

## 1. Argumentos declarados no `SKILL.md`

```yaml
argument-hint: "[basico|profissional|especialidade] [profissional-ou-especialidade] [inicio AAAA-MM-DD] [fim AAAA-MM-DD]"
arguments: [variacao, alvo, inicio, fim]
```

- `arguments` dá nome aos argumentos posicionais. Com isso, `$variacao`, `$alvo`, `$inicio` e
  `$fim` ficam disponíveis no corpo da skill (equivalem a `$0`, `$1`, `$2` e `$3`).
- `argument-hint` aparece no autocomplete do menu `/`.
- Um nome com espaço vai entre aspas: `/relatorio-ocupacao profissional "Helena Prado"`.
- Os argumentos aparecem em dois lugares do corpo:
  - no texto, para o modelo saber o que foi pedido (`variacao=$variacao`, `alvo=$alvo` ...);
  - na **injeção dinâmica**, como parâmetros do script.

## 2. Injeção dinâmica que filtra o período

```markdown
!`python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py --variacao "$variacao" --alvo "$alvo" --inicio "$inicio" --fim "$fim"`
```

Na invocação, **antes** de enviar qualquer coisa ao modelo, o Claude Code:

1. substitui `${CLAUDE_SKILL_DIR}` e `$variacao/$alvo/$inicio/$fim` pelos valores digitados;
2. checa o comando resultante contra as regras de permissão. A regra `allowed-tools` da skill
   pré-aprova `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/dados_ocupacao.py *)`;
3. executa o comando e **substitui a linha pela saída** do script.

O script ([`scripts/dados_ocupacao.py`](../servico-agendamento/.claude/skills/relatorio-ocupacao/scripts/dados_ocupacao.py))
faz o filtro do período **no SQL**, usando a consulta versionada do projeto
[`db/consultas/ocupacao_por_medico.sql`](../servico-agendamento/db/consultas/ocupacao_por_medico.sql):

```sql
SELECT medico_id, dia, consultas, minutos_ocupados
FROM vw_ocupacao_diaria
WHERE dia BETWEEN :inicio AND :fim
```

Assim, **os registros fora do intervalo não chegam ao contexto**. O modelo recebe só as linhas
agregadas do período e não tem como "considerar" um dia que não pediu. Sem datas, o período
padrão é a semana corrente (segunda a sexta), e o bloco injetado diz isso.

O cabeçalho da saída também registra o que a injeção recebeu e o que filtrou. É isso que torna a
demonstração verificável:

```
**Argumentos recebidos pela injeção:** variacao=`profissional` alvo=`Helena Prado` inicio=`2026-11-16` fim=`2026-11-18`
- **Período:** 16/11/2026 a 18/11/2026 (informado nos argumentos), 3 dia(s) úteis
- **Registros na base:** 833 consultas de 2026-11-16 a 2026-12-04
- **Registros considerados (período + recorte):** 45 consultas de 2026-11-16 a 2026-11-18
```

## 3. Demonstração: duas invocações

| | A: só profissional | B: profissional + período |
|---|---|---|
| Comando | `/relatorio-ocupacao profissional "Helena Prado"` | `/relatorio-ocupacao profissional "Helena Prado" 2026-11-16 2026-11-18` |
| Sessão | [ex03-a-so-profissional.md](evidencias/sessoes/ex03-a-so-profissional.md) | [ex03-b-profissional-e-periodo.md](evidencias/sessoes/ex03-b-profissional-e-periodo.md) |
| Injeção recebeu | `alvo=Helena Prado inicio= fim=` | `alvo=Helena Prado inicio=2026-11-16 fim=2026-11-18` |
| Período aplicado | 23/11 a 27/11 (**padrão**, semana corrente) | 16/11 a 18/11 (**informado**) |
| Registros considerados | 78 de 833 | 45 de 833 |
| Dias no relatório | seg 23/11 a sex 27/11 (5) | seg 16/11 a qua 18/11 (3) |
| Ocupação da Dra. Helena | 81,1% (73/90 slots) | 79,6% (43/54 slots) |
| Faltas | 0 (semana corrente, ainda não apuradas) | 1 (dias já passados) |

O resultado reflete os argumentos nos dois casos:

- **O nome filtra o profissional**: nas duas, a injeção traz só "Profissionais no recorte: Dra.
  Helena Prado" (a busca não diferencia acento nem maiúscula, e aceita parte do nome).
- **As datas mudam o período e, com ele, os registros**: 78 contra 45 consultas, 5 contra 3
  dias, e números de ocupação diferentes.
- **O modelo seguiu o período**: em B, a resposta fala só de 16 a 18/11, como manda a regra de
  `por-profissional.md` ("se o desenvolvedor passou datas, não fale de dias fora delas"), e nota
  que as faltas já foram apuradas porque os dias são anteriores a 23/11.
- Nas duas sessões, a variação `profissional` fez o modelo ler `variacoes/por-profissional.md`
  (progressive disclosure do Ex. 2), e a resposta segue o formato desse arquivo: ficha, tabela
  diária, indicadores e leitura operacional.

Os números podem ser conferidos sem o Claude Code, rodando o script diretamente:

```bash
cd servico-agendamento
python3 .claude/skills/relatorio-ocupacao/scripts/dados_ocupacao.py \
  --variacao profissional --alvo "Helena Prado" --inicio 2026-11-16 --fim 2026-11-18
```

## 4. Por que um script, e não um `SELECT` direto na linha `!`

- **Segurança contra injeção de shell.** Os argumentos vêm entre aspas (`"$alvo"`) e chegam ao
  script como `argv`. O Claude Code também recusa a injeção quando o texto entre aspas não pode
  ser checado. Num teste preliminar com o argumento `$(touch /tmp/PWNED2)x`, a invocação foi
  abortada com *"Quoted text in this command can't be checked before it runs"*, e nenhum arquivo
  foi criado.
- **Parâmetros posicionais com partes opcionais.** No relatório básico não existe `alvo`, então
  `/relatorio-ocupacao basico 2026-11-16 2026-11-20` chega como `alvo=2026-11-16`,
  `inicio=2026-11-20`. O script reconhece datas pelo formato, em qualquer posição (detalhes no
  Ex. 4).
- **Erros não derrubam a skill.** Comando com código de saída diferente de zero aborta a
  invocação inteira, e o modelo nunca vê a mensagem. Por isso o script sempre sai com 0 e
  devolve `ERRO DE PARÂMETRO: ...`, que o `SKILL.md` manda repassar ao desenvolvedor.
