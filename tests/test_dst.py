"""DST-sensitive behaviour, explicitly required by the work order."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from conftest import NY, ny

from temporal_awareness import FixedClock, SystemClock, TemporalContext, format_coarse_time

# 2026 US DST transitions in America/New_York:
#   spring forward: 2026-03-08  02:00 -> 03:00  (a 1-hour gap, 23h day)
#   fall back:      2026-11-01  02:00 -> 01:00  (a 1-hour repeat, 25h day)
SPRING_FORWARD_DATE = (2026, 3, 8)
FALL_BACK_DATE = (2026, 11, 1)


class TestSpringForward:
    def test_nonexistent_local_time_is_accepted_and_normalized(self):
        # 02:30 does not exist on this date; zoneinfo resolves it forward.
        moment = datetime(2026, 3, 8, 2, 30, tzinfo=NY)
        ctx = TemporalContext.from_datetime(moment)
        assert ctx.timezone == "America/New_York"
        assert ctx.exact_timestamp.startswith("2026-03-08T02:30:00")
        # The coarse rendering is still a valid, human-scale value.
        assert "around" in ctx.coarse_time or "night" in ctx.coarse_time

    def test_day_is_23_hours_but_fraction_stays_in_range(self):
        start = datetime(2026, 3, 8, 0, 0, tzinfo=NY).astimezone(timezone.utc)
        end = datetime(2026, 3, 8, 23, 59, 59, tzinfo=NY).astimezone(timezone.utc)
        assert (end - start) < timedelta(hours=24)
        for hour in range(24):
            moment = datetime(2026, 3, 8, hour, 0, tzinfo=NY)
            ctx = TemporalContext.from_datetime(moment)
            assert 0.0 <= ctx.elapsed_day_fraction < 1.0

    def test_offset_before_and_after_transition(self):
        before = datetime(2026, 3, 8, 1, 30, tzinfo=NY).utcoffset()
        after = datetime(2026, 3, 8, 3, 30, tzinfo=NY).utcoffset()
        assert before == timedelta(hours=-5)
        assert after == timedelta(hours=-4)

    def test_wall_clock_arithmetic_crosses_the_gap_without_raising(self):
        # datetime + timedelta is wall-clock arithmetic within one zone, so
        # 01:30 + 1h lands on the nonexistent 02:30 rather than raising.
        # The library must survive that and still render valid output.
        moment = datetime(2026, 3, 8, 1, 30, tzinfo=NY) + timedelta(hours=1)
        assert moment.hour == 2
        ctx = TemporalContext.from_datetime(moment)
        assert ctx.date == "2026-03-08"
        assert 0.0 <= ctx.elapsed_day_fraction < 1.0

    def test_absolute_time_arithmetic_skips_the_gap(self):
        # Converting to UTC first gives true elapsed time: 01:30 EST + 1h is
        # 03:30 EDT. Both paths are supported; callers pick by intent.
        utc_start = datetime(2026, 3, 8, 1, 30, tzinfo=NY).astimezone(timezone.utc)
        after = (utc_start + timedelta(hours=1)).astimezone(NY)
        assert after.hour == 3
        assert after.minute == 30
        assert after.utcoffset() == timedelta(hours=-4)

    def test_fixed_clock_step_is_wall_clock(self):
        clock = FixedClock(datetime(2026, 3, 8, 1, 30, tzinfo=NY), step=timedelta(hours=1))
        hours = [clock.now().hour for _ in range(3)]
        assert hours == [1, 2, 3]


class TestFallBack:
    def test_ambiguous_local_time_resolves_to_earlier_offset(self):
        moment = datetime(2026, 11, 1, 1, 30, tzinfo=NY)
        assert moment.utcoffset() == timedelta(hours=-4)  # EDT, first occurrence

    def test_offsets_differ_within_the_repeated_hour(self):
        edt = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=0)
        est = datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=1)
        assert edt.utcoffset() != est.utcoffset()
        assert est.astimezone(timezone.utc) > edt.astimezone(timezone.utc)

    def test_day_is_25_hours_but_fraction_stays_in_range(self):
        # Measured in UTC, because subtracting two same-zone datetimes is
        # wall-clock arithmetic and hides the extra hour.
        start = datetime(2026, 11, 1, 0, 0, tzinfo=NY).astimezone(timezone.utc)
        end = datetime(2026, 11, 1, 23, 59, 59, tzinfo=NY).astimezone(timezone.utc)
        assert (end - start) > timedelta(hours=24)
        for hour in range(24):
            ctx = TemporalContext.from_datetime(datetime(2026, 11, 1, hour, 0, tzinfo=NY))
            assert 0.0 <= ctx.elapsed_day_fraction < 1.0

    def test_repeated_hour_still_classifies_identically(self):
        first = TemporalContext.from_datetime(datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=0))
        second = TemporalContext.from_datetime(datetime(2026, 11, 1, 1, 30, tzinfo=NY, fold=1))
        assert first.time_of_day == second.time_of_day
        assert first.coarse_time == second.coarse_time
        assert first.day_progress == second.day_progress


class TestOtherZones:
    def test_europe_berlin_spring_forward_has_no_2am(self):
        from zoneinfo import ZoneInfo

        berlin = ZoneInfo("Europe/Berlin")
        moment = datetime(2026, 3, 29, 2, 30, tzinfo=berlin)
        ctx = TemporalContext.from_datetime(moment)
        assert ctx.timezone == "Europe/Berlin"
        assert 0.0 <= ctx.elapsed_day_fraction < 1.0

    def test_southern_hemisphere_dst_does_not_break_fractions(self):
        from zoneinfo import ZoneInfo

        sydney = ZoneInfo("Australia/Sydney")
        for hour in range(24):
            ctx = TemporalContext.from_datetime(datetime(2026, 10, 4, hour, 0, tzinfo=sydney))
            assert 0.0 <= ctx.elapsed_day_fraction < 1.0
            assert ctx.time_of_day in {"morning", "afternoon", "evening", "night"}

    def test_zone_without_dst_is_unaffected(self):
        from zoneinfo import ZoneInfo

        tokyo = ZoneInfo("Asia/Tokyo")
        assert datetime(2026, 3, 8, 3, 0, tzinfo=tokyo).utcoffset() == timedelta(hours=9)
        assert datetime(2026, 11, 1, 3, 0, tzinfo=tokyo).utcoffset() == timedelta(hours=9)

    def test_fixed_offset_timezone_never_transitions(self):
        plus9 = timezone(timedelta(hours=9))
        for month in range(1, 13):
            moment = datetime(2026, month, 15, 12, 0, tzinfo=plus9)
            assert moment.utcoffset() == timedelta(hours=9)


class TestDeterminismAcrossDst:
    def test_same_wall_clock_always_renders_identically(self):
        moment = datetime(2026, 3, 8, 2, 30, tzinfo=NY)
        renders = {format_coarse_time(moment) for _ in range(50)}
        assert len(renders) == 1

    def test_context_built_twice_across_a_transition_is_stable(self):
        ctx = TemporalContext.from_datetime(datetime(2026, 11, 1, 1, 30, tzinfo=NY))
        assert ctx.as_dict() == TemporalContext.from_datetime(
            datetime(2026, 11, 1, 1, 30, tzinfo=NY)
        ).as_dict()

    def test_system_clock_always_returns_aware_datetime_across_year(self):
        clock = SystemClock("America/New_York")
        for _ in range(20):
            assert clock.now().utcoffset() is not None
