# Capability Map: SynthGuard

SynthGuard is a local-first synthetic-data quality gate. It generates candidate tabular datasets, measures whether they are useful and privacy-conscious, and exposes the same workflow through a Streamlit studio and MCP tools.

| Module id | Responsibility | Depends on |
|---|---|---|
| `data-core` | Ingest one CSV, infer a reviewable schema, generate synthetic candidates, and persist reproducible artifacts | — |
| `evaluation-core` | Measure statistical fidelity, exact/near-copy privacy risk, and downstream ML utility | `data-core` |
| `quality-gate` | Apply user thresholds, rank candidates, explain failures, and select the safest useful dataset | `evaluation-core` |
| `studio-ui` | Provide the Streamlit upload, configuration, comparison, report, and download experience | `quality-gate` |
| `mcp-server` | Expose the controlled workflow to MCP clients with typed tools and safe file access | `quality-gate` |
| `release-quality` | Supply automated tests, demo data, documentation, security checks, packaging, and portfolio evidence | `studio-ui`, `mcp-server` |

Build order:

```text
data-core
    ↓
evaluation-core
    ↓
quality-gate
    ↓
studio-ui + mcp-server
    ↓
release-quality
```

## Stable Boundaries

- `data-core` owns dataset ingestion, inferred metadata, synthesis configuration, and generated artifacts. It does not decide whether a candidate is acceptable.
- `evaluation-core` calculates evidence. It does not select a winner or mutate generated data.
- `quality-gate` turns evaluation evidence and user thresholds into deterministic decisions.
- `studio-ui` and `mcp-server` are consumers of the same application services; neither duplicates domain logic.
- `release-quality` verifies and packages the product but does not introduce product behavior.

Each module has a corresponding `SPEC-<module-id>.md`. A module is planned and implemented only after its specification is approved.
