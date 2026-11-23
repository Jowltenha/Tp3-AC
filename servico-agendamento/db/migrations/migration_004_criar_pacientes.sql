-- migration_004: pacientes (dados pessoais; acesso restrito, ver skill exportar-pacientes)
CREATE TABLE pacientes (
    id              INTEGER PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    cpf             VARCHAR(14)  NOT NULL,
    data_nascimento DATE         NOT NULL,
    telefone        VARCHAR(20)  NOT NULL,
    convenio        VARCHAR(40)  NOT NULL
);
