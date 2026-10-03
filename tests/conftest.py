"""Shared fixtures.

Every test that touches time uses a fixed, timezone-aware moment. No test is
allowed to depend on the real wall clock except the one that explicitly
verifies SystemClock is timezone-aware.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from temporal_awareness import FixedClock  # noqa: E402

NY = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")


def ny(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=NY)


def tokyo(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=TOKYO)


@pytest.fixture
def saturday_afternoon():
    """2026-10-03 14:22:31 America/New_York — the README's example instant."""

    return ny(2026, 10, 3, 14, 22, 31)


@pytest.fixture
def clock(saturday_afternoon):
    return FixedClock(saturday_afternoon)
