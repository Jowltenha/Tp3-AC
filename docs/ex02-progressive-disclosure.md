# Ex. 2: Progressive disclosure no `SKILL.md`

## 1. Estrutura

```
servico-agendamento/.claude/skills/relatorio-ocupacao/
├── SKILL.md                      nível 2: carregado a cada invocação
│                                 (instruções gerais + relatório básico + roteamento)
├── variacoes/
│   ├── por-profissional.md       nível 3: lido SÓ se variacao=profissional
│   └── por-especialidade.md      nível 3: lido SÓ se variacao=especialidade
└── scripts/
    └── dados_ocupacao.py         executado, nunca lido: só a SAÍDA entra no contexto
```

| Nível | O que é | Quando entra no contexto | Tamanho |
|---|---|---|---|
| 1 | `name` + `description` | Em toda sessão, **se** o modelo puder invocar a skill. Aqui não entra, por causa de `disable-model-invocation` (Ex. 1) | 179 caracteres |
| 2 | Corpo do `SKILL.md` renderizado | Quando a skill é invocada | cerca de 2,3 mil caracteres de instruções, mais a saída do script |
| 3 | `variacoes/por-profissional.md` | Só quando o modelo lê o arquivo, porque a variação pedida é `profissional` | 1.953 caracteres |
| 3 | `variacoes/por-especialidade.md` | Só quando a variação pedida é `especialidade` | 1.432 caracteres |
| código | `scripts/dados_ocupacao.py` | **Nunca**. Só a saída filtrada entra | 12.216 caracteres que nunca vão ao modelo |

Como fica o `SKILL.md`:

- **Essencial, acessível de imediato:** regras gerais (somente leitura, não expor pacientes,
  sempre citar o período) e a seção **"Relatório básico"** completa, com o formato da resposta.
- **Roteamento:** a seção "Qual variação seguir" manda ler `variacoes/por-profissional.md` ou
  `variacoes/por-especialidade.md` *antes de escrever*, e diz explicitamente que o relatório
  básico **não** deve ler esses arquivos.
- **Variações, carregadas sob demanda:** cada arquivo traz o formato completo da sua variação
  (ficha do profissional, taxa de cancelamento, ranking de especialidades, desequilíbrio interno
  e recomendações).

## 2. Demonstração: duas invocações

| | `/relatorio-ocupacao basico` | `/relatorio-ocupacao especialidade` |
|---|---|---|
| Sessão | [ex02-a-basico-sem-variacoes.md](evidencias/sessoes/ex02-a-basico-sem-variacoes.md) | [ex02-b-especialidade-carrega-variacao.md](evidencias/sessoes/ex02-b-especialidade-carrega-variacao.md) |
| Chamadas de ferramenta | **nenhuma** | **1**: `Read .claude/skills/relatorio-ocupacao/variacoes/por-especialidade.md` |
| `por-profissional.md` lido? | não | **não**: só a variação pedida entrou |
| `por-especialidade.md` lido? | não | sim |
| Turnos | 1 | 2 |
| Tokens de entrada (novos + cache) | 29.400 | 59.672 |

Como ler as evidências:

1. Em cada `.md` de sessão, a seção **"Conteúdo da skill que ENTROU no contexto (renderizado)"**
   mostra o texto exato que o Claude Code inseriu na conversa, tirado da transcrição que ele
   mesmo grava em `~/.claude/projects/...`. Nos dois casos é o `SKILL.md`. O conteúdo de
   `variacoes/` **não** aparece ali.
2. Na sessão **básica**, a linha do tempo não tem `Read` nenhum. O relatório foi escrito só com
   o nível 2.
3. Na sessão **por especialidade**, a linha do tempo mostra o `Read` de `por-especialidade.md`, e
   só dele. A resposta final segue o formato desse arquivo (ranking de pressão de demanda,
   desequilíbrio interno, recomendação de capacidade), que não existe no `SKILL.md`.

A diferença de tokens (29,4 mil contra 59,7 mil) inclui o segundo turno inteiro, já que o
contexto é reenviado ao modelo depois do `Read`. Na prática, é o custo de pedir a variação. O
relatório básico, o caso mais frequente, nunca paga esse custo.

## 3. Por que isso evita sobrecarregar o contexto

1. **O contexto é cumulativo e é reenviado a cada turno.** O Claude Code insere o conteúdo
   renderizado da skill na conversa como **uma mensagem**, e ela **permanece** nos turnos
   seguintes. Na compactação automática, as skills invocadas ainda disputam um orçamento de cerca
   de 25 mil tokens. Um `SKILL.md` monolítico com as três variações pagaria cerca de 5,7 mil
   caracteres em **toda** invocação, e de novo em cada turno seguinte da sessão. Com a divisão, o
   caso básico paga cerca de 2,3 mil, e cada variação acrescenta só o próprio arquivo.
2. **O carregamento sob demanda usa uma ferramenta comum.** Arquivos de apoio não são lidos
   automaticamente. O modelo decide ler com `Read`, guiado pelo roteamento do `SKILL.md`. Por isso
   o roteamento é explícito e baseado num campo objetivo (a linha **Variação** do bloco
   injetado), e não em "use se achar relevante".
3. **O que é código é executado, não lido.** O `dados_ocupacao.py` tem cerca de 12 mil
   caracteres e roda na injeção dinâmica. Só a saída (as tabelas do recorte pedido) entra no
   contexto. A lógica de SQL, os cálculos e as validações nunca ocupam espaço.
4. **Menos ruído significa menos erro.** Instruções de variações que não foram pedidas competem
   pela atenção do modelo. Com o formato "por especialidade" no contexto de um relatório básico,
   o modelo poderia, por exemplo, acrescentar um ranking de especialidades que ninguém pediu.
   Manter fora do contexto o que não se aplica é também uma forma de garantir o formato.
5. **A skill cresce sem custo para quem não usa a parte nova.** Uma variação futura (por
   exemplo, "por convênio") entra como `variacoes/por-convenio.md` mais uma linha no
   roteamento. O custo do relatório básico continua o mesmo.
