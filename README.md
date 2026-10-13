# SynthGuard

SynthGuard is a local-first synthetic-data quality gate. Its goal is to generate candidate tabular datasets, measure whether they remain useful without copying source records too closely, and expose reproducible decisions through a Streamlit studio and MCP tools.

The implemented `data-core`, `evaluation-core`, and `quality-gate` modules safely generate immutable Gaussian Copula or CTGAN runs, compare each candidate with its source, and apply explicit thresholds to select the strongest passing candidate. The Streamlit studio and MCP server are tracked as the next modules in `CAPABILITY_MAP.md`.

## Why this project exists

Development and ML teams need realistic data, but real customer or operational datasets may be sensitive. Generating rows is only the beginning: a useful system must preserve structure, record exactly how data was produced, expose limitations, and eventually prove both utility and privacy risk. SynthGuard is being built around that evidence-first workflow.

## Current capabilities

- Local CSV ingestion with byte, row, encoding, and structural limits
- Deterministic column profiling with advisory identifier and sensitive-column flags
- Reviewable SDV metadata and validated semantic-type overrides
- Gaussian Copula and CPU CTGAN generation through one contract
- Immutable run directories containing synthetic CSV, metadata, and a manifest
- SHA-256 source fingerprints and artifact checksums
- SDMetrics statistical quality scores for distributions and column relationships
- Exact-copy detection plus seeded, bounded mixed-type nearest-neighbor evidence
- SDMetrics DCR baseline protection with explicit metric provenance
- Optional leakage-safe classification utility using weighted F1 on held-out real rows
- One typed, JSON-serializable evaluation result shared by future interfaces
- Configurable, explainable pass/fail thresholds with deterministic candidate ranking
- Streamlit audit studio with a built-in demo, comparison workspace, and CSV/report downloads
- Five-tool FastMCP stdio server with an explicit local filesystem allowlist
- Structured errors that avoid echoing source values or unrestricted paths
- Offline automated tests, static typing, linting, and formatting gates

## Quick start

Requirements: Python 3.12 and `uv`.

```bash
uv sync --all-extras
```

Launch the local studio:

```bash
uv run streamlit run src/synthguard/studio_ui/app.py
```

Use **Try the demo dataset** for a no-setup walkthrough, or upload one UTF-8 CSV up to 25 MB. The studio never renders source rows and keeps session artifacts in a local temporary directory.

### MCP setup

Start the stdio server directly:

```bash
SYNTHGUARD_ALLOWED_ROOTS="/path/to/data:/path/to/output" uv run synthguard-mcp
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "synthguard": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/SynthGuard", "synthguard-mcp"],
      "env": {
        "SYNTHGUARD_ALLOWED_ROOTS": "/path/to/data:/path/to/output"
      }
    }
  }
}
```

On Windows, separate allowed roots with `;` instead of `:`. If the variable is omitted, only the server process’s current working directory is allowed. The server exposes `profile_dataset`, `generate_synthetic_data`, `evaluate_synthetic_data`, `gate_candidates`, and `run_synthguard_workflow`.

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

Evaluate the generated candidate:

```python
from synthguard.evaluation_core import EvaluationRequest, evaluate_candidate

evaluation = evaluate_candidate(
    EvaluationRequest(
        real_csv=source,
        synthetic_csv=result.artifacts.synthetic_csv,
        metadata_json=result.artifacts.metadata_json,
        classification_target="churned",  # Optional categorical or boolean target
        random_seed=42,
    )
)

print(evaluation.statistical.overall_score)
print(evaluation.privacy.exact_match_count)
print(evaluation.privacy.dcr_baseline_protection_score)
print(evaluation.utility.utility_retention if evaluation.utility else None)
```

Apply explicit thresholds and compare candidates:

```python
from synthguard.quality_gate import CandidateEvidence, GatePolicy, GateRequest, apply_quality_gate

gate = apply_quality_gate(
    GateRequest(
        candidates=(CandidateEvidence(candidate_id="gaussian", evaluation=evaluation),),
        policy=GatePolicy(
            min_statistical_score=0.75,
            max_exact_match_rate=0.0,
            max_near_duplicate_rate=0.05,
            min_dcr_score=0.5,
            min_utility_retention=0.8,
        ),
    )
)

print(gate.winner_candidate_id)
print(gate.candidates[0].failed_criteria)
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
- `SPEC-evaluation-core.md` defines the implemented evidence contract.
- `SPEC-quality-gate.md` defines the implemented decision and ranking contract.
- `SPEC-studio-ui.md` defines the implemented local product experience.
- `SPEC-mcp-server.md` defines the implemented agent tool and filesystem-safety contract.
- `tasks/plan.md` records architecture decisions and risks.
- `tasks/todo.md` records acceptance criteria and verification evidence.
- `AGENTS.md` defines the rules Codex and other coding agents must follow.

## Safety and limitations

- Processing is local and does not require an API key.
- Only one CSV table is supported in the current module.
- Sensitive-column detection is advisory and must be reviewed by a person.
- Synthetic output is not automatically anonymous, private, or compliant.
- Exact matches, near-neighbor distances, and DCR are risk indicators—not privacy guarantees.
- Statistical and ML scores describe this candidate under documented baselines; they do not prove fitness for every workload.
- `evaluation-core` returns independent evidence only. `quality-gate` applies user-visible thresholds and rankings, but a passing result is still not a privacy or compliance certification.
- The locked SDV API controls internal sampling state, so exact output may differ across dependency versions even when the requested seed is unchanged.
- Do not commit source datasets or generated user runs.

SynthGuard calls a candidate “passing” only under the exact policy returned with the gate result. Generated artifacts remain synthetic candidates, not approved safe datasets.
