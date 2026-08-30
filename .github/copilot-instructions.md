# Copilot instructions for Sainsburys API

This is an async Python integration library (`pysainsburys`) using the
**http** protocol.

## Before editing

1. Read `AGENTS.md` for commands and architecture.
2. For specialized workflows, check `.agents/skills/` (AG Kit + project skill
   `pysainsburys`).

## Commands

```bash
uv sync
uv run pytest
prek run -a
```

## Code layout

- `pysainsburys/client.py` — public async API
- `pysainsburys/adapter.py` — protocol adapter
- `pysainsburys/config.py` — configuration
- `tests/` — pytest tests

Keep I/O async, adapter logic in `adapter.py`, and follow conventional commits.
