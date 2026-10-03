"""Time-of-day boundaries, coarse time, day progress."""

from __future__ import annotations

from datetime import datetime

import pytest
from conftest import NY, ny

from temporal_awareness import (
    TIME_OF_DAY_BOUNDARIES,
    classify_time_of_day,
    describe_day_progress,
    elapsed_day_fraction,
    format_coarse_time,
    weekday_name,
)

# (hour, minute, expected time-of-day) — every boundary minute is covered.
BOUNDARY_CASES = [
    (0, 0, "night"),
    (4, 59, "night"),
    (5, 0, "morning"),
    (11, 59, "morning"),
    (12, 0, "afternoon"),
    (16, 59, "afternoon"),
    (17, 0, "evening"),
    (20, 59, "evening"),
    (21, 0, "night"),
    (23, 59, "night"),
]


class TestTimeOfDay:
    @pytest.mark.parametrize("hour,minute,expected", BOUNDARY_CASES)
    def test_boundaries(self, hour, minute, expected):
        assert classify_time_of_day(ny(2026, 10, 3, hour, minute)) == expected

    def test_boundaries_are_contiguous_and_cover_24h(self):
        labels = [label for _, label in TIME_OF_DAY_BOUNDARIES]
        assert labels == ["night", "morning", "afternoon", "evening", "night"]

    def test_canonical_label_set(self):
        observed = {classify_time_of_day(ny(2026, 10, 3, h)) for h in range(24)}
        assert observed == {"morning", "afternoon", "evening", "night"}

    def test_boundary_value_is_inclusive_lower_bound(self):
        for bound, _label in TIME_OF_DAY_BOUNDARIES:
            moment = datetime(2026, 10, 3, bound.hour, bound.minute, tzinfo=NY)
            assert classify_time_of_day(moment) == classify_time_of_day(moment)


class TestCoarseTime:
    @pytest.mark.parametrize(
        "hour,minute,expected",
        [
            (9, 0, "around 9 AM"),
            (9, 3, "around 9 AM"),
            (14, 22, "around 2:15 PM"),
            (14, 30, "around 2:30 PM"),
            (17, 59, "around 6 PM"),
            (11, 30, "around 11:30 AM"),
            (8, 0, "around 8 AM"),
            (23, 59, "around midnight"),  # 23:59 rounds up past the day end
        ],
    )
    def test_rounding_to_quarter_hour(self, hour, minute, expected):
        assert format_coarse_time(ny(2026, 10, 3, hour, minute)) == expected

    @pytest.mark.parametrize(
        "hour,minute,expected",
        [
            (0, 0, "around midnight"),
            (0, 4, "around midnight"),  # 00:04 rounds back to 00:00
            (12, 0, "around noon"),
            (12, 3, "around noon"),  # 12:03 rounds back to 12:00
        ],
    )
    def test_special_labels(self, hour, minute, expected):
        assert format_coarse_time(ny(2026, 10, 3, hour, minute)) == expected

    @pytest.mark.parametrize(
        "hour,minute,expected",
        [
            (0, 30, "late at night"),
            (1, 30, "in the middle of the night"),
            (2, 30, "in the middle of the night"),
            (3, 30, "early morning hours"),
            (4, 45, "early morning hours"),
        ],
    )
    def test_small_hours_degrade_to_phrases(self, hour, minute, expected):
        assert format_coarse_time(ny(2026, 10, 3, hour, minute)) == expected

    def test_noon_does_not_emit_12_00_pm(self):
        assert "12:00 PM" not in format_coarse_time(ny(2026, 10, 3, 12, 0))

    def test_midnight_does_not_emit_12_00_am(self):
        assert "12:00 AM" not in format_coarse_time(ny(2026, 10, 3, 0, 0))

    def test_rounding_up_past_midnight_wraps(self):
        assert format_coarse_time(ny(2026, 10, 3, 23, 59)) == "around midnight"
        assert format_coarse_time(ny(2026, 10, 3, 23, 50)) == "around 11:45 PM"

    @pytest.mark.parametrize("granularity", [1, 5, 15, 20, 30, 60])
    def test_supported_granularities(self, granularity):
        assert format_coarse_time(ny(2026, 10, 3, 14, 22), granularity=granularity)

    @pytest.mark.parametrize("granularity", [0, -15, 7, 90])
    def test_invalid_granularity_rejected(self, granularity):
        with pytest.raises(ValueError):
            format_coarse_time(ny(2026, 10, 3, 14, 22), granularity=granularity)

    def test_is_never_a_raw_timestamp(self, saturday_afternoon):
        coarse = format_coarse_time(saturday_afternoon)
        assert "T" not in coarse
        assert ":31" not in coarse  # seconds are never surfaced

    def test_does_not_leak_timezone_offset(self, saturday_afternoon):
        assert "-04:00" not in format_coarse_time(saturday_afternoon)


class TestDayProgress:
    @pytest.mark.parametrize(
        "hour,minute,expected",
        [
            (0, 0, "the day is just beginning"),
            (5, 59, "the day is just beginning"),
            (6, 0, "the morning is underway"),
            (11, 59, "the morning is underway"),
            (12, 0, "half the day has passed"),
            (14, 23, "half the day has passed"),
            (14, 24, "a large part of the day has passed"),
            (18, 0, "a large part of the day has passed"),
            (21, 35, "a large part of the day has passed"),
            (22, 0, "the day is nearly over"),
            (23, 59, "the day is nearly over"),
        ],
    )
    def test_buckets(self, hour, minute, expected):
        assert describe_day_progress(ny(2026, 10, 3, hour, minute)) == expected

    def test_fraction_is_monotonic_within_a_day(self):
        fractions = [
            elapsed_day_fraction(ny(2026, 10, 3, h, m)) for h, m in [(0, 0), (6, 0), (12, 0), (18, 0), (23, 59)]
        ]
        assert fractions == sorted(fractions)
        assert fractions[0] == 0.0
        assert 0.0 <= fractions[-1] < 1.0

    def test_fraction_at_readme_example(self):
        fraction = elapsed_day_fraction(ny(2026, 10, 3, 14, 22, 31))
        assert 0.59 < fraction < 0.61


class TestWeekday:
    def test_readme_date_is_saturday(self):
        assert weekday_name(ny(2026, 10, 3)) == "Saturday"

    def test_monday(self):
        assert weekday_name(ny(2026, 10, 5)) == "Monday"

    def test_sunday(self):
        assert weekday_name(ny(2026, 10, 4)) == "Sunday"
