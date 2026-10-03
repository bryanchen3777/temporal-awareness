"""Prompt-context formatting and injection."""

from __future__ import annotations

import re

from conftest import ny

from temporal_awareness import FixedClock, TemporalContext, build_context, inject, wrap


class TestPromptContext:
    def test_readme_example(self, saturday_afternoon):
        # 14:22 is 0.5992 of the day, just inside the "half the day" bucket.
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert ctx.as_prompt_context() == (
            "Temporal context:\n"
            "Saturday, 2026-10-03.\n"
            "Afternoon, around 2:15 PM.\n"
            "Half the day has passed."
        )

    def test_later_afternoon_reads_as_large_part_of_day(self):
        ctx = TemporalContext.from_datetime(ny(2026, 10, 3, 18, 0))
        assert ctx.as_prompt_context().endswith("A large part of the day has passed.")

    def test_prompt_context_hides_the_exact_instant(self, saturday_afternoon):
        block = TemporalContext.from_datetime(saturday_afternoon).as_prompt_context()
        assert "14:22:31" not in block
        assert "-04:00" not in block
        assert "2026-10-03T" not in block

    def test_prompt_context_is_short_enough_to_inject(self, saturday_afternoon):
        block = TemporalContext.from_datetime(saturday_afternoon).as_prompt_context()
        assert len(block) < 200
        assert block.count("\n") == 3

    def test_str_matches_prompt_context(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert str(ctx) == ctx.as_prompt_context()

    def test_as_dict_keeps_exact_time_for_grounding(self, saturday_afternoon):
        payload = TemporalContext.from_datetime(saturday_afternoon).as_dict()
        assert payload["exact_timestamp"] == "2026-10-03T14:22:31-04:00"
        assert payload["coarse_time"] == "around 2:15 PM"
        assert payload["weekday"] == "Saturday"
        assert payload["timezone"] == "America/New_York"
        # 14:22:31 is 51751 s into an 86400 s day.
        assert payload["elapsed_day_fraction"] == round(51751 / 86400, 4)

    def test_as_dict_is_json_serialisable(self, saturday_afternoon):
        import json

        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert json.loads(json.dumps(ctx.as_dict()))["date"] == "2026-10-03"

    def test_night_context_reads_naturally(self):
        ctx = TemporalContext.from_datetime(ny(2026, 10, 3, 2, 30))
        assert ctx.as_prompt_context() == (
            "Temporal context:\n"
            "Saturday, 2026-10-03.\n"
            "Night, in the middle of the night.\n"
            "The day is just beginning."
        )


class TestBuildContext:
    def test_uses_injected_clock(self, saturday_afternoon):
        ctx = build_context(FixedClock(saturday_afternoon))
        assert ctx.as_prompt_context() == TemporalContext.from_datetime(
            saturday_afternoon
        ).as_prompt_context()

    def test_custom_granularity(self, saturday_afternoon):
        assert build_context(FixedClock(saturday_afternoon), granularity=30).coarse_time == (
            "around 2:30 PM"
        )


class TestWrap:
    def test_custom_header(self, saturday_afternoon):
        block = wrap(TemporalContext.from_datetime(saturday_afternoon), header="Current time:")
        assert block.splitlines()[0] == "Current time:"

    def test_header_none_drops_header(self, saturday_afternoon):
        block = wrap(TemporalContext.from_datetime(saturday_afternoon), header=None)
        assert not block.startswith("Temporal context:")
        assert "Saturday, 2026-10-03." in block

    def test_footer_states_the_boundary(self, saturday_afternoon):
        block = wrap(TemporalContext.from_datetime(saturday_afternoon))
        assert "does not imply any required action" in block

    def test_footer_can_be_disabled(self, saturday_afternoon):
        block = wrap(TemporalContext.from_datetime(saturday_afternoon), footer=None)
        assert "does not imply" not in block


class TestInject:
    def test_appends_to_system_prompt(self, saturday_afternoon):
        result = inject(
            "You are a helpful assistant.",
            TemporalContext.from_datetime(saturday_afternoon),
        )
        assert result.startswith("You are a helpful assistant.")
        assert "Temporal context:" in result
        assert "Saturday, 2026-10-03." in result

    def test_empty_prompt_returns_block_only(self, saturday_afternoon):
        result = inject("", TemporalContext.from_datetime(saturday_afternoon))
        assert result.startswith("Temporal context:")

    def test_blank_prompt_returns_block_only(self, saturday_afternoon):
        assert inject("   \n", TemporalContext.from_datetime(saturday_afternoon)).startswith(
            "Temporal context:"
        )

    def test_builds_context_from_clock_when_none_given(self, saturday_afternoon):
        result = inject("Base.", FixedClock(saturday_afternoon))
        assert "Saturday, 2026-10-03." in result

    def test_custom_separator(self, saturday_afternoon):
        result = inject(
            "Base.", TemporalContext.from_datetime(saturday_afternoon), separator="\n---\n"
        )
        assert "\n---\nTemporal context:" in result

    def test_is_deterministic(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon)
        assert inject("Base.", ctx) == inject("Base.", ctx)

    def test_does_not_invent_actions(self, saturday_afternoon):
        result = inject("", TemporalContext.from_datetime(saturday_afternoon))
        lowered = result.lower()
        for forbidden in ("you should", "must ask", "accept the invitation", "user means"):
            assert forbidden not in lowered

    def test_no_api_keys_or_endpoints(self, saturday_afternoon):
        result = inject("", TemporalContext.from_datetime(saturday_afternoon))
        assert "sk-" not in result
        assert "api_key" not in result

    def test_iso_timestamp_never_appears_in_prompt(self, saturday_afternoon):
        result = inject("Base.", TemporalContext.from_datetime(saturday_afternoon))
        assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", result)


class TestContextBuilders:
    def test_at_helper_builds_wall_clock_context(self):
        ctx = TemporalContext.at(tz="America/New_York", year=2026, month=10, day=3, hour=14, minute=22)
        assert ctx.date == "2026-10-03"
        assert ctx.coarse_time == "around 2:15 PM"

    def test_at_helper_defaults_to_midnight_utc(self):
        ctx = TemporalContext.at(year=2026, month=10, day=3)
        assert ctx.timezone == "UTC"
        assert ctx.coarse_time == "around midnight"

    def test_local_time_helper_creates_same_day_datetime(self):
        ctx = TemporalContext.at(tz="America/New_York", year=2026, month=10, day=3, hour=14)
        later = ctx.local_time(19, 30)
        assert later.hour == 19
        assert later.date().isoformat() == "2026-10-03"
        assert ctx.relative(later) == "later today (evening)"

    def test_invalid_granularity_rejected(self, saturday_afternoon):
        for bad in (0, 7):
            try:
                TemporalContext.from_datetime(saturday_afternoon, granularity=bad)
            except ValueError:
                continue
            raise AssertionError(f"granularity={bad} should be rejected")

    def test_naive_datetime_rejected(self):
        import datetime as _dt

        try:
            TemporalContext.from_datetime(_dt.datetime(2026, 10, 3, 14, 22))
        except ValueError:
            return
        raise AssertionError("naive datetime should be rejected")

    def test_formatter_round_trip(self, saturday_afternoon):
        ctx = TemporalContext.from_datetime(saturday_afternoon, granularity=30)
        assert ctx.formatter().coarse_time(saturday_afternoon) == "around 2:30 PM"
