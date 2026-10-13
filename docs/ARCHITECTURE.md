# Architecture

SynthGuard separates measurement from decisions and exposes one workflow through two adapters.

```text
CSV
 │
 ▼
data-core ── profile → reviewed metadata → candidate artifacts
 │
 ▼
evaluation-core ── statistical + privacy-risk + optional utility evidence
 │
 ▼
quality-gate ── explicit criteria → deterministic ranking → winner/no winner
 │
 ├── Streamlit studio
 └── FastMCP tools
```

## Module boundaries

- `data-core` owns bounded ingestion, advisory profiling, SDV adapters, and atomic artifacts.
- `evaluation-core` owns measurements and never makes a pass/fail decision.
- `quality-gate` owns transparent policy decisions and deterministic ranking.
- `workflow.py` composes those public APIs once for both interfaces.
- `studio-ui` renders the workflow but does not recalculate evidence.
- `mcp-server` validates local paths and translates typed results into MCP responses.

Dependency flow is one-way. UI and protocol concerns cannot enter domain modules. Pydantic contracts are stable boundaries; pandas, SDV, SDMetrics, scikit-learn, Streamlit, and FastMCP objects stay inside their owning adapters.

## Artifact lifecycle

Each generation writes to a temporary directory below a validated output root. Only a complete run is renamed to its immutable run ID. A run contains `synthetic.csv`, reviewed `metadata.json`, and `manifest.json` with source fingerprint, configuration, dependency versions, duration, warnings, and checksums.

## Why the quality gate matters

A generator can produce plausible-looking rows while losing correlations, copying records, or becoming useless for ML. SynthGuard keeps those dimensions separate, shows the evidence, and applies user-owned thresholds. A pass means only that the candidate met that recorded policy.

The complete ownership map is in [CAPABILITY_MAP.md](../CAPABILITY_MAP.md).
