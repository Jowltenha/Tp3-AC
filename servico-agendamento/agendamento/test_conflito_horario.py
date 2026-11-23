"""Teste colocalizado ao módulo (convenção de formatação própria: tabela alinhada à mão)."""

from datetime import datetime

from agendamento.consultas import Consulta, conflita

BASE = datetime(2026, 12, 1, 9, 0)

CASOS = [
    #  medico_a  min_a  medico_b  min_b  conflita?
    (  7,        0,     7,        15,    True ),
    (  7,        0,     7,        30,    False),
    (  7,        0,     8,        0,     False),
    (  7,        0,     7,        29,    True ),
]


def test_tabela_de_conflitos():
    for med_a, min_a, med_b, min_b, esperado in CASOS:
        a = Consulta(1, 1, med_a, BASE.replace(minute=min_a))
        b = Consulta(2, 2, med_b, BASE.replace(minute=min_b))
        assert conflita(a, b) is esperado
