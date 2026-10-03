# temporal-awareness — Agent Notes

Project-local working notes. The user-facing contract lives in `README.md`;
this file records decisions and constraints that are **not** derivable from
the code.

## Status

| Ticket | State | Commit |
|---|---|---|
| TAW-0.1 Foundation | **CLOSED** | `465a3dd` |
| TAW-0.1.1 CI / Release Integrity | **CLOSED** | `5e89606` |
| TAW-0.2 Adapter Layer | **DEFERRED** (architecture decision) | — |

CI is green on Python 3.9, 3.10, 3.11, 3.12, 3.13 (ubuntu-latest) and
Python 3.12 (windows-latest). 165 tests per job.

## Repo location

`C:\Users\bbfcc\.local\bin\temporal-awareness`

Local Python (not on PATH):
`C:\Users\bbfcc\AppData\Local\Programs\Python\Python312\python.exe`

## Architecture decisions

### TAW-0.2 Adapter Layer — DEFERRED, not backlog

This is an **architecture decision**, not a scheduling choice. It is not
permanently rejected; it is consumer-driven.

`inject(prompt, ctx)` is already a clean model-agnostic boundary. Adding
provider adapters immediately pushes this library toward understanding
messages arrays, system prompts, tool schemas, token budgets and
provider-specific request formats — i.e. from

```
Temporal Awareness -> Agent
```

toward

```
Temporal Awareness -> LLM Provider Integration
```

which inverts the project's core positioning.

**Do not add provider adapters until a real consumer exists.** The first
consumer is what will reveal the actual integration boundary (system prompt?
per-turn tool result? metadata at memory-write time?). Any adapter designed
before that is a product of imagination.

**Banned in this repo until that decision is revisited:** OpenAI adapters,
Anthropic adapters, Ollama adapters, MiniMax adapters, any LLM dependency,
any plugin framework.

### CI runner policy

Keep `ubuntu-latest` unpinned. Do not add macOS until a consumer requires it.

Rationale: 3.9–3.13 plus Windows already give real coverage. The
`ubuntu-latest` -> Ubuntu 26 migration (dated 2026-10-19) is not a current
correctness finding. Pinning or adding platforms now would add maintenance
surface for a problem that has not occurred. If CI genuinely regresses after
the migration, fix the actual failure then.

This follows the project principle: *minimal, verifiable, no hypothetical
infrastructure.*

## Standing constraints

- **No Soul OS coupling.** This repo must never import from, reference, or
  read Soul OS runtime or production data. Enforced by `tests/test_boundaries.py`.
- **Boundary tests must be adversarially validated.** A green boundary suite
  proves nothing on its own. When changing `tests/test_boundaries.py`, verify
  by injecting violations and confirming they are actually rejected.
  The `ast.ImportFrom`-only gap in the original version was found this way.
- **No unrelated refactoring.** Each ticket stays inside its scope.
- **No new runtime dependencies** without an explicit ticket. The only one is
  `tzdata` on Windows, which is the IANA timezone database, not a calendar
  library.

## Local verification

```powershell
cd C:\Users\bbfcc\.local\bin\temporal-awareness
.\.venv\Scripts\python.exe -m pytest
```

Multi-line commit messages must go through a file:

```powershell
git commit -F .git\COMMIT_EDITMSG.txt
```

(`git commit -m $msg` with a here-string gets word-split by PowerShell and
produces bogus `pathspec` errors.)
