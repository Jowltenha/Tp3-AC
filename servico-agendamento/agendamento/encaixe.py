"""Sugestão de encaixe: primeiro horário livre de um médico em um dia."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from agendamento.consultas import Consulta
from agendamento.turnos import TURNOS

DURACAO = 30


def horarios_livres(agenda: list[Consulta], medico_id: int, dia: date):
    livres = []
    for inicio, fim in TURNOS.values():
        atual = datetime.combine(dia, inicio)
        limite = datetime.combine(dia, fim)
        while atual <= limite:
            ocupado = any(
                c.medico_id == medico_id and c.inicio == atual for c in agenda
            )
            if not ocupado:
                livres.append(atual)
            atual += timedelta(minutes=DURACAO)
    return livres


def sugerir_encaixe(agenda, medico_id, dia, paciente_nome, paciente_cpf):
    livres = horarios_livres(agenda, medico_id, dia)
    print(f"Encaixe para {paciente_nome} (CPF {paciente_cpf}): {len(livres)} horários livres")
    return livres[0]
