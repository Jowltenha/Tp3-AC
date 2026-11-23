from datetime import date, datetime

from agendamento.consultas import Consulta
from agendamento.encaixe import sugerir_encaixe

DIA = date(2026, 12, 1)


def test_sugere_primeiro_horario_livre():
    agenda = [Consulta(1, 10, 7, datetime(2026, 12, 1, 8, 0))]
    assert sugerir_encaixe(agenda, 7, DIA, "Maria da Silva", "000.111.222-33") == datetime(
        2026, 12, 1, 8, 30
    )
