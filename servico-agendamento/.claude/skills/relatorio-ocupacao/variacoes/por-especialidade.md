# Variação: relatório por especialidade médica

> Carregado sob demanda pela skill `relatorio-ocupacao` só quando `variacao=especialidade`.
> Complementa as regras gerais do SKILL.md, sem substituí-las.

## Formato

1. **Título**: `Ocupação por especialidade: <período>`. Se houver alvo, use
   `Ocupação de <especialidade>: <período>`.
2. **Tabela**: copie "Ocupação por especialidade" do bloco de dados sem alterar números.
3. **Ranking de pressão de demanda**: liste as especialidades da maior para a menor ocupação,
   no formato `<especialidade>: <ocupação> (<situação>)`.
4. **Desequilíbrio interno**: para cada especialidade com 2 ou mais profissionais, diga quem é
   o "Mais demandado" e se vale redistribuir pacientes dentro da especialidade.
5. **Recomendação de capacidade** (no máximo 3 itens, só com base nos números):
   - especialidade `LOTADO`: avaliar turno extra ou novo profissional;
   - especialidade `OCIOSO`: avaliar reduzir turnos ou divulgar a agenda;
   - cancelamentos altos (mais de 10% dos ocupados): revisar o lembrete de consulta.

## Restrições

- Especialidades válidas na base: Cardiologia, Dermatologia, Ortopedia, Pediatria. Se o script
  devolveu `ERRO DE PARÂMETRO` por especialidade inexistente, repasse a lista ao desenvolvedor.
- Não detalhe ocupação por dia nesta variação. Quem precisar do dia a dia usa a variação
  `profissional` ou a `basico`.
