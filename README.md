# Temporal Awareness

**A lightweight, model-agnostic temporal context layer for AI agents.**

Temporal Awareness gives an AI agent access to human-readable temporal
context without making decisions for the agent.

It answers:

> What is the current temporal situation?

It does not answer:

> What should the agent do about it?

---

## Why

Most AI systems expose time as a raw timestamp:

```
2026-10-03T14:22:31-04:00
```

That is useful for software, but it is not necessarily the most useful
representation for an AI agent. A conversational agent may need to
understand:

```
Saturday.
Afternoon, around 2:15 PM.
Half the day has passed.
```

The goal is not to make the model "tell the time." The goal is to make time
available as contextual information that an agent can interpret.

---

## Install

```bash
pip install temporal-awareness
```

Python 3.9+. No third-party runtime dependencies. (`tzdata` is pulled in on
Windows only, because Windows ships no IANA timezone database.)

---

## Quick start

```python
from temporal_awareness import TemporalContext

ctx = TemporalContext.now()
print(ctx.as_prompt_context())
```

```
Temporal context:
Saturday, 2026-10-03.
Afternoon, around 2:15 PM.
Half the day has passed.
```

Inject it into an existing system prompt:

```python
from temporal_awareness import inject

system_prompt = inject("You are a helpful assistant.", ctx)
```

---

## Architecture

```
System Clock
     │
     ▼
Temporal Context
     │   date · weekday · time of day · coarse time · day progress
     ▼
Temporal Relations
     │   today · tomorrow · yesterday · earlier · later · tonight
     ▼
Human Temporal Representation
     │
     ▼
Agent
```

**Temporal Awareness provides context. The agent provides interpretation.**

---

## Core principle

Temporal Awareness is an information layer, not a decision layer.

For example, given: *"Let's eat later."*

Temporal Awareness may provide:

```
Saturday afternoon.
```

It must **not** decide:

- The user means dinner.
- Ask the user what time.
- Accept the invitation.

Those decisions belong to the consuming agent.

---

## API

### `TemporalContext`

| Method | Returns | Purpose |
|---|---|---|
| `TemporalContext.now(clock=None)` | `TemporalContext` | Build from a clock. Defaults to UTC system clock. |
| `TemporalContext.from_datetime(moment)` | `TemporalContext` | Build from any aware `datetime`. |
| `TemporalContext.at(tz=..., year=..., ...)` | `TemporalContext` | Build from wall-clock fields. |
| `ctx.as_prompt_context()` | `str` | The block to inject into a prompt. |
| `ctx.as_dict()` | `dict` | Structured form, exact time included. |
| `ctx.relative(target)` | `str` | Coarse relation to another moment. |
| `ctx.relation(target)` | `TemporalRelation` | Structured relation. |
| `ctx.local_time(hour, minute)` | `datetime` | A time later the same local day. |
| `ctx.exact_timestamp` | `str` | ISO-8601 instant, for grounding. |

Fields: `moment`, `timezone`, `date`, `weekday`, `time_of_day`, `coarse_time`,
`day_progress`, `elapsed_day_fraction`, `granularity`.

### Clocks

```python
from temporal_awareness import FixedClock, SystemClock

SystemClock("Asia/Tokyo")                        # real clock, explicit zone
FixedClock(datetime(2026, 10, 3, 14, 22, tzinfo=ZoneInfo("America/New_York")))
```

Nothing in the library calls `datetime.now()` outside `SystemClock`, so tests
never touch the machine clock. `SystemClock` defaults to **UTC**, not to the
host's local zone — pass `assume_system_local=True` if you genuinely want
host-local time.

### Relations

```python
ctx = TemporalContext.now()

ctx.relative(datetime(2026, 10, 3, 17, 0, tzinfo=ZoneInfo("America/New_York")))
# 'later today (evening)'

ctx.relation(target).kind
# <RelationKind.LATER_TODAY: 'later_today'>
```

Relation kinds: `now`, `earlier_today`, `later_today`, `tonight`,
`yesterday`, `tomorrow`, `in_duration`, `ago`.

### Time-of-day boundaries

Explicit and tested. A moment is classified by the last bound `<=` its local
wall-clock time:

| Period | Range |
|---|---|
| `night` | 00:00 – 04:59, 21:00 – 23:59 |
| `morning` | 05:00 – 11:59 |
| `afternoon` | 12:00 – 16:59 |
| `evening` | 17:00 – 20:59 |

Coarse time rounds to the nearest 15 minutes by default
(`granularity=`, configurable, must divide 60). The small hours degrade to
words — `late at night`, `in the middle of the night`, `early morning
hours` — because `around 12:20 AM` is not how a person describes the middle
of the night. Noon and midnight get their own words for the same reason.

### Exact time and human time coexist

```
Exact timestamp      →  grounding, logging, computation
Coarse time context  →  LLM interpretation
```

Exact time stays available via `ctx.exact_timestamp` and `ctx.as_dict()`. It
is simply never the primary prompt representation. `as_prompt_context()`
never emits seconds, a `T` separator, or a UTC offset.

---

## Design principles

1. **Model agnostic.** No dependency on any LLM. It can be used with OpenAI,
   Anthropic, Gemini, Ollama, MiniMax, local models, or custom agents.
2. **Human-readable.** Temporal information is offered in representations
   that preserve inference space. Exact timestamps remain available for
   grounding; coarse context is for interpretation.
3. **No hidden cognition.** The library does not infer intent, emotion,
   motivation, agency, personality, or memory.
4. **Deterministic infrastructure.** Same timestamp + timezone + configuration
   produces the same output, on every machine.
5. **Small surface area.** It deliberately avoids becoming a general-purpose
   agent framework.

---

## Non-goals

Temporal Awareness is **not**:

- a calendar
- a scheduler
- a reminder system
- a memory system
- a reasoning engine
- an agency system
- an emotion engine
- a conversational framework

Those systems may consume Temporal Awareness, but do not belong inside it.

---

## Relationship to Soul OS

Temporal Awareness can be used by Soul OS, but it is not part of Soul OS
architecture.

```
Temporal Awareness
        │
        │ provides temporal context
        ▼
Soul OS
        │
        │ interprets the context
        ▼
Soul / Agency
```

Temporal Awareness therefore remains independently reusable.

---

## v0.1 scope

- timezone-aware clock access with injectable/fake clocks
- date and weekday
- time-of-day classification
- coarse human-readable time
- day-progress representation
- basic temporal relations
- prompt-context formatting
- deterministic tests, including DST transitions

Future versions may expand temporal representations, but should preserve the
boundary between temporal information and agent cognition.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

The suite includes `tests/test_dst.py` (spring-forward, fall-back, southern
hemisphere, fixed-offset zones) and `tests/test_boundaries.py`, which asserts
on the source tree that no LLM, calendar, scheduler, memory, or
network dependency has crept in.

---

## Philosophy

> Give the agent time.
> Do not tell the agent what time means.

## License

MIT
