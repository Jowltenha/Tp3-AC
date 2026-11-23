from datetime import datetime, timedelta

import pytest

from agendamento.consultas import Consulta, agendar, cancelar
from agendamento.notificacoes import mensagem_lembrete

BASE = datetime(2026, 12, 1, 9, 0)


def test_agendar_sem_conflito():
    agenda = [Consulta(1, 10, 7, BASE)]
    agendar(agenda, Consulta(2, 11, 7, BASE + timedelta(minutes=30)))
    assert len(agenda) == 2


def test_agendar_com_conflito():
    agenda = [Consulta(1, 10, 7, BASE)]
    with pytest.raises(ValueError):
        agendar(agenda, Consulta(2, 11, 7, BASE + timedelta(minutes=15)))


def test_cancelar_exige_antecedencia():
    with pytest.raises(ValueError):
        cancelar(Consulta(1, 10, 7, BASE), agora=BASE - timedelta(hours=2))


def test_lembrete_usa_so_primeiro_nome():
    texto = mensagem_lembrete(Consulta(1, 10, 7, BASE), "Maria da Silva")
    assert "Maria" in texto and "Silva" not in texto
