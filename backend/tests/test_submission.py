"""Tests for submission payload helpers."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.submission import apply_date_strategy, apply_weekly_times


def test_apply_weekly_times_uses_weekday():
    payload = {
        "motivo": "Trabalho",
        "weekly_times": {
            "0": {"hora_saida": "06:45", "hora_retorno": "12:00"},
            "1": {"hora_saida": "07:00", "hora_retorno": "13:00"},
        },
    }
    # 2026-06-15 is a Monday (weekday 0)
    monday = datetime(2026, 6, 15, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    result = apply_weekly_times(payload, when=monday)
    assert "weekly_times" not in result
    assert result["hora_saida"] == "06:45"
    assert result["hora_retorno"] == "12:00"


def test_apply_weekly_times_keeps_inline_when_no_match():
    payload = {
        "hora_saida": "18:00",
        "hora_retorno": "21:00",
        "weekly_times": {"0": {"hora_saida": "06:45", "hora_retorno": "12:00"}},
    }
    # 2026-06-16 is Tuesday (weekday 1) — no entry in weekly_times
    tuesday = datetime(2026, 6, 16, 12, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    result = apply_weekly_times(payload, when=tuesday)
    assert result["hora_saida"] == "18:00"
    assert result["hora_retorno"] == "21:00"


def test_apply_date_strategy_today():
    payload = {"data_saida": "2020-01-01"}
    result = apply_date_strategy(payload, "today")
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    assert result["data_saida"] == today
