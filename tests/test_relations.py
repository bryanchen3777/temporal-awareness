"""Temporal relations: today / tomorrow / yesterday / earlier / later / tonight."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from conftest import NY, TOKYO, ny, tokyo

from temporal_awareness import RelationKind, TemporalContext, relate
from temporal_awareness.relations import describe_duration


class TestSameDay:
    def test_readme_example_later_this_afternoon(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        target = datetime(2026, 10, 3, 17, 0, tzinfo=NY)
        assert ctx.relative(target) == "later today (evening)"

    def test_within_a_minute_is_now(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        target = saturday_afternoon + timedelta(seconds=30)
        assert ctx.relation(target).kind is RelationKind.NOW
        assert ctx.relative(target) == "now"

    def test_earlier_today(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relative(ny(2026, 10, 3, 9, 0)) == "earlier today (morning)"

    def test_later_tonight(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relation(ny(2026, 10, 3, 22, 0)).kind is RelationKind.TONIGHT
        assert ctx.relative(ny(2026, 10, 3, 22, 0)) == "later tonight"

    def test_late_night_now_going_forward_is_not_tonight(self):
        ctx = TemporalContext.from_datetime(ny(2026, 10, 3, 22, 0))
        assert ctx.relation(ny(2026, 10, 3, 23, 30)).kind is RelationKind.LATER_TODAY


class TestDayRelations:
    def test_tomorrow_morning(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relative(ny(2026, 10, 4, 9, 0)) == "tomorrow (morning)"

    def test_yesterday_evening(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relative(ny(2026, 10, 2, 19, 0)) == "yesterday (evening)"

    def test_never_contains_a_raw_timestamp(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        phrase = ctx.relative(ny(2026, 10, 5, 14, 22, 31))
        assert "T" not in phrase
        assert "14:22:31" not in phrase

    def test_far_future_in_days(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relative(ny(2026, 10, 6, 12, 0)) == "in 3 days"

    def test_far_past_ago(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relative(ny(2026, 9, 28, 12, 0)) == "about 5 days"

    def test_is_future_flag(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.relation(ny(2026, 10, 4, 9, 0)).is_future is True
        assert ctx.relation(ny(2026, 10, 2, 9, 0)).is_future is False


class TestStructuredRelation:
    def test_as_dict_fields(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        payload = ctx.relation(ny(2026, 10, 4, 9, 0)).as_dict()
        assert payload["kind"] == "tomorrow"
        assert payload["target_date"] == "2026-10-04"
        assert payload["target_time_of_day"] == "morning"
        assert payload["delta_seconds"] > 0

    def test_kind_values_are_stable_strings(self):
        assert RelationKind.TOMORROW.value == "tomorrow"
        assert RelationKind.EARLIER_TODAY.value == "earlier_today"

    def test_naive_datetimes_rejected(self, saturday_afternoon):
        with pytest.raises(ValueError, match="timezone-aware"):
            relate(saturday_afternoon, datetime(2026, 10, 4, 9, 0))


class TestCrossTimezone:
    def test_tokyo_late_night_is_tomorrow_for_that_local_zone(self):
        tokyo_ctx = TemporalContext.from_datetime(tokyo(2026, 10, 3, 23, 30))
        assert tokyo_ctx.relation(tokyo(2026, 10, 4, 23, 30)).kind is RelationKind.TOMORROW

    def test_day_offset_uses_local_dates_not_utc(self):
        # 22:00 -> 00:30 local is only 2.5 absolute hours, yet the target
        # falls on the *next* calendar day in that zone.
        reference = datetime(2026, 10, 3, 22, 0, tzinfo=NY)
        target = datetime(2026, 10, 4, 0, 30, tzinfo=NY)
        assert (target - reference).total_seconds() == 2.5 * 3600
        assert relate(reference, target).kind is RelationKind.TOMORROW
        assert relate(reference, target).target_date == "2026-10-04"

    def test_same_absolute_pair_reads_differently_per_zone(self):
        # 2026-10-04 03:00 UTC is 2026-10-03 23:00 in New York and
        # 2026-10-04 12:00 in Tokyo. Two hours later the same absolute pair
        # is "tomorrow" in New York but still "today" in Tokyo.
        instant = datetime(2026, 10, 4, 3, 0, tzinfo=timezone.utc)

        ny_ref = instant.astimezone(NY)
        assert ny_ref.date().isoformat() == "2026-10-03"
        assert relate(ny_ref, ny_ref + timedelta(hours=2)).kind is RelationKind.TOMORROW

        tokyo_ref = instant.astimezone(TOKYO)
        assert tokyo_ref.date().isoformat() == "2026-10-04"
        assert relate(tokyo_ref, tokyo_ref + timedelta(hours=2)).kind is RelationKind.LATER_TODAY

    def test_same_instant_agrees_on_delta_seconds(self):
        instant = datetime(2026, 10, 4, 7, 0, tzinfo=__import__("datetime").timezone.utc)
        ny_ctx = TemporalContext.from_datetime(instant.astimezone(NY))
        tokyo_ctx = TemporalContext.from_datetime(instant.astimezone(TOKYO))
        target = instant + timedelta(hours=2)
        assert ny_ctx.relation(target).delta_seconds == tokyo_ctx.relation(target).delta_seconds


class TestDescribeDuration:
    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (30, "moments"),
            (300, "a few minutes"),
            (45 * 60, "about 45 minutes"),
            (2 * 3600, "about 2 hours"),
            (2 * 3600 + 30 * 60, "about 2 hours 30 minutes"),
            (2 * 3600 + 5 * 60, "about 2 hours"),  # sub-10-minute remainder is dropped
            (26 * 3600, "about a day"),
            (5 * 86400, "about 5 days"),
        ],
    )
    def test_phrases(self, seconds, expected):
        assert describe_duration(timedelta(seconds=seconds)) == expected

    def test_symmetric_in_magnitude(self):
        assert describe_duration(timedelta(hours=-3)) == describe_duration(timedelta(hours=3))
