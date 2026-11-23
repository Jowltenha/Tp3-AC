-- Consulta de leitura usada pelo analista de dados e pela skill relatorio-ocupacao
-- (TP3: acrescentada a coluna minutos_ocupados, necessária para a taxa de ocupação)
SELECT medico_id, dia, consultas, minutos_ocupados
FROM vw_ocupacao_diaria
WHERE dia BETWEEN :inicio AND :fim
ORDER BY dia, medico_id;
