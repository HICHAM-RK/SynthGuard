# SynthGuard Agent Instructions

## Mission

Build SynthGuard as a local-first synthetic-data quality gate. The product must generate candidate tabular datasets, measure their statistical usefulness and privacy risk, and expose deterministic decisions through both Streamlit and MCP interfaces.

## Sources of Truth

Read these before changing behavior:

1. `CAPABILITY_MAP.md` for module ownership and dependency direction.
2. The active `SPEC-<module-id>.md` for requirements and public contracts.
3. `tasks/plan.md` for technical order and risks.
4. `tasks/todo.md` for the current task and verification commands.
5. Existing source and tests for implemented patterns.

If code and a specification disagree, stop and surface the conflict. Update an approved specification before changing its contract.

## Current Stack

- Python 3.12
- `uv` for dependencies and commands
- Pydantic v2 for contracts
- pandas and SDV for local tabular processing
- Streamlit for the future studio interface
- FastMCP for the future MCP server
- pytest, pytest-cov, Ruff, and mypy for quality checks

## Required Commands

```bash
uv sync --all-extras
uv run pytest --cov=synthguard --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy src/synthguard
```

Use focused tests while developing, then run the complete relevant gate before declaring a task complete.

## Implementation Workflow

1. Work on the first unchecked task in `tasks/todo.md` whose dependencies are complete.
2. Load only the relevant spec sections, source files, and tests.
3. Write or update a failing test before changing behavior.
4. Implement the smallest complete vertical slice that satisfies the task.
5. Run focused tests, then lint, format, and type checks.
6. Update the task checklist with verified results.
7. Keep commits atomic and describe why the change exists.

Do not mark a task complete from inspection alone when an executable verification is available.

## Code Conventions

- Use `snake_case` for modules, functions, and variables.
- Use `PascalCase` for classes and Pydantic models.
- Use `UPPER_SNAKE_CASE` for enum values.
- Type every public function; avoid `Any` at boundaries.
- Validate untrusted data only at boundaries, then rely on internal types.
- Keep domain logic independent from Streamlit and MCP.
- Return typed results and raise structured domain errors; never return ad hoc error strings.
- Prefer pure transformations and dependency injection over hidden global state.
- Import public interfaces from package `__init__.py`; consumers must not depend on internal modules.

## Data and Privacy Boundaries

### Always

- Keep all processing local and offline unless an approved future spec changes this.
- Validate and resolve every input and output path.
- Preserve source datasets unchanged.
- Record reproducibility metadata for every generation run.
- Use synthetic, non-sensitive fixtures in tests and documentation.
- Treat sensitive-column inference as advisory, not authoritative.

### Ask first

- Add a dependency, network access, telemetry, database, or background worker.
- Change a public contract, artifact format, resource limit, or synthesis method.
- Modify module ownership or dependency direction.
- Add claims about anonymization, privacy guarantees, or regulatory compliance.

### Never

- Commit `.env` files, credentials, source user datasets, or generated user artifacts.
- Log raw rows, complete identifiers, secrets, or unrestricted filesystem paths.
- Read or write outside validated roots.
- Hide a failed evaluation or return partial output as a successful run.
- weaken, delete, or skip a failing test merely to make a gate pass.
- Duplicate domain logic inside UI or MCP adapters.

## Definition of Done

A task is complete only when:

- Its acceptance criteria are satisfied.
- Focused and relevant regression tests pass.
- Ruff formatting and lint checks pass.
- mypy passes for affected modules.
- No secrets or sensitive fixtures appear in the diff.
- User-visible or contract changes are documented.
- `tasks/todo.md` reflects the verified state and next task.
