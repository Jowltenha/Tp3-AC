#!/usr/bin/env python3
"""Gera os dados SINTÉTICOS de agenda usados pelo TP3 (determinístico: semente fixa).

Saída:
  dados/profissionais.csv          profissionais, especialidades e turnos (não sensível)
  dados/consultas.csv              agendamentos de 16/11/2026 a 04/12/2026 (não sensível: só ids)
  dados-sensiveis/pacientes.csv    pacientes fictícios com nome/CPF/telefone (sensível por formato)

A data de referência é fixa (23/11/2026), e não `date.today()`, para que qualquer pessoa
que rode o script obtenha exatamente os mesmos dados que aparecem nas evidências.

Uso: python3 scripts/gerar_dados_sinteticos.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SEMENTE = 20261123
REFERENCIA = date(2026, 11, 23)  # "hoje" dos dados: antes disso as consultas já aconteceram
INICIO, FIM = date(2026, 11, 16), date(2026, 12, 4)

# id, nome, especialidade, turnos, taxa-alvo de ocupação (perfil sintético)
PROFISSIONAIS = [
    (1, "Dra. Helena Prado", "Cardiologia", "manha,tarde", 0.88),
    (2, "Dr. Marcos Teixeira", "Cardiologia", "manha", 0.62),
    (3, "Dra. Beatriz Nunes", "Dermatologia", "tarde", 0.95),
    (4, "Dr. Rafael Costa", "Dermatologia", "manha,tarde", 0.45),
    (5, "Dra. Luísa Martins", "Pediatria", "manha,tarde", 0.76),
    (6, "Dr. Otávio Ramos", "Ortopedia", "tarde", 0.32),
]
TURNOS = {"manha": (time(8, 0), time(12, 0)), "tarde": (time(13, 0), time(18, 0))}
DURACAO_MIN = 30

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo", "Íris", "João",
         "Karina", "Leonardo", "Marina", "Nelson", "Olívia", "Paulo", "Quitéria", "Renato",
         "Sílvia", "Tiago"]
SOBRENOMES = ["Sintética", "Fictício", "Exemplo", "Simulado", "Teste"]
FAMILIAS = ["Rocha", "Lima", "Souza", "Alves", "Pereira", "Gomes", "Ribeiro", "Carvalho"]
CONVENIOS = ["Plano Ouro", "Plano Prata", "Particular", "Plano Bronze"]


def slots(turnos: str, dia: date) -> list[datetime]:
    resultado = []
    for turno in turnos.split(","):
        inicio, fim = TURNOS[turno]
        atual = datetime.combine(dia, inicio)
        while atual + timedelta(minutes=DURACAO_MIN) <= datetime.combine(dia, fim):
            resultado.append(atual)
            atual += timedelta(minutes=DURACAO_MIN)
    return resultado


def main() -> None:
    rnd = random.Random(SEMENTE)
    (RAIZ / "dados").mkdir(exist_ok=True)
    (RAIZ / "dados-sensiveis").mkdir(exist_ok=True)

    with (RAIZ / "dados/profissionais.csv").open("w", newline="", encoding="utf-8") as arq:
        w = csv.writer(arq, delimiter=";")
        w.writerow(["id", "nome", "especialidade", "turnos"])
        for pid, nome, esp, turnos, _ in PROFISSIONAIS:
            w.writerow([pid, nome, esp, turnos])

    pacientes = []
    for i in range(1, 61):
        nome = f"{rnd.choice(NOMES)} {rnd.choice(SOBRENOMES)} {rnd.choice(FAMILIAS)}"
        cpf = f"000.{i:03d}.{rnd.randint(100, 999)}-{rnd.randint(10, 99)}"
        nasc = date(rnd.randint(1950, 2022), rnd.randint(1, 12), rnd.randint(1, 28))
        tel = f"(21) 90000-{i:04d}"
        pacientes.append([i, nome, cpf, nasc.isoformat(), tel, rnd.choice(CONVENIOS)])
    with (RAIZ / "dados-sensiveis/pacientes.csv").open("w", newline="", encoding="utf-8") as arq:
        w = csv.writer(arq, delimiter=";")
        w.writerow(["id", "nome", "cpf", "data_nascimento", "telefone", "convenio"])
        w.writerows(pacientes)

    consultas, cid = [], 1
    dia = INICIO
    while dia <= FIM:
        if dia.weekday() < 5:
            for pid, _, _, turnos, taxa in PROFISSIONAIS:
                for inicio in slots(turnos, dia):
                    if rnd.random() >= taxa:
                        continue
                    sorte = rnd.random()
                    if sorte < 0.07:
                        status = "cancelada"
                    elif dia < REFERENCIA:
                        status = "falta" if sorte < 0.12 else "realizada"
                    else:
                        status = "agendada"
                    consultas.append(
                        [cid, rnd.randint(1, 60), pid, inicio.isoformat(sep=" "), DURACAO_MIN, status]
                    )
                    cid += 1
        dia += timedelta(days=1)
    with (RAIZ / "dados/consultas.csv").open("w", newline="", encoding="utf-8") as arq:
        w = csv.writer(arq, delimiter=";")
        w.writerow(["id", "paciente_id", "medico_id", "inicio", "duracao_min", "status"])
        w.writerows(consultas)

    print(f"{len(PROFISSIONAIS)} profissionais, {len(pacientes)} pacientes, {len(consultas)} consultas")


if __name__ == "__main__":
    main()
