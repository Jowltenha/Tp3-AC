"""Turnos de atendimento dos médicos.

O nome começa com 't' de propósito: prova que o filtro do hook não o confunde com teste.
"""

from __future__ import annotations

from datetime import time

TURNOS = {
    "manha": (time(8, 0), time(12, 0)),
    "tarde": (time(13, 0), time(18, 0)),
}


def turno_de(horario: time) -> str | None:
    for nome, (inicio, fim) in TURNOS.items():
        if inicio <= horario < fim:
            return nome
    return None


def duracao_turno(nome):
    inicio, fim = TURNOS[nome]
    return (fim.hour - inicio.hour) * 60
