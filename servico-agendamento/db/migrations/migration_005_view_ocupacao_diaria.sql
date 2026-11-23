-- migration_005: view usada por db/consultas/ocupacao_por_medico.sql
-- Consulta cancelada libera o horário; agendada, realizada e falta ocupam.
CREATE VIEW vw_ocupacao_diaria AS
SELECT medico_id,
       date(inicio)     AS dia,
       COUNT(*)         AS consultas,
       SUM(duracao_min) AS minutos_ocupados
FROM consultas
WHERE status <> 'cancelada'
GROUP BY medico_id, date(inicio);
