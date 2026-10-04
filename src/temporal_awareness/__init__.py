"""Temporal Awareness — a temporal context layer for AI agents.

This package provides human-readable temporal context. It is a context
layer, not a reasoning or decision layer.

The layer answers one question:

    What is the current temporal situation?

It does not answer:

    What should the agent do about it?

Whether a consuming agent interprets that context, ignores it, or is
measurably affected by it is a property of the agent, not of this
package. Supplying context is not evidence of temporal cognition.

Give the agent time. Do not tell the agent what time means.
"""

from __future__ import annotations

from .clock import Clock, FixedClock, SystemClock, resolve_tz
from .context import TemporalContext
from .formatter import (
    TIME_OF_DAY_BOUNDARIES,
    Formatter,
    classify_time_of_day,
    describe_day_progress,
    elapsed_day_fraction,
    format_coarse_time,
    weekday_name,
)
from .injection import build_context, inject, wrap
from .relations import RelationKind, TemporalRelation, relate

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # clock
    "Clock",
    "SystemClock",
    "FixedClock",
    "resolve_tz",
    # context
    "TemporalContext",
    "build_context",
    # formatting
    "Formatter",
    "TIME_OF_DAY_BOUNDARIES",
    "classify_time_of_day",
    "format_coarse_time",
    "describe_day_progress",
    "elapsed_day_fraction",
    "weekday_name",
    # relations
    "TemporalRelation",
    "RelationKind",
    "relate",
    # injection
    "inject",
    "wrap",
]
