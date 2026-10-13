# SynthGuard

**Synthetic data, with receipts.**

SynthGuard is a local-first quality gate for tabular synthetic data. It generates competing datasets, measures whether they preserve useful patterns, checks whether they copy source records too closely, and returns a deterministic pass/fail decision with the evidence behind it.

It runs on your machine, requires no API key, and exposes the same workflow through a Streamlit studio and five MCP tools.

## The problem it solves

Teams often need realistic data for development, testing, demos, and machine-learning experiments, but real customer data can be sensitive. A synthetic-data generator alone does not answer the important questions:

- Did the generated data preserve distributions and relationships?
- Did it reproduce exact or nearly identical source records?
- Can a model trained on it still work on real held-out data?
- Which candidate is safest and most useful under the team's own limits?
- Can someone reproduce and audit the decision later?

SynthGuard turns those questions into one repeatable experiment. It does **not** claim that synthetic data is automatically anonymous, private, or compliant.

## The core idea, in plain language

Imagine that a company has a useful table of customer, health, employee, or financial records. Developers need realistic data for testing and machine-learning work, but sharing the original rows may expose private information.

SynthGuard creates a new, artificial table that tries to preserve the useful patterns of the original. It then checks the candidate before allowing it to be released:

```text
Private CSV
    ↓
Review detected column types
    ↓
Generate one or more synthetic candidates
    ↓
Measure statistical similarity, copy risk, and ML usefulness
    ↓
Apply the selected quality thresholds
    ↓
PASS → download the synthetic CSV and evidence report
FAIL → inspect the evidence and improve the next run
```

A failed result does **not** mean generation crashed. It means a synthetic CSV was produced, but at least one configured quality or privacy-risk threshold was not satisfied. SynthGuard deliberately keeps failed candidates from looking release-ready.

## How a run works

1. **Upload one CSV** or use the fictional demo dataset. Processing stays on the local machine.
2. **Review the inferred schema.** SynthGuard identifies numeric, categorical, boolean, datetime, ID-like, and potentially sensitive columns. These suggestions remain reviewable.
3. **Choose generation settings.** Select Gaussian Copula for a fast statistical baseline, CTGAN for a slower neural candidate, or compare both. Set the row count and random seed.
4. **Optionally choose a prediction target.** This enables the downstream ML utility experiment.
5. **Set the release policy.** The default thresholds cover statistical quality, exact and near copies, record distance, and optional utility retention.
6. **Generate and evaluate.** Every candidate is measured using the same pipeline and ranked from the recorded evidence.
7. **Export only with context.** A passing winner can be downloaded with its Markdown evaluation report. Failed candidates remain visible for diagnosis but are not presented as approved outputs.

## Why it is different

Most demos stop after generating a CSV. SynthGuard treats generation as the start of the workflow:

1. **Competing candidates** — run Gaussian Copula, CTGAN, or both behind one interface.
2. **Three evidence dimensions** — statistical fidelity, copy-risk indicators, and optional downstream ML utility remain visible instead of being hidden in one score.
3. **Policy as data** — every threshold, criterion result, rank, and reason is returned in a typed record.
4. **Deterministic selection** — the same evidence and policy produce the same ranking and winner.
5. **Local by design** — source data is not uploaded to a model or cloud service.
6. **Two real interfaces, one domain workflow** — Streamlit serves people; MCP serves coding agents without duplicating calculations.
7. **Reproducible artifacts** — each run stores reviewed metadata, checksums, configuration, versions, warnings, and timing.

## What is included

| Feature | What it does | Why it matters |
|---|---|---|
| Single CSV input | Accepts one bounded UTF-8 table and preserves the source unchanged | Keeps the first release focused and safe to run locally |
| Automatic column detection | Infers numeric, categorical, boolean, datetime, ID, and potentially sensitive columns for review | Removes setup work without pretending inference is always correct |
| Two synthesis methods | Produces a fast Gaussian Copula candidate and an optional CPU CTGAN candidate | Lets users compare a statistical baseline with a neural generator |
| Statistical comparison | Scores column distributions and column-pair relationships with SDMetrics | Shows whether synthetic data still behaves like the source |
| Exact and near-copy checks | Counts identical rows, mixed-type nearest neighbors, and DCR baseline protection | Surfaces memorization and record-proximity risk |
| ML utility test | Trains equivalent classifiers on real and synthetic training data, then evaluates both on one untouched real holdout | Measures whether synthetic data can support a concrete downstream task |
| Configurable quality gate | Applies inclusive user thresholds and explains every pass, fail, or skipped criterion | Replaces an unexplained “good” score with an auditable decision |
| Comparison workspace | Ranks candidates and displays weak columns, privacy evidence, utility, and criterion details | Makes tradeoffs visible before download |
| Downloadable outputs | Exports the selected synthetic CSV and a Markdown evidence report | Makes results useful outside the app |
| MCP workflow | Offers profile, generate, evaluate, gate, and full-workflow tools over stdio | Lets local agents use the same controlled pipeline |
| Automated verification | Tests domain logic, UI rendering, MCP discovery, paths, packaging, types, style, and coverage | Demonstrates engineering quality beyond a notebook demo |

## Architecture

```text
CSV → profile/review → generate candidates → evaluate evidence → apply policy
                                                               │
                                            ┌──────────────────┴───────────────┐
                                            ▼                                  ▼
                                   Streamlit studio                       MCP server
```

The domain modules are independent from Streamlit and FastMCP. `evaluation-core` measures evidence; `quality-gate` alone decides whether that evidence meets the supplied policy. See the [architecture guide](docs/ARCHITECTURE.md), [capability map](CAPABILITY_MAP.md), and [threat model](docs/THREAT_MODEL.md).

## Quick start

Requirements: Python 3.12 and [`uv`](https://docs.astral.sh/uv/).

Clone the repository and enter the project:

```bash
git clone https://github.com/HICHAM-RK/SynthGuard.git
cd SynthGuard
```

Install the locked dependencies:

```bash
uv sync --locked --all-extras
```

Launch the web app:

```bash
uv run streamlit run src/synthguard/studio_ui/app.py
```

Open the local address printed by Streamlit, normally [http://localhost:8501](http://localhost:8501). The application runs locally and does not require an API key.

Choose **Try the demo dataset** for a no-setup walkthrough, or upload one UTF-8 CSV up to 25 MB. A committed fictional dataset is also available at [examples/demo_customers.csv](examples/demo_customers.csv).

To stop the app, return to the terminal and press `Ctrl+C`.

For the fastest programmatic demo, generate one Gaussian candidate:

```python
from pathlib import Path

from synthguard.data_core import GenerationMethod
from synthguard.quality_gate import GatePolicy
from synthguard.workflow import run_workflow

run = run_workflow(
    source_csv=Path("examples/demo_customers.csv"),
    output_directory=Path("runs"),
    methods=(GenerationMethod.GAUSSIAN_COPULA,),
    row_count=100,
    random_seed=42,
    classification_target=None,  # Set to "churned" to include the ML utility experiment.
    policy=GatePolicy(),
)

print(run.gate.winner_candidate_id)
print(run.report_markdown)
```

Each successful candidate creates:

```text
runs/<run-id>/
├── synthetic.csv
├── metadata.json
└── manifest.json
```

## MCP setup

Allow only the source/output roots the server needs, then start its stdio transport:

```bash
SYNTHGUARD_ALLOWED_ROOTS="/path/to/data:/path/to/output" uv run synthguard-mcp
```

Example client configuration:

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

Use `;` instead of `:` between allowed roots on Windows. If the variable is omitted, only the server process's current working directory is allowed.

The five tools are:

- `profile_dataset`
- `generate_synthetic_data`
- `evaluate_synthetic_data`
- `gate_candidates`
- `run_synthguard_workflow`

They return aggregate evidence and artifact paths, never source rows. See [SPEC-mcp-server.md](SPEC-mcp-server.md) for the exact boundary.

## Evidence and decisions

The default gate evaluates:

- minimum statistical quality;
- maximum exact-copy rate;
- maximum near-copy rate;
- minimum DCR baseline-protection score; and
- minimum utility retention when utility is requested or required.

A failed candidate still receives a score and rank so users can diagnose it, but only a passing candidate can win. If none pass, SynthGuard returns no winner instead of silently choosing a failed dataset.

## Development and verification

```bash
uv run pytest --cov=synthguard --cov-report=term-missing --cov-fail-under=85
uv run ruff check .
uv run ruff format --check .
uv run mypy src/synthguard
uv build
```

GitHub Actions repeats lint, formatting, type checking, tests, coverage, dependency audit, package build, and isolated wheel smoke checks for every pull request and push to `main`.

## Safety and limitations

- Processing is local and makes no remote model call.
- One single-table CSV is supported; relational and time-series synthesis are out of scope.
- Sensitive-column and identifier detection is advisory and requires human review.
- Exact copies, nearest-neighbor distances, and DCR are risk indicators, not privacy guarantees.
- No differential privacy, anonymity proof, regulatory certification, or production approval is provided.
- Statistical and ML scores apply only to the tested candidate, task, split, and policy.
- CTGAN can be slow on CPU and cannot promise byte-identical output across dependency versions.
- Do not commit source datasets or generated user runs.

Read [SECURITY.md](SECURITY.md) and the [threat model](docs/THREAT_MODEL.md) before using real data.

## Project documents

- [Architecture](docs/ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Release evidence](docs/RELEASE_EVIDENCE.md)
- [Security policy](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)
- [MIT license](LICENSE)
- [Release-quality specification](SPEC-release-quality.md)
- [Agent workflow](AGENTS.md)

SynthGuard calls a candidate “passing” only under the exact policy stored with its result. The final decision to release or use that dataset remains a human responsibility.
