# Ex. 7: Descrições para seleção automática de subagentes

## 1. Como o Claude Code escolhe um subagente

O agente principal recebe no contexto o `name` + `description` de **todos** os subagentes
disponíveis (os embutidos, como `Explore`, `Plan` e `general-purpose`, e os do projeto). A cada
pedido, ele compara o texto do pedido com essas descrições e decide se delega, e para quem. O
corpo do `.md` (o system prompt) **não** entra nessa decisão: ele só carrega quando o subagente
roda. Por isso a descrição precisa funcionar sozinha como **regra de roteamento**.

Critérios usados para escrever as descrições:

| Critério | Aplicação |
|---|---|
| **Gatilho por intenção** (verbo + objeto) | revisor: *revisar, auditar, aprovar* + *código Python*; relatórios: *pergunta sobre números da agenda* |
| **Objeto concreto** (artefatos, pastas) | revisor: *diff, branch, PR, commit ou arquivo .py em `agendamento/`, `tests/`, `scripts/`*; relatórios: *ocupação, horários livres, cancelamentos, faltas, por profissional ou especialidade* |
| **Momento** | revisor: *antes de um merge, e logo depois de escrever ou alterar código Python*; relatórios: *que se responde consultando o banco local* |
| **Saída prometida** | revisor: *parecer com achados por severidade e veredito*; relatórios: *tabela + resposta curta* |
| **Exclusão explícita, que aponta o vizinho** | revisor: *NÃO use para perguntas sobre dados ... isso é do gerador-relatorios*; relatórios: *NÃO revisa nem escreve código (isso é do revisor-codigo) e NÃO gera o relatório semanal oficial* |
| **"Use PROATIVAMENTE"** | Nas duas descrições: torna a delegação mais agressiva **dentro** do domínio delimitado |
| **Curta** | As descrições somam cerca de 900 caracteres, muito abaixo do orçamento de 15 mil tokens do conjunto |

## 2. As duas descrições

**`revisor-codigo`** ([arquivo](../servico-agendamento/.claude/agents/revisor-codigo.md)):

> Revisor de código Python do serviço de agendamento. Use PROATIVAMENTE sempre que o
> desenvolvedor pedir para revisar, auditar ou aprovar código Python (diff, branch, PR, commit
> ou arquivo .py em agendamento/, tests/ ou scripts/) antes de um merge, e logo depois de
> escrever ou alterar código Python. Devolve um parecer com achados por severidade e um
> veredito APROVADO ou MUDANÇAS NECESSÁRIAS. NÃO use para perguntas sobre dados, números de
> ocupação, consultas SQL ou relatórios: isso é do gerador-relatorios.

**`gerador-relatorios`** ([arquivo](../servico-agendamento/.claude/agents/gerador-relatorios.md)):

> Analista de DADOS da agenda do serviço de agendamento. Use PROATIVAMENTE quando o
> desenvolvedor fizer uma pergunta sobre números da agenda (ocupação, horários livres,
> cancelamentos, faltas, demanda por profissional ou por especialidade, comparação entre
> períodos) que se responde consultando o banco local. Devolve tabela + resposta curta. NÃO
> revisa nem escreve código (isso é do revisor-codigo) e NÃO gera o relatório semanal oficial,
> que só o desenvolvedor dispara com /relatorio-ocupacao.

### Por que não se sobrepõem

| Dimensão | `revisor-codigo` | `gerador-relatorios` |
|---|---|---|
| Objeto | **código** (`.py`, diff, branch) | **dados** (o banco local da agenda) |
| Verbo | revisar, auditar, aprovar | perguntar, comparar, contar |
| Saída | parecer + veredito | tabela + resposta |
| Zona ambígua: "SQL" | excluído explicitamente ("NÃO use para ... consultas SQL") | coberto ("se responde consultando o banco") |
| Zona ambígua: "relatório" | excluído explicitamente | perguntas pontuais: sim. **Relatório oficial: não** (fica com a skill explícita do Ex. 1) |
| Modelo / custo | `sonnet` (raciocínio sobre regras) | `haiku` (SELECT + resumo) |

O caso mais perigoso é um pedido como *"revise a consulta SQL de ocupação"*. A palavra "revise"
puxa para o revisor, e "SQL de ocupação" puxa para os dados. A regra escolhida: **revisar um
arquivo `.sql` versionado é revisão de código**, mas o revisor é de *Python*, então o pedido não
casa perfeitamente com nenhum dos dois e o agente principal resolve sozinho ou pergunta. Esse é o
comportamento desejado. É melhor não delegar do que delegar ao especialista errado.

## 3. Testes com pedidos em linguagem natural

Nenhum dos pedidos nomeia um subagente. O resultado é o que o Claude Code fez de fato (sessões
reais, headless).

| # | Pedido do desenvolvedor | Esperado | Selecionado | Sessão |
|---|---|---|---|---|
| A | *"Terminei a sugestão de encaixe de horários na branch feature/encaixe-horarios. Dá uma olhada se está pronta para ir pra main?"* | `revisor-codigo` | **`revisor-codigo`** ✅ | [ex07-a](evidencias/sessoes/ex07-a-selecao-auto-revisao.md) |
| B | *"Qual especialidade teve mais cancelamentos entre 16/11/2026 e 20/11/2026, e quantos foram?"* | `gerador-relatorios` | **`gerador-relatorios`** ✅ | [ex07-b](evidencias/sessoes/ex07-b-selecao-auto-dados.md) |

Registro de cada teste:

- **A**: o pedido não usa as palavras "revisar" nem "código". Mesmo assim, "dá uma olhada se está
  pronta para ir pra main" + "branch" casou com o gatilho *antes de um merge*. Na linha do tempo,
  a primeira ação do agente principal é `Agent {"subagent_type": "revisor-codigo", ...}`. O
  subagente rodou no modelo `claude-sonnet-5-5`, executou `git diff`/`git show` e
  `scripts/checar_branch.py`, e devolveu o parecer com veredito **MUDANÇAS NECESSÁRIAS**.
- **B**: a primeira ação é `Agent {"subagent_type": "gerador-relatorios", ...}`. O subagente rodou
  no `claude-haiku-4-5`, consultou o banco com `scripts/consultar_local.py` e respondeu
  **Dermatologia, 9 cancelamentos** (Pediatria e Cardiologia com 7). O número confere com o
  relatório por especialidade do Ex. 4 (*"Dermatologia ... 9 cancelamentos"*, no mesmo período),
  gerado por um caminho totalmente independente, o script da skill.
- Em nenhum dos dois o agente principal escolheu um subagente embutido (`general-purpose`,
  `Explore`), nem o subagente "vizinho".

### Execução anterior mantida como evidência

A primeira execução do teste A ([`execucoes-anteriores/ex07-a-selecao-auto-revisao-v1.md`](evidencias/execucoes-anteriores/ex07-a-selecao-auto-revisao-v1.md))
**também selecionou o `revisor-codigo`**, então a seleção funcionou desde a primeira versão da
descrição. O que falhou foi a execução dos testes: o revisor tentou `git worktree add` para
rodar o pytest na branch, e o `permissionMode: dontAsk` negou (o comportamento correto do Ex. 8).
O ajuste foi dar ao revisor um caminho sancionado,
[`scripts/checar_branch.py`](../servico-agendamento/scripts/checar_branch.py), liberado no
`settings.json` e citado no prompt, em vez de afrouxar o modo de permissão. Os testes foram
repetidos depois disso.
