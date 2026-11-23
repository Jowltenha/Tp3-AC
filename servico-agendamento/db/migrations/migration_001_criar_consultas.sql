-- migration_001: cria a tabela de consultas
CREATE TABLE consultas (
    id          SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL,
    medico_id   INTEGER NOT NULL,
    inicio      TIMESTAMP NOT NULL,
    duracao_min INTEGER NOT NULL DEFAULT 30,
    status      VARCHAR(20) NOT NULL DEFAULT 'agendada'
);
