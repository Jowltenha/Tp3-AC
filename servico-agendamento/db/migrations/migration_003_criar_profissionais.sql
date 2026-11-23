-- migration_003: profissionais (médicos) e suas especialidades/turnos
CREATE TABLE profissionais (
    id            INTEGER PRIMARY KEY,
    nome          VARCHAR(120) NOT NULL,
    especialidade VARCHAR(60)  NOT NULL,
    turnos        VARCHAR(40)  NOT NULL DEFAULT 'manha,tarde'  -- chaves de agendamento.turnos.TURNOS
);
