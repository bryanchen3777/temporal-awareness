"""``TemporalContext`` — the object a consuming agent receives.

It carries the exact timestamp (for grounding, logging, computation) *and*
the coarse human-readable representation (for LLM interpretation), and keeps
the two clearly separate so neither is confused for the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .clock import Clock, SystemClock, resolve_tz
from .formatter import (
    Formatter,
    classify_time_of_day,
    describe_day_progress,
    elapsed_day_fraction,
    format_coarse_time,
    weekday_name,
)
from .relations import TemporalRelation, relate

if TYPE_CHECKING:  # pragma: no cover
    from .clock import TzLike

__all__ = ["TemporalContext"]


@dataclass(frozen=True)
class TemporalContext:
    """An immutable snapshot of "the temporal situation right now"."""

    moment: datetime
    timezone: str
    date: str
    weekday: str
    time_of_day: str
    coarse_time: str
    day_progress: str
    elapsed_day_fraction: float
    granularity: int = 15

    # ---------------------------------------------------------------- build

    @classmethod
    def now(
        cls,
        clock: Optional[Clock] = None,
        *,
        granularity: int = 15,
    ) -> "TemporalContext":
        """Build a context from a clock. Defaults to the real UTC clock."""

        active = clock if clock is not None else SystemClock()
        return cls.from_datetime(active.now(), granularity=granularity)

    @classmethod
    def from_datetime(
        cls,
        moment: datetime,
        *,
        granularity: int = 15,
    ) -> "TemporalContext":
        if moment.tzinfo is None:
            raise ValueError("TemporalContext requires a timezone-aware datetime")
        if granularity <= 0 or 60 % granularity != 0:
            raise ValueError("granularity must be a positive divisor of 60")

        tzinfo = moment.tzinfo
        name = getattr(tzinfo, "key", None) or str(tzinfo)

        return cls(
            moment=moment,
            timezone=name,
            date=moment.date().isoformat(),
            weekday=weekday_name(moment),
            time_of_day=classify_time_of_day(moment),
            coarse_time=format_coarse_time(moment, granularity=granularity),
            day_progress=describe_day_progress(moment),
            elapsed_day_fraction=elapsed_day_fraction(moment),
            granularity=granularity,
        )

    @classmethod
    def at(
        cls,
        *,
        tz: "TzLike" = None,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        granularity: int = 15,
        assume_system_local: bool = False,
    ) -> "TemporalContext":
        """Build a context from wall-clock fields in a given timezone.

        Useful in tests, notebooks and examples.
        """

        zone = resolve_tz(tz, assume_system_local=assume_system_local)
        moment = datetime(year, month, day, hour, minute, second, tzinfo=zone)
        return cls.from_datetime(moment, granularity=granularity)

    # ------------------------------------------------------------- accessors

    @property
    def exact_timestamp(self) -> str:
        """ISO-8601 instant. For grounding/logging, not for LLM prompts."""

        return self.moment.isoformat()

    def formatter(self) -> Formatter:
        return Formatter(granularity=self.granularity)

    def relative(self, target: datetime) -> str:
        """Human-readable relation of ``target`` to this moment."""

        return self.relation(target).phrase

    def relation(self, target: datetime) -> TemporalRelation:
        return relate(self.moment, target)

    def local_time(self, hour: int, minute: int = 0, second: int = 0) -> datetime:
        """A datetime on this context's date in its own timezone.

        A wall time inside a DST gap is normalized forward by ``zoneinfo``
        rather than raising, and an ambiguous wall time resolves to the
        earlier (daylight) offset — the standard "first occurrence" rule.
        """

        tzinfo = self.moment.tzinfo
        assert tzinfo is not None
        return datetime(
            self.moment.year, self.moment.month, self.moment.day, hour, minute, second, tzinfo=tzinfo
        )

    # ------------------------------------------------------------ rendering

    def as_prompt_context(self) -> str:
        """The concise block intended for direct injection into an LLM.

        Three lines, no exact timestamp, no timezone offset. Deterministic for
        a given moment and granularity.
        """

        return "\n".join(
            (
                "Temporal context:",
                f"{self.weekday}, {self.date}.",
                f"{self.time_of_day.capitalize()}, {self.coarse_time}.",
                f"{self.day_progress.capitalize()}.",
            )
        )

    def as_dict(self) -> dict:
        """Structured form for tools, structured output, or logging."""

        return {
            "exact_timestamp": self.exact_timestamp,
            "timezone": self.timezone,
            "date": self.date,
            "weekday": self.weekday,
            "time_of_day": self.time_of_day,
            "coarse_time": self.coarse_time,
            "day_progress": self.day_progress,
            "elapsed_day_fraction": round(self.elapsed_day_fraction, 4),
        }

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.as_prompt_context()
