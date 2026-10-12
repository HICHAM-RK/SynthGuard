# SynthGuard

SynthGuard is a local-first synthetic-data quality gate. Its goal is to generate candidate tabular datasets, measure whether they remain useful without copying source records too closely, and expose reproducible decisions through a Streamlit studio and MCP tools.

The first implemented module, `data-core`, safely profiles one CSV and generates immutable Gaussian Copula or CTGAN runs. Quality, privacy, ML-utility evaluation, the pass/fail gate, Streamlit, and MCP are tracked as the next modules in `CAPABILITY_MAP.md`.

## Why this project exists

Development and ML teams need realistic data, but real customer or operational datasets may be sensitive. Generating rows is only the beginning: a useful system must preserve structure, record exactly how data was produced, expose limitations, and eventually prove both utility and privacy risk. SynthGuard is being built around that evidence-first workflow.

## Current capabilities

- Local CSV ingestion with byte, row, encoding, and structural limits
- Deterministic column profiling with advisory identifier and sensitive-column flags
- Reviewable SDV metadata and validated semantic-type overrides
- Gaussian Copula and CPU CTGAN generation through one contract
- Immutable run directories containing synthetic CSV, metadata, and a manifest
- SHA-256 source fingerprints and artifact checksums
- Structured errors that avoid echoing source values or unrestricted paths
- Offline automated tests, static typing, linting, and formatting gates

## Quick start

Requirements: Python 3.12 and `uv`.

```bash
uv sync --all-extras
```

```python
from pathlib import Path

from synthguard.data_core import (
    GenerationMethod,
    GenerationRequest,
    ProfileRequest,
    SemanticType,
    generate_candidate,
    profile_csv,
)

source = Path("customers.csv")
profile = profile_csv(ProfileRequest(source_path=source))

for column in profile.columns:
    print(column.name, column.semantic_type, column.is_sensitive_candidate)

result = generate_candidate(
    GenerationRequest(
        source_path=source,
        output_directory=Path("runs"),
        method=GenerationMethod.GAUSSIAN_COPULA,
        row_count=1_000,
        random_seed=42,
        column_overrides={"customer_id": SemanticType.IDENTIFIER},
    )
)

print(result.artifacts.synthetic_csv)
print(result.artifacts.manifest_json)
```

Each successful run creates:

```text
runs/<run-id>/
├── synthetic.csv
├── metadata.json
└── manifest.json
```

The manifest records the source fingerprint, method, requested seed, row count, dependency versions, warnings, duration, and artifact checksums.

## Development commands

```bash
uv run pytest --cov=synthguard --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy src/synthguard
```

## Architecture and progress

- `CAPABILITY_MAP.md` defines module ownership and build order.
- `SPEC-data-core.md` defines the implemented module contract.
- `tasks/plan.md` records architecture decisions and risks.
- `tasks/todo.md` records acceptance criteria and verification evidence.
- `AGENTS.md` defines the rules Codex and other coding agents must follow.

## Safety and limitations

- Processing is local and does not require an API key.
- Only one CSV table is supported in the current module.
- Sensitive-column detection is advisory and must be reviewed by a person.
- Synthetic output is not automatically anonymous, private, or compliant.
- The locked SDV API controls internal sampling state, so exact output may differ across dependency versions even when the requested seed is unchanged.
- Do not commit source datasets or generated user runs.

SynthGuard will only call a candidate “accepted” after the future evaluation and quality-gate modules provide measurable evidence. Current generation artifacts should be treated as candidates, not approved safe datasets.
