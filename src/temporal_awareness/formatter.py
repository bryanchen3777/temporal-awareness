"""Deterministic, human-readable temporal formatting.

Everything here is a pure function of a timezone-aware ``datetime``. Same
input, same output, on every machine.

Two representations coexist on purpose:

* **Exact time** (the ``datetime`` itself) stays available for grounding,
  logging and computation.
* **Coarse time** (the strings produced here) is what an LLM should read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Tuple

__all__ = [
    "TimeOfDay",
    "TIME_OF_DAY_ORDER",
    "TIME_OF_DAY_BOUNDARIES",
    "classify_time_of_day",
    "format_coarse_time",
    "describe_day_progress",
    "elapsed_day_fraction",
    "WEEKDAY_NAMES",
    "weekday_name",
    "Formatter",
]

WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

#: The canonical time-of-day labels exposed by the public API.
TimeOfDay = str

#: Fixed presentation order, for callers that want to render every period.
TIME_OF_DAY_ORDER: Tuple[TimeOfDay, ...] = ("morning", "afternoon", "evening", "night")

#: Explicit, inclusive lower bounds for each period. A moment is classified by
#: the last bound that is <= its local wall-clock time.
#:
#:   night      00:00 - 04:59
#:   morning    05:00 - 11:59
#:   afternoon  12:00 - 16:59
#:   evening    17:00 - 20:59
#:   night      21:00 - 23:59
TIME_OF_DAY_BOUNDARIES: Tuple[Tuple[time, TimeOfDay], ...] = (
    (time(0, 0), "night"),
    (time(5, 0), "morning"),
    (time(12, 0), "afternoon"),
    (time(17, 0), "evening"),
    (time(21, 0), "night"),
)

#: Ordered ceilings for :func:`describe_day_progress`.
#: The 0.60 ceiling is deliberate: from roughly 14:24 onward the day is
#: mostly behind you, which is where "a large part of the day has passed"
#: starts to be the honest description.
_DAY_PROGRESS_STEPS: Tuple[Tuple[float, str], ...] = (
    (0.25, "the day is just beginning"),
    (0.50, "the morning is underway"),
    (0.60, "half the day has passed"),
    (0.90, "a large part of the day has passed"),
    (1.01, "the day is nearly over"),
)

#: Rounded hour-of-day -> phrase, for the hours where a clock reading like
#: "12:20 AM" stops being how a person describes the moment. Keyed on the
#: rounded hour so the phrase is stable against minute noise.
_SMALL_HOUR_PHRASES = {
    0: "late at night",
    1: "in the middle of the night",
    2: "in the middle of the night",
    3: "early morning hours",
    4: "early morning hours",
}


def weekday_name(moment: datetime) -> str:
    return WEEKDAY_NAMES[moment.weekday()]


def classify_time_of_day(moment: datetime) -> TimeOfDay:
    """Return ``morning`` / ``afternoon`` / ``evening`` / ``night``."""

    current = time(moment.hour, moment.minute)
    result = TIME_OF_DAY_BOUNDARIES[0][1]
    for bound, label in TIME_OF_DAY_BOUNDARIES:
        if current < bound:
            break
        result = label
    return result


def elapsed_day_fraction(moment: datetime) -> float:
    """Fraction of the local day already elapsed, in ``[0.0, 1.0)``.

    Computed from local wall-clock fields rather than by subtracting
    ``datetime.combine(date, time.min)``, so a DST transition inside the day
    can never produce a negative or greater-than-one value.
    """

    seconds = moment.hour * 3600 + moment.minute * 60 + moment.second
    return seconds / 86400.0


def describe_day_progress(moment: datetime) -> str:
    fraction = elapsed_day_fraction(moment)
    for ceiling, phrase in _DAY_PROGRESS_STEPS:
        if fraction < ceiling:
            return phrase
    return _DAY_PROGRESS_STEPS[-1][1]


def _clock_label(hour24: int, minute: int) -> str:
    """``(9, 0) -> "9 AM"``, ``(14, 30) -> "2:30 PM"``."""

    suffix = "AM" if hour24 < 12 else "PM"
    hour12 = hour24 % 12 or 12
    if minute == 0:
        return f"{hour12} {suffix}"
    return f"{hour12}:{minute:02d} {suffix}"


def format_coarse_time(moment: datetime, *, granularity: int = 15) -> str:
    """Human-readable coarse local time, e.g. ``around 2:30 PM``.

    The exact minute is rounded to the nearest ``granularity`` so the value is
    stable under noise and does not imply false precision.

    The small hours (00:00-04:59) degrade to a period phrase instead of
    ``around 12:20 AM``, because that string is not how a person describes
    the middle of the night. Noon and midnight get their own words for the
    same reason.
    """

    if granularity <= 0:
        raise ValueError("granularity must be positive")
    if granularity > 60 or 60 % granularity != 0:
        raise ValueError("granularity must divide 60 evenly")

    total_minutes = moment.hour * 60 + moment.minute
    half = granularity // 2
    rounded = ((total_minutes + half) // granularity) * granularity

    # Rounding up past the end of the day wraps into the next day's start.
    if rounded >= 1440:
        rounded -= 1440

    hour24, minute = divmod(rounded, 60)

    if hour24 == 12 and minute == 0:
        return "around noon"
    if hour24 == 0 and minute == 0:
        return "around midnight"
    if hour24 < 5:
        return _SMALL_HOUR_PHRASES[hour24]
    return f"around {_clock_label(hour24, minute)}"


@dataclass(frozen=True)
class Formatter:
    """Bundles formatting choices so a caller can pin them once."""

    granularity: int = 15

    def time_of_day(self, moment: datetime) -> TimeOfDay:
        return classify_time_of_day(moment)

    def coarse_time(self, moment: datetime) -> str:
        return format_coarse_time(moment, granularity=self.granularity)

    def day_progress(self, moment: datetime) -> str:
        return describe_day_progress(moment)

    def weekday(self, moment: datetime) -> str:
        return weekday_name(moment)
