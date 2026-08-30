# AGENTS.md

This file provides guidance to AI coding agents when working with code in this
repository.

## Agent skills

Skills for specialized workflows live in `.agents/skills/` (from
[AG Kit](https://github.com/vudovn/ag-kit)) plus a project-specific skill at
`.agents/skills/pysainsburys/`.

| Tool | How skills are loaded |
| --- | --- |
| Cursor | `.cursor/skills/` (bridged from `.agents/skills/`) |
| Claude Code | `CLAUDE.md` and `.agents/skills/*/SKILL.md` |
| VS Code / Copilot | `.github/copilot-instructions.md` |
| Codex / Grok / others | This file and `.agents/skills/*/SKILL.md` |

After updating AG Kit, re-run `python3 scripts/install_agent_skills.py` to
refresh Cursor skill links.

## Project overview

**Sainsburys API** — A async integration API for Sainsburys

Async Python integration library using the **http** protocol.
Package name: `pysainsburys`.

## Development commands

```bash
uv sync
uv run pytest
uv run pytest tests/test_client.py::test_name
prek run -a
ruff check --fix .
ruff format .
```

```bash
uv sync --group docs
uv run mkdocs serve
uv run mkdocs build --strict
```

## Architecture

- `pysainsburys/client.py` — high-level async `Client`
- `pysainsburys/adapter.py` — `http` adapter implementation
- `pysainsburys/config.py` — `Config` and `COMM_PROTOCOL`
- `tests/` — pytest suite (Sybil doctests via `conftest.py`)

## Conventions

- Follow [conventional commits](https://www.conventionalcommits.org)
- Ruff for lint/format; mypy configured in `pyproject.toml`
- pytest-asyncio for async tests
- Keep transport logic in `adapter.py`; expose behavior through `Client`

## Useful AG Kit skills

Browse `.agents/skills/` or invoke by name, for example:

- `python-patterns` — Python and async conventions
- `testing-patterns` — pytest strategies
- `clean-code` — readability and maintainability
- `systematic-debugging` — root-cause analysis
- `verify-changes` — prove changes by running checks
- `pysainsburys` — this project's layout and commands

Install or update AG Kit skills:

```bash
npx @vudovn/ag-kit init    # first install
npx @vudovn/ag-kit update    # safe merge update
python3 scripts/install_agent_skills.py
```
