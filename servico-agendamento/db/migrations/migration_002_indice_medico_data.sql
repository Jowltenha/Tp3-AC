-- migration_002: índice para busca de agenda por médico e data
CREATE INDEX idx_consultas_medico_inicio ON consultas (medico_id, inicio);
