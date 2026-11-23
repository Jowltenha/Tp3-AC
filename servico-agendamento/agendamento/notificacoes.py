"""Mensagens de lembrete enviadas aos pacientes (LGPD: só o primeiro nome)."""

from __future__ import annotations

from agendamento.consultas import Consulta


def mensagem_lembrete(consulta: Consulta, nome_paciente: str) -> str:
    """Monta o texto do lembrete sem expor dados além do primeiro nome."""
    primeiro_nome = nome_paciente.split()[0]
    return f"Olá, {primeiro_nome}! Lembrete da sua consulta em {consulta.inicio:%d/%m/%Y às %H:%M}."
