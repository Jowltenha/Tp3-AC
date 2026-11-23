# Ex. 9: Escopos de subagentes e padrão de delegação

## 1. Os escopos disponíveis

O Claude Code procura definições de subagente em cinco lugares. Quando dois arquivos usam o
mesmo `name`, vale o de **maior prioridade**:

| Prioridade | Escopo | Local (Linux/WSL) | Quem enxerga | Quem pode alterar | Versionado? |
|---|---|---|---|---|---|
| 1 | **managed** | `/etc/claude-code/.claude/agents/` (diretório de managed settings, distribuído pela TI) | Todos os usuários da máquina, em todos os projetos | Só a TI (root/MDM) | Fora do repositório; gerenciado pela organização |
| 2 | CLI | `--agents '<json>'` ou `--agents arquivo.json` | Só aquela sessão | Quem lançou o comando | Não |
| 3 | **project** | `<repo>/.claude/agents/` | Quem trabalha **neste repositório** (exige aceitar a confiança na pasta) | Quem faz commit no repositório | **Sim**, via git |
| 4 | **user** | `~/.claude/agents/` | **Um desenvolvedor**, em todos os projetos dele | O próprio desenvolvedor | Não |
| 5 | plugin | `<plugin>/agents/` | Onde o plugin estiver habilitado (`plugin:agente`) | O mantenedor do plugin | No repositório do plugin |

### Critérios para escolher

1. **Abrangência do público:** uma pessoa (user), uma squad ou um repositório (project), ou a
   instituição toda (managed).
2. **Acoplamento ao projeto:** o subagente cita caminhos, regras de negócio, scripts e
   ferramentas MCP de um repositório específico?
3. **Quem precisa poder mudar e quem não pode:** a squad evolui o arquivo por PR (project), ou a
   regra é imposta de fora e não pode ser contornada localmente (managed)?
4. **Rastreabilidade:** a mudança precisa passar por revisão e ficar no histórico do projeto?

## 2. Recomendações

### `revisor-codigo` → **project** (`servico-agendamento/.claude/agents/revisor-codigo.md`)

- **Acoplado ao projeto.** O prompt cita `agendamento/consultas.py`, `turnos.py`, a regra das
  24 h, o ruff com `E,F,I,B,UP`, `.venv/bin/pytest` e `scripts/checar_branch.py`. O
  `disallowedTools` nega `mcp__banco-producao__*`, um servidor que só existe neste
  repositório. Em outro projeto, essas referências estariam erradas ou seriam inúteis.
- **A squad inteira precisa usar a mesma versão.** É o portão de revisão antes do merge. No
  escopo **user**, cada desenvolvedor teria a sua cópia e o critério de aprovação divergiria.
- **Muda por PR, com histórico.** Endurecer uma regra do revisor é decisão da squad e precisa
  ficar no `git log` junto com o código que ele revisa. O commit `31ce15e` deste repositório é
  exatamente isso: um ajuste no revisor, versionado.
- **Por que não managed:** o revisor encarna regras de negócio do agendamento, que não valem para
  outras squads, e a squad precisa iterar sobre ele sem depender da TI.

O mesmo raciocínio vale para o **`gerador-relatorios`** (também project): conhece o esquema
`consultas/profissionais`, o script `scripts/consultar_local.py` e o servidor MCP do projeto.

### `conformidade-seguranca-infnet` → **managed**

Arquivo de referência: [`escopos/managed/agents/conformidade-seguranca-infnet.md`](../escopos/managed/agents/conformidade-seguranca-infnet.md)
(no repositório só como modelo; quem instala em `/etc/claude-code/.claude/agents/` é a TI).

- **Público: toda a instituição.** A Política de Segurança da Informação (PSI-01 a PSI-05:
  segredos, LGPD, dependências, configuração do Claude Code, mínimo privilégio) vale para todas
  as squads do Infnet.
- **Não pode ser sobrescrito nem desligado localmente.** Managed é a maior prioridade. Um
  `.claude/agents/conformidade-seguranca-infnet.md` criado por uma squad, ou um arquivo no
  `~/.claude/agents/` de alguém, perde para a versão da TI. No escopo **project**, qualquer PR
  da squad poderia afrouxar a auditoria do próprio projeto.
- **Uma fonte única.** Atualizar a PSI é um deploy da TI e chega a todas as máquinas, sem abrir
  PR em dezenas de repositórios.
- **Independente das instruções locais.** Com `omitClaudeMd: true`, um subagente **managed** não
  carrega nenhum `CLAUDE.md`, nem os managed. Assim a auditoria não pode ser influenciada por um
  `CLAUDE.md` de projeto ("ignore a pasta X").
- **Por que não plugin:** um plugin também distribui para várias squads, mas o usuário escolhe
  instalar ou desabilitar. Para algo obrigatório, isso não serve.

### `explicador-codigo` → **user** (exemplo)

Arquivo: [`escopos/user/agents/explicador-codigo.md`](../escopos/user/agents/explicador-codigo.md),
instalado em `~/.claude/agents/`. É uma preferência pessoal de trabalho (explicações curtas para
quem está chegando), útil em **todos** os projetos de uma pessoa, mas que não é regra da squad
nem da instituição. Não deve ir para o repositório, onde imporia um gosto individual aos colegas.

## 3. Padrão de delegação

| Subagente | Escopo | Delegação automática (descrição) | Delegação explícita |
|---|---|---|---|
| `revisor-codigo` | project | **Sim**: "Use PROATIVAMENTE ... revisar, auditar ou aprovar código Python ... antes de um merge" | `@agent-revisor-codigo ...` (uma tarefa) e **`/revisar-pr <branch>`** (portão formal) |
| `gerador-relatorios` | project | **Sim**: "Use PROATIVAMENTE ... pergunta sobre números da agenda" | `@agent-gerador-relatorios ...` |
| `relatorio-ocupacao` (skill) | project | **Não**: `disable-model-invocation: true` | `/relatorio-ocupacao ...` |
| `exportar-pacientes` (skill) | project | **Não**: `disable-model-invocation: true` | `/exportar-pacientes ...` |
| `conformidade-seguranca-infnet` | managed | **Sim**: "Use PROATIVAMENTE antes de qualquer commit, push ou PR que mexa em configuração, credenciais ..." | `@agent-conformidade-seguranca-infnet` |
| `explicador-codigo` | user | Sim, mas só para pedidos do tipo "me explica" | `@agent-explicador-codigo` |

### Regra que organiza a tabela

> **Automático quando o efeito é só leitura e o custo de acionar errado é baixo. Explícito quando
> há efeito no processo, dados sensíveis ou uma decisão formal.**

- **Revisão consultiva → automática.** Errar para mais (revisar algo que nem precisava) custa
  alguns tokens de um modelo intermediário, e o revisor não altera nada (`disallowedTools` sem
  `Write/Edit`, `permissionMode: dontAsk`). Errar para menos (o código ir sem revisão) custa
  caro. Por isso a descrição é ampla dentro do seu domínio e começa com "Use PROATIVAMENTE".
- **Portão de merge → explícito.** O parecer que **libera o merge** é um ato formal, como o
  relatório oficial do Ex. 1. Ele fica com a skill [`/revisar-pr`](../servico-agendamento/.claude/skills/revisar-pr/SKILL.md),
  que tem `disable-model-invocation: true`, `context: fork` e `agent: revisor-codigo`. Só o
  desenvolvedor abre o portão, e a revisão roda num subagente `revisor-codigo` **novo**, com o
  mesmo isolamento do Ex. 8. A skill injeta o `git log` e o `git diff --stat` da branch antes de
  delegar.
- **Perguntas sobre dados → automáticas.** O `gerador-relatorios` só lê o banco local, sem a
  tabela `pacientes`, e roda no `haiku`, com custo baixo.
- **Relatório oficial e exportação → só explícitos.** São skills com
  `disable-model-invocation: true` (Ex. 1 e Ex. 5). Nenhuma descrição de subagente cobre esses
  casos. O `gerador-relatorios` diz explicitamente "NÃO gera o relatório semanal oficial".
- **Conformidade → automática e obrigatória.** A descrição gerenciada aciona a auditoria em todo
  commit sensível, de qualquer squad. Como vive em managed, nenhuma squad remove o gatilho.

### Evidência das três formas de acionar o `revisor-codigo`

| Forma | Pedido | O que aconteceu | Sessão |
|---|---|---|---|
| **Automática** (descrição) | *"Dá uma olhada se está pronta para ir pra main?"* | O agente principal escolheu `revisor-codigo` sozinho | [ex07-a](evidencias/sessoes/ex07-a-selecao-auto-revisao.md) |
| **Explícita** por @-menção | `@agent-revisor-codigo revise ... antes do merge` | O agente principal delegou ao subagente nomeado | [ex06](evidencias/sessoes/ex06-revisor-explicito.md) |
| **Explícita formal** (portão de merge) | `/revisar-pr feature/encaixe-horarios` | A skill rodou **direto** num `revisor-codigo` novo. O agente principal nem chamou o modelo (zero ferramentas carregadas na sessão principal) | [ex09](evidencias/sessoes/ex09-revisar-pr-delegacao-explicita.md) |

No `/revisar-pr`, a **primeira e única mensagem** do subagente é o corpo da skill renderizado,
com o `git log` e o `git diff --stat` injetados:

```text
Revise a branch `feature/encaixe-horarios` antes do merge na `main`.
Commits da branch:
55fc9c1 feat(agendamento): sugestão de encaixe de horário
Arquivos alterados:
 servico-agendamento/agendamento/encaixe.py | 31 +++++
 servico-agendamento/tests/test_encaixe.py  | 13 +++
```

O subagente rodou `checar_branch.py` (ruff ok, 6 testes passando), leu `consultas.py` e
`turnos.py` e devolveu **MUDANÇAS NECESSÁRIAS** com os mesmos três achados críticos, agora com
as linhas certas (`encaixe.py:30`, `:18`, `:19-21`). `permission_denials: []`.

As três formas chegam ao **mesmo subagente, com o mesmo isolamento e o mesmo critério**, porque
existe uma única definição em escopo project.

### Como as duas formas convivem sem conflito

1. **As descrições não se sobrepõem** (Ex. 7): cada uma diz quando usar e **quando não usar**,
   apontando o vizinho. O roteamento automático tem um único candidato por pedido.
2. **O explícito sempre vence o automático.** Uma `@-menção` força aquele subagente. `/revisar-pr`
   força o fluxo formal. Quando o desenvolvedor quer controle, ele nomeia o artefato.
3. **Quando o explícito é o único caminho, isso é aplicado pelo Claude Code, não pela
   descrição.** Para o que **não pode** ser automático, o padrão não confia na redação da
   descrição: usa `disable-model-invocation: true`. Esse campo também impede que a skill seja
   pré-carregada em subagentes.

## 4. Justificativa final: escopo e delegação são a mesma decisão

| Subagente | Escopo | Por que o escopo sustenta a delegação escolhida |
|---|---|---|
| `revisor-codigo` | project | A delegação **automática** depende de a descrição ser **a mesma para toda a squad**: o mesmo pedido precisa cair no mesmo revisor, com o mesmo critério, em qualquer máquina. Só project garante isso, porque o arquivo vem com o `git clone`. A delegação **explícita** formal (`/revisar-pr`, com `agent: revisor-codigo`) referencia o subagente **pelo nome**, então precisa que ele exista com esse nome em todo checkout, o que project também garante. No escopo user, `/revisar-pr` quebraria na máquina de quem não tem o arquivo |
| `gerador-relatorios` | project | A descrição dele foi escrita **em contraste** com a do `revisor-codigo` ("NÃO revisa nem escreve código"). A não-sobreposição só funciona se os dois estiverem sempre juntos, na mesma versão. Por isso ficam no mesmo escopo e evoluem no mesmo PR |
| `conformidade-seguranca-infnet` | managed | A delegação é **automática e obrigatória**. O gatilho ("antes de qualquer commit, push ou PR...") precisa existir em toda squad e **não pode ser editado** por ela. Managed é o único escopo que distribui para todos **e** tem prioridade sobre project e user. Num escopo mais baixo, o gatilho automático viraria opcional |
| `explicador-codigo` | user | Delegação automática **pessoal**: o gatilho "me explica" reflete o jeito de trabalhar de uma pessoa. No escopo project, a descrição dele passaria a competir no roteamento de toda a squad, e "explica esse diff" poderia cair nele em vez do revisor |

**Coerência em uma frase:** *quanto mais pessoas dependem de um gatilho automático ser previsível,
mais alto o escopo precisa estar; e o que só pode ser disparado explicitamente nunca depende de
escopo nem de descrição, porque é travado no próprio artefato (`disable-model-invocation`).*

Consequências práticas que este repositório já segue:

- Os dois subagentes de projeto e as três skills ficam em `servico-agendamento/.claude/`, versionados
  e revisados no mesmo fluxo de PR do código (commits `bd9e676` e `31ce15e`).
- Os nomes são únicos entre escopos (`revisor-codigo` ≠ `conformidade-seguranca-infnet` ≠
  `explicador-codigo`), então a precedência nunca esconde um subagente por acidente. A exceção é
  proposital: se uma squad tentar criar um `conformidade-seguranca-infnet` próprio, a versão
  managed vence.
- O orçamento de descrições (cerca de 15 mil tokens no total, com aviso na inicialização) fica
  tranquilo: as descrições são curtas, e os detalhes estão no corpo de cada `.md`, que só carrega
  quando o subagente roda.
