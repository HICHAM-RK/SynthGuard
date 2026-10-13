# Contributing to SynthGuard

SynthGuard is local-first and evidence-first. Contributions must preserve those boundaries.

## Set up

Install Python 3.12 and `uv`, then run:

```bash
uv sync --locked --all-extras
```

## Make a change

1. Read `AGENTS.md`, `CAPABILITY_MAP.md`, and the relevant `SPEC-*.md`.
2. Add or update a failing test before changing behavior.
3. Keep domain logic independent from Streamlit and MCP adapters.
4. Use only fictional, non-sensitive fixtures.
5. Update the active specification before changing a public contract.

## Verify

```bash
uv run pytest --cov=synthguard --cov-report=term-missing --cov-fail-under=85
uv run ruff check .
uv run ruff format --check .
uv run mypy src/synthguard
uv build
```

Do not weaken a failing test, hide an evaluation failure, or make privacy, anonymity, or compliance guarantees. See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
