# Variação: relatório por profissional

> Carregado sob demanda pela skill `relatorio-ocupacao` só quando `variacao=profissional`.
> Complementa as regras gerais do SKILL.md, sem substituí-las.

## Quando o alvo é um profissional específico

O bloco de dados traz uma linha em "Ocupação por profissional" e o detalhe diário dele.

1. **Título**: `Ocupação de <nome do profissional>: <período>`.
2. **Ficha**: especialidade, turnos (`manha` 08h-12h, `tarde` 13h-18h, de `agendamento/turnos.py`)
   e capacidade total em slots de 30 min.
3. **Tabela diária**: copie o "Detalhe diário por profissional" sem alterar números.
4. **Indicadores**:
   - ocupação do período e situação (`LOTADO`, `normal`, `OCIOSO`);
   - taxa de cancelamento = cancelamentos / (ocupados + cancelamentos);
   - faltas (só existem em dias já passados, antes de 23/11/2026 na base sintética).
5. **Leitura operacional**: no máximo 3 itens.
   - Dia `LOTADO`: sugerir encaixe com outro profissional da mesma especialidade.
   - Dia `OCIOSO`: sugerir abrir o horário para retorno ou teleconsulta.
   - Taxa de cancelamento acima de 10%: sugerir lembrete adicional (`agendamento/notificacoes.py`).

## Quando não há alvo (todos os profissionais)

1. Título `Ocupação por profissional: <período>`.
2. Copie a tabela "Ocupação por profissional" ordenando mentalmente da maior para a menor
   ocupação, mas **sem alterar os números**.
3. Destaque o profissional mais lotado e o mais ocioso. Se forem da mesma especialidade, aponte
   a oportunidade de redistribuir pacientes entre eles.
4. Não reproduza o detalhe diário completo. Cite apenas os dias `LOTADO`.

## Restrições

- Nunca compare profissionais pelo nome em tom de avaliação de desempenho. O relatório trata
  de capacidade da agenda, não de produtividade individual.
- O período vale exatamente como informado. Se o desenvolvedor passou datas, não fale de dias
  fora delas.
