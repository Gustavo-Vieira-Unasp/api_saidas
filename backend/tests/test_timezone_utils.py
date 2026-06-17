"""Tests for schedule timezone normalization."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.timezone_utils import to_scheduler_naive


def test_to_scheduler_naive_keeps_local_wall_clock():
    local = datetime(2026, 6, 17, 17, 3)
    assert to_scheduler_naive(local) == local


def test_to_scheduler_naive_converts_utc_to_brt():
    utc = datetime(2026, 6, 17, 20, 3, tzinfo=ZoneInfo("UTC"))
    assert to_scheduler_naive(utc) == datetime(2026, 6, 17, 17, 3)


def test_to_scheduler_naive_converts_brt_aware_to_naive():
    brt = datetime(2026, 6, 17, 17, 3, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert to_scheduler_naive(brt) == datetime(2026, 6, 17, 17, 3)


def test_to_scheduler_iso_includes_brt_offset():
    from app.core.timezone_utils import to_scheduler_iso

    assert to_scheduler_iso(datetime(2026, 6, 17, 17, 3)) == (
        "2026-06-17T17:03:00-03:00"
    )


def test_to_utc_iso_appends_z():
    from app.core.timezone_utils import to_utc_iso

    assert to_utc_iso(datetime(2026, 6, 17, 20, 3)) == "2026-06-17T20:03:00Z"
