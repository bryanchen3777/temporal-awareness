"""Clock abstraction.

The whole library depends on a ``Clock`` that returns a timezone-aware
``datetime``. Nothing in this package calls ``datetime.now()`` directly
outside of :class:`SystemClock`, so tests can freeze time without touching
the machine clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional, Union
from zoneinfo import ZoneInfo

__all__ = [
    "Clock",
    "SystemClock",
    "FixedClock",
    "resolve_tz",
    "UTC",
]

UTC = timezone.utc

TzLike = Union[str, tzinfo, None]


class Clock:
    """Interface for a source of timezone-aware time."""

    def now(self) -> datetime:  # pragma: no cover - interface
        raise NotImplementedError

    def __call__(self) -> datetime:
        return self.now()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"{type(self).__name__}()"


def resolve_tz(tz: TzLike = None, *, assume_system_local: bool = False) -> tzinfo:
    """Normalize a timezone input into a concrete ``tzinfo``.

    Default is UTC. The library never silently assumes the host's local
    timezone, because that would make output machine-dependent. Callers who
    genuinely want host-local time must opt in explicitly with
    ``assume_system_local=True``.
    """

    if isinstance(tz, tzinfo):
        return tz
    if isinstance(tz, str):
        try:
            return ZoneInfo(tz)
        except Exception as exc:  # noqa: BLE001 - surfaced as a clear error
            raise ValueError(f"unknown timezone: {tz!r}") from exc
    if tz is None:
        if assume_system_local:
            return datetime.now().astimezone().tzinfo or UTC
        return UTC
    raise TypeError(f"cannot interpret {tz!r} as a timezone")


class SystemClock(Clock):
    """Reads the real wall clock, always in an explicit timezone."""

    def __init__(self, tz: TzLike = None, *, assume_system_local: bool = False):
        self._tz = resolve_tz(tz, assume_system_local=assume_system_local)

    @property
    def tz(self) -> tzinfo:
        return self._tz

    def now(self) -> datetime:
        return datetime.now(tz=self._tz)

    def __repr__(self) -> str:
        name = getattr(self._tz, "key", None) or str(self._tz)
        return f"SystemClock(tz={name!r})"


class FixedClock(Clock):
    """A frozen clock. Optionally advances by a fixed step on every read."""

    def __init__(self, moment: datetime, *, step: Optional[timedelta] = None):
        if moment.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._moment = moment
        self._step = step

    @property
    def tz(self) -> tzinfo:
        assert self._moment.tzinfo is not None
        return self._moment.tzinfo

    def now(self) -> datetime:
        current = self._moment
        if self._step is not None:
            self._moment = self._moment + self._step
        return current

    def set(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FixedClock requires a timezone-aware datetime")
        self._moment = moment

    def __repr__(self) -> str:
        return f"FixedClock({self._moment.isoformat()!r})"
