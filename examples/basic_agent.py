"""Minimal end-to-end example, also used as a smoke test.

Run it directly:

    python examples/basic_agent.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from zoneinfo import ZoneInfo  # noqa: E402

from temporal_awareness import FixedClock, TemporalContext, inject  # noqa: E402

SYSTEM_PROMPT = (
    "You are a conversational assistant. "
    "Answer the user directly and naturally."
)


def main() -> None:
    # In production you would just call TemporalContext.now(). Here we freeze
    # the clock so the printed output is reproducible.
    clock = FixedClock(datetime(2026, 10, 3, 14, 22, 31, tzinfo=ZoneInfo("America/New_York")))

    context = TemporalContext.now(clock)

    print("--- prompt context ---")
    print(context.as_prompt_context())

    print()
    print("--- structured ---")
    for key, value in context.as_dict().items():
        print(f"{key}: {value}")

    print()
    print("--- relations ---")
    for hour, minute, label in ((17, 0, "later today"), (9, 0, "tomorrow"), (20, 0, "tomorrow")):
        target = context.local_time(hour, minute) + timedelta(days=1 if label == "tomorrow" else 0)
        print(f"{label}: {context.relative(target)}")

    print()
    print("--- injected system prompt ---")
    print(inject(SYSTEM_PROMPT, context))


if __name__ == "__main__":
    main()
