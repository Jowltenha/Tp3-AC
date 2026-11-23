"""Regras de agendamento e cancelamento de consultas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

ANTECEDENCIA_MINIMA_CANCELAMENTO = timedelta(hours=24)


@dataclass
class Consulta:
    id: int
    paciente_id: int
    medico_id: int
    inicio: datetime
    duracao_min: int = 30
    status: str = "agendada"

    @property
    def fim(self) -> datetime:
        return self.inicio + timedelta(minutes=self.duracao_min)


def conflita(a: Consulta, b: Consulta) -> bool:
    """Duas consultas do mesmo médico conflitam quando os intervalos [inicio, fim) se sobrepõem."""
    if a.medico_id != b.medico_id:
        return False
    return a.inicio < b.fim and b.inicio < a.fim


def agendar(agenda: list[Consulta], nova: Consulta) -> Consulta:
    """Inclui ``nova`` na agenda, recusando conflito de horário."""
    for existente in agenda:
        if existente.status == "agendada" and conflita(existente, nova):
            raise ValueError(f"Conflito com a consulta {existente.id} do médico {nova.medico_id}")
    agenda.append(nova)
    return nova


def cancelar(consulta: Consulta, agora: datetime) -> Consulta:
    """Cancela respeitando a antecedência mínima de 24 h (regra do contrato)."""
    if consulta.inicio - agora < ANTECEDENCIA_MINIMA_CANCELAMENTO:
        raise ValueError("Cancelamento exige 24 h de antecedência")
    consulta.status = "cancelada"
    return consulta
