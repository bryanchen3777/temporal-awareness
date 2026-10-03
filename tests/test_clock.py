"""Clock behaviour: timezone handling, determinism, DST."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from conftest import NY, TOKYO, ny, tokyo

from temporal_awareness import FixedClock, SystemClock, TemporalContext, resolve_tz


class TestResolveTz:
    def test_none_defaults_to_utc_not_system_local(self):
        assert resolve_tz(None) is timezone.utc

    def test_string_resolves_to_zoneinfo(self):
        assert getattr(resolve_tz("America/New_York"), "key", None) == "America/New_York"

    def test_tzinfo_passes_through(self):
        assert resolve_tz(NY) is NY

    def test_unknown_timezone_raises(self):
        with pytest.raises(ValueError, match="unknown timezone"):
            resolve_tz("Mars/Olympus_Mons")

    def test_bad_type_raises(self):
        with pytest.raises(TypeError):
            resolve_tz(42)  # type: ignore[arg-type]

    def test_system_local_requires_opt_in(self):
        opted_in = resolve_tz(None, assume_system_local=True)
        assert opted_in is not None


class TestFixedClock:
    def test_returns_frozen_moment(self, saturday_afternoon):
        clock = FixedClock(saturday_afternoon)
        assert clock.now() == saturday_afternoon
        assert clock.now() == saturday_afternoon
        assert clock() == saturday_afternoon

    def test_rejects_naive_datetime(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            FixedClock(datetime(2026, 10, 3, 14, 22))

    def test_set_replaces_moment(self, saturday_afternoon):
        clock = FixedClock(saturday_afternoon)
        clock.set(ny(2027, 1, 1, 8, 0))
        assert clock.now().year == 2027

    def test_set_rejects_naive(self, saturday_afternoon):
        clock = FixedClock(saturday_afternoon)
        with pytest.raises(ValueError, match="timezone-aware"):
            clock.set(datetime(2027, 1, 1, 8, 0))

    def test_step_advances_on_each_read(self, saturday_afternoon):
        clock = FixedClock(saturday_afternoon, step=timedelta(minutes=30))
        assert clock.now().minute == 22
        assert clock.now().minute == 52
        assert clock.now().hour == 15

    def test_tz_property(self, saturday_afternoon):
        assert FixedClock(saturday_afternoon).tz is NY


class TestSystemClock:
    def test_returns_timezone_aware_datetime(self):
        moment = SystemClock("Asia/Tokyo").now()
        assert moment.tzinfo is not None
        assert moment.utcoffset() is not None

    def test_uses_requested_timezone(self):
        moment = SystemClock("Asia/Tokyo").now()
        assert getattr(moment.tzinfo, "key", None) == "Asia/Tokyo"

    def test_repr_mentions_timezone(self):
        assert "Asia/Tokyo" in repr(SystemClock("Asia/Tokyo"))


class TestTimezoneHandling:
    def test_same_instant_renders_per_local_timezone(self):
        instant = datetime(2026, 10, 3, 18, 22, 31, tzinfo=timezone.utc)

        ny_ctx = TemporalContext.from_datetime(instant.astimezone(NY))
        tokyo_ctx = TemporalContext.from_datetime(instant.astimezone(TOKYO))

        assert ny_ctx.coarse_time == "around 2:15 PM"
        # 03:22 JST lands in the small hours, so it degrades to a phrase.
        assert tokyo_ctx.coarse_time == "early morning hours"
        assert ny_ctx.weekday == "Saturday"
        assert ny_ctx.date == "2026-10-03"
        # 03:22 JST is already the next calendar day in Tokyo.
        assert tokyo_ctx.weekday == "Sunday"
        assert tokyo_ctx.date == "2026-10-04"
        assert ny_ctx.timezone == "America/New_York"
        assert tokyo_ctx.timezone == "Asia/Tokyo"

    def test_day_offset_can_differ_by_timezone(self):
        # 2026-10-03 23:30 in Tokyo is still 2026-10-03 10:30 in New York,
        # but 2026-10-04 23:30 in Tokyo is 2026-10-04 in New York too. The
        # local date is what drives day relations.
        tokyo_late = tokyo(2026, 10, 4, 23, 30)
        ny_ctx = TemporalContext.from_datetime(tokyo_late.astimezone(NY))
        assert ny_ctx.date == "2026-10-04"

    def test_utc_offset_timezone_is_named(self):
        ctx = TemporalContext.from_datetime(
            datetime(2026, 10, 3, 14, 22, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        )
        assert ctx.timezone == "UTC+05:30"
        assert ctx.coarse_time == "around 2:15 PM"


class TestDeterminism:
    def test_same_timestamp_same_output(self, saturday_afternoon):
        first = TemporalContext.now(FixedClock(saturday_afternoon))
        second = TemporalContext.now(FixedClock(saturday_afternoon))
        assert first == second
        assert first.as_prompt_context() == second.as_prompt_context()
        assert first.as_dict() == second.as_dict()

    def test_frozen_context_is_hashable(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert {ctx, TemporalContext.from_datetime(saturday_afternoon)} == {ctx}
