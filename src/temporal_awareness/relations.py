"""Temporal relations between a reference moment and a target moment.

This module answers "how is this target positioned relative to now?" in words
and in structured form. It never answers "what should the agent do about it".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict

from .formatter import classify_time_of_day

__all__ = [
    "RelationKind",
    "TemporalRelation",
    "relate",
    "describe_duration",
    "DAY_NAMES",
]

#: Human-readable day names keyed by the calendar-day offset.
DAY_NAMES: Dict[int, str] = {
    -1: "yesterday",
    0: "today",
    1: "tomorrow",
}


class RelationKind(str, Enum):
    NOW = "now"
    EARLIER_TODAY = "earlier_today"
    LATER_TODAY = "later_today"
    TONIGHT = "tonight"
    YESTERDAY = "yesterday"
    TOMORROW = "tomorrow"
    IN_DURATION = "in_duration"
    AGO = "ago"


def describe_duration(delta: timedelta) -> str:
    """Coarse English duration, e.g. ``about 2 hours`` / ``a few minutes``."""

    seconds = int(abs(delta.total_seconds()))
    if seconds < 60:
        return "moments"
    minutes = seconds // 60
    if minutes < 60:
        if minutes < 10:
            return "a few minutes"
        return f"about {minutes} minutes"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    if hours < 24:
        if remaining_minutes < 10:
            return f"about {hours} hours"
        return f"about {hours} hours {remaining_minutes} minutes"
    days = hours // 24
    if days == 1:
        return "about a day"
    return f"about {days} days"


@dataclass(frozen=True)
class TemporalRelation:
    """Structured answer to "where does the target sit relative to now?"."""

    kind: RelationKind
    phrase: str
    delta_seconds: float
    target_date: str
    target_time_of_day: str

    @property
    def is_future(self) -> bool:
        return self.delta_seconds > 0

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "phrase": self.phrase,
            "delta_seconds": self.delta_seconds,
            "target_date": self.target_date,
            "target_time_of_day": self.target_time_of_day,
        }


def relate(reference: datetime, target: datetime) -> TemporalRelation:
    """Compute the relation of ``target`` to ``reference``.

    Both must be timezone-aware. The delta is an absolute instant difference,
    but the day offset comes from each moment's own local date, so
    ``2026-10-03 23:30 +09:00`` is "today" for a Tokyo agent even while it is
    still ``2026-10-03 10:30`` in New York.
    """

    if reference.tzinfo is None or target.tzinfo is None:
        raise ValueError("both reference and target must be timezone-aware")

    delta = target - reference
    delta_seconds = delta.total_seconds()
    offset = (target.date() - reference.date()).days
    target_tod = classify_time_of_day(target)
    target_date = target.date().isoformat()

    def build(kind: RelationKind, phrase: str) -> TemporalRelation:
        return TemporalRelation(
            kind=kind,
            phrase=phrase,
            delta_seconds=delta_seconds,
            target_date=target_date,
            target_time_of_day=target_tod,
        )

    if abs(delta_seconds) < 60:
        return build(RelationKind.NOW, "now")

    if offset == 0:
        if delta_seconds > 0:
            # Only call it "tonight" when the target actually lands in the
            # evening/night stretch ahead of the reference.
            if target_tod == "night" and reference.hour < 21:
                return build(RelationKind.TONIGHT, "later tonight")
            return build(RelationKind.LATER_TODAY, f"later today ({target_tod})")
        return build(RelationKind.EARLIER_TODAY, f"earlier today ({target_tod})")

    if offset == 1:
        return build(RelationKind.TOMORROW, f"tomorrow ({target_tod})")
    if offset == -1:
        return build(RelationKind.YESTERDAY, f"yesterday ({target_tod})")

    if offset > 1:
        if offset <= 7:
            return build(RelationKind.IN_DURATION, f"in {offset} days")
        return build(RelationKind.IN_DURATION, describe_duration(delta))
    return build(RelationKind.AGO, describe_duration(delta))
