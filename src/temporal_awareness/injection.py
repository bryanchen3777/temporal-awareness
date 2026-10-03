"""Prompt injection helpers.

The only thing this module does is put a context block into a string. It does
not call any model, does not format provider-specific payloads, and does not
decide anything on the agent's behalf.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union

from .clock import Clock
from .context import TemporalContext

__all__ = [
    "build_context",
    "inject",
    "inject_relations",
    "wrap",
    "DEFAULT_HEADER",
    "DEFAULT_FOOTER",
]

DEFAULT_HEADER = "Temporal context:"
DEFAULT_FOOTER = (
    "This context is informational. Interpret it as you see fit; "
    "the timing information does not imply any required action."
)


def build_context(clock: Optional[Clock] = None, *, granularity: int = 15) -> TemporalContext:
    """Convenience: build a :class:`TemporalContext` from a clock."""

    return TemporalContext.now(clock, granularity=granularity)


def wrap(
    context: TemporalContext,
    *,
    header: Optional[str] = DEFAULT_HEADER,
    footer: Optional[str] = DEFAULT_FOOTER,
) -> str:
    """Render the context block, optionally with a boundary reminder."""

    lines = []
    if header is not None:
        lines.append(header)
    lines.append(f"{context.weekday}, {context.date}.")
    lines.append(f"{context.time_of_day.capitalize()}, {context.coarse_time}.")
    lines.append(f"{context.day_progress.capitalize()}.")
    body = "\n".join(lines)
    if footer:
        body = f"{body}\n{footer}"
    return body


def inject(
    system_prompt: str,
    context: Union[TemporalContext, Clock, None] = None,
    *,
    granularity: int = 15,
    header: Optional[str] = DEFAULT_HEADER,
    footer: Optional[str] = DEFAULT_FOOTER,
    separator: str = "\n\n",
) -> str:
    """Append a temporal context block to an existing system prompt.

    ``context`` may be a ready :class:`TemporalContext` or a
    :class:`~temporal_awareness.clock.Clock` to sample.

    Purely string concatenation — no model calls, no tokenization, no
    provider-specific behaviour. Works with any LLM because it produces text.
    """

    if isinstance(context, TemporalContext):
        active = context
    else:
        active = build_context(context, granularity=granularity)

    block = wrap(active, header=header, footer=footer)
    if not system_prompt or not system_prompt.strip():
        return block
    return f"{system_prompt.rstrip()}{separator}{block}"


def inject_relations(
    system_prompt: str,
    context: TemporalContext,
    targets: List[datetime],
    *,
    separator: str = "\n",
) -> str:
    """Append relation lines for a set of concrete timestamps.

    Still only information: each target becomes a coarse phrase such as
    ``later today (evening)``.
    """

    if not targets:
        return system_prompt
    lines = [context.relative(t) for t in targets]
    return f"{system_prompt.rstrip()}{separator}{separator.join(lines)}"
