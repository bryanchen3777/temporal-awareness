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

That is useful for software, but it is a poor fit for language: it carries
maximum precision and almost no usable context. Any consumer that wants to
reason over *when* something happens has to reconstruct that coarse
structure itself, on every call.

This layer provides the reconstruction directly:

```
Saturday.
Afternoon, around 2:15 PM.
Half the day has passed.
```

The goal is not to make a model "tell the time." The goal is to make
temporal structure available as readable context — and to leave every
question about what a consuming agent does with it entirely outside this
library.

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

Whether the consuming agent uses that context, ignores it, or is
measurably affected by it is a question about the agent — not about this
library. See [What this layer is not](#what-this-layer-is-not).

---

## What this layer is not

Providing temporal context is an engineering capability. It is not, by
itself, evidence that a consuming agent has temporal cognition.

None of the following is evidence of temporal cognition:

- Injecting this context into a prompt.
- The context changing the agent's output.
- The agent calling a clock or a temporal tool.
- Tool-call frequency, or any ON/OFF behavioural delta.

Those are **observable implementation behaviours**. They show that time
information reached the model. They do not show that the model understood
it, weighted it, or reasoned over it.

Establishing temporal cognition requires a construct, an operational
definition for it, and controls able to separate *"the agent used the
time"* from *"the agent reacted to more text"*. This repository does not
define those controls, does not define a threshold, and does not claim to.

---

## Scope of the change log

This library's own behaviour is unchanged by this document. It describes
what the library has always done: derive temporal structure and hand it
over as context.

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

This repository is an independent engineering and research sandbox. It is
not part of Soul OS architecture, and it does not modify Soul OS runtime.

```
Temporal context layer
        │
        │ provides temporal context
        ▼
Consuming agent or system
        │
        │ interprets, ignores, or is unaffected
        ▼
Agent behaviour
```

**Results obtained in this repository do not automatically constitute
acceptance of any capability in another project.** Acceptance is governed
by that project's own canonical construct, operationalization, controls,
and gate. This library supplies a reusable capability; it supplies no
evidence about any agent's cognition.

Any experiment run against a consuming system — including a real
counterfactual comparison — remains that project's work, with its own
controls and its own decision criteria. Providing a context layer makes
such an experiment *possible*. It does not make its result *true*.

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
