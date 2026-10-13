# Implementation Plan: SynthGuard `data-core`

## Overview

Implement the first SynthGuard module as a typed, local-only Python library. The module will validate one CSV, create a reviewable profile and SDV metadata, generate Gaussian-copula and CTGAN candidates, and persist complete run artifacts atomically. Evaluation and product interfaces remain outside this phase.

## Approved Decisions

- Python 3.12 with a `src/` package layout and `uv` lockfile.
- CSV-only, single-table MVP.
- 25 MB and 100,000-row input limits; 100,000-row output limit.
- Gaussian Copula is the fast baseline; CTGAN is the slower comparison method.
- Pydantic contracts are the only public boundary.
- Artifact runs are immutable and finalized atomically.
- No network access, user-data logging, database, UI, or MCP implementation in this module.

## Dependency Graph

```text
Project configuration
        ↓
Typed contracts and domain errors
        ↓
CSV validation and fingerprinting
        ↓
Profiling and metadata overrides
        ↓
Synthesizer adapter protocol
        ├── Gaussian Copula adapter
        └── CTGAN adapter
                    ↓
          Atomic artifact manifest
                    ↓
        End-to-end offline verification
```

## Vertical Delivery Slices

### Phase 1: Contract and ingestion foundation

- Task 1 establishes the package, tooling, typed public contracts, and a first executable test.
- Task 2 delivers a complete CSV-to-validated-frame path with fingerprinting and structured errors.

### Checkpoint: Safe ingestion

- The project installs reproducibly.
- A valid fixture loads and an unsafe or invalid source fails through the public error contract.
- Tests, lint, formatting, and types pass.

### Phase 2: Reviewable dataset understanding

- Task 3 turns a validated frame into a deterministic, JSON-serializable profile.
- Task 4 creates SDV metadata and applies validated user overrides.

### Checkpoint: Review before generation

- The caller can inspect every inferred column and warning.
- Unknown or incompatible overrides fail without training a model.

### Phase 3: Candidate generation

- Task 5 introduces the synthesizer adapter and a complete Gaussian-copula run.
- Task 6 adds CTGAN without changing the public generation contract.

### Checkpoint: Two local candidates

- Both methods generate the exact requested row count on committed fixtures.
- Failures remain structured and leave no successful-looking partial run.

### Phase 4: Artifact integrity and hardening

- Task 7 persists immutable CSV, metadata, and manifest artifacts atomically.
- Task 8 closes security, reproducibility, coverage, and documentation gaps.

### Checkpoint: Module complete

- Every `SPEC-data-core.md` success criterion has direct test evidence.
- Full offline quality gates pass with at least 90% module coverage.

## Architecture Decisions

### Public contracts

Only `synthguard.data_core` exports are stable. Internal modules may evolve without becoming accidental consumer dependencies. Inputs and outputs are Pydantic models; expected failures use one `DataCoreError` shape with stable codes.

### Adapter boundary

Generation methods implement one internal adapter protocol. Orchestration validates once, selects a registered adapter, trains it, samples the requested rows, and passes results to artifact persistence. This prevents method-specific behavior from leaking into UI or MCP consumers.

### Filesystem safety

Source files are read-only. Output paths are resolved under a caller-provided root. Runs are written into a temporary generated directory and renamed to their final immutable run ID only after all artifacts succeed.

### Reproducibility

Each manifest records the source fingerprint, reviewed metadata, method, seed, row count, dependency versions, duration, warnings, and artifact checksums. When an underlying method cannot guarantee byte-identical results, the limitation is explicit.

## Verification Strategy

- Unit tests cover validation, inference, override behavior, adapter selection, manifest creation, and path containment.
- Integration tests run both synthesizers against tiny non-sensitive fixtures on CPU.
- Tests patch or isolate nondeterministic timing and identifiers instead of weakening content assertions.
- Complete gates: pytest with coverage, Ruff lint, Ruff format check, and mypy.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| CTGAN is slow or nondeterministic on CPU | High | Tiny fixtures, constrained epochs in tests, explicit reproducibility limitation |
| SDV APIs vary by installed version | High | Lock dependencies and isolate SDV usage behind adapters |
| Type inference misclassifies IDs or categories | Medium | Reviewable profiles, warnings, and validated overrides before training |
| Partial writes look like successful runs | High | Temporary directory plus atomic finalization and cleanup tests |
| Error output leaks source values or paths | High | Structured errors, redaction rules, and regression tests |
| Large files exhaust memory | Medium | Pre-read size check, bounded row count, explicit resource errors |

## Parallelization

Tasks 3 and 4 share contracts and should be sequential. Gaussian and CTGAN adapter implementation can be developed independently after the adapter protocol is fixed, but integration and artifact work must use the merged contract. Documentation can proceed alongside final hardening after behavior stabilizes.

## Open Questions

None blocking. Changes to the approved synthesis methods, limits, or public contract require a spec update before implementation.

---

# Implementation Plan: SynthGuard `evaluation-core`

## Overview

Implement a typed, offline evaluator that validates a real/synthetic artifact pair and produces independent statistical, privacy-risk, and optional classification-utility evidence. The module returns measurements only; threshold decisions remain owned by `quality-gate`.

## Dependency Graph

```text
Evaluation contracts
        ↓
Pair and metadata validation
        ├── Statistical quality adapter
        ├── Privacy evidence adapter
        └── Classification utility adapter
                    ↓
          Evaluation orchestration
                    ↓
       End-to-end verification and docs
```

## Delivery Slices

### Phase 1: Validated evaluation pair

- Evaluation Task 1 defines immutable contracts, stable errors, and package exports.
- Evaluation Task 2 loads bounded artifacts, validates current SDV metadata, checks exact schema order, and fingerprints inputs.

### Checkpoint: Trusted inputs

- Valid pairs produce one internal typed representation.
- Missing, malformed, empty, mismatched, and invalid-metadata inputs fail without leaking source values.

### Phase 2: Independent evidence

- Evaluation Task 3 converts the current SDMetrics quality report into deterministic typed evidence.
- Evaluation Task 4 calculates exact copies, bounded mixed-type nearest-neighbor evidence, and DCR baseline protection.
- Evaluation Task 5 runs the optional leakage-safe weighted-F1 classification experiment.

### Checkpoint: Three evidence dimensions

- Each evaluator is independently testable and returns evidence without threshold decisions.
- Sampling and model splits are deterministic from the request seed.

### Phase 3: Product-ready module

- Evaluation Task 6 orchestrates the complete result and handles partial optional utility cleanly.
- Evaluation Task 7 evaluates actual data-core artifacts, closes coverage gaps, and documents the public API.

### Checkpoint: Module complete

- Every `SPEC-evaluation-core.md` success criterion has direct evidence.
- Full offline quality gates pass with at least 90% evaluation-module coverage.

## Architecture Decisions

- Pydantic contracts form the stable consumer interface; pandas and estimator objects remain internal.
- Validation loads each file once and passes trusted frames to pure metric adapters.
- Current `sdmetrics.reports.QualityReport` and `Metadata` APIs are isolated behind adapters.
- Potentially quadratic privacy work uses deterministic bounded sampling.
- Identifier columns are excluded from proximity calculations but remain part of exact-row matching.
- ML utility uses one fixed logistic-regression methodology so comparisons remain interpretable and reproducible.
- Individual evaluator failures are explicit operational errors; the service never invents replacement scores.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Mixed-type distance is misleading | High | Document encoding/scaling, exclude IDs, expose threshold and raw aggregate distances |
| DCR becomes expensive | High | Seeded row bounds and subsampling metadata |
| Utility test leaks holdout data | High | Split first; fit each preprocessing/model pipeline only on its training source |
| Small classes make stratification impossible | Medium | Validate class counts and fail with `INSUFFICIENT_CLASSES` |
| SDMetrics output schemas change | High | Lock dependencies, adapter tests, and typed conversion |
| Metrics expose sensitive values | High | Return names and aggregate scores only; regression tests scan errors/results |

## Verification Strategy

- Controlled fixtures establish ordering: realistic data should outperform collapsed data.
- Exact-copy fixtures prove privacy signals independently from SDMetrics.
- Utility tests compare two pipelines on one untouched real holdout.
- An end-to-end test generates a data-core run and evaluates its artifacts with network access denied.
- Complete gates: module coverage, full project tests, Ruff, formatting, and mypy.

## Open Questions

None blocking. Threshold decisions, regression, and formal privacy mechanisms remain deferred by specification.

---

# Implementation Plan: SynthGuard `quality-gate`

## Delivery Slices

1. Define immutable policy, candidate, criterion, decision, result, and error contracts.
2. Implement inclusive criteria with explicit optional/required utility behavior.
3. Add fixed transparent composite scoring, deterministic ranking, and winner selection.
4. Verify permutation stability, JSON serialization, value-safe errors, coverage, and docs.

## Architecture Decisions

- The module consumes `EvaluationResult` and never imports evaluator internals.
- Threshold checks and ranking are pure functions with no time, random, network, or filesystem input.
- Near-duplicate rate uses the sampled synthetic row count recorded by evaluation-core.
- A failed candidate still receives a score and rank for diagnosis, but can never become the winner.
- UI and MCP consumers receive the same criterion explanations without recreating policy logic.

## Verification

- Boundary tests for every comparator.
- Required-versus-optional utility tests.
- Input-permutation and tie-break tests.
- Full project tests, Ruff, formatting, mypy, and 95% module coverage.

---

# Implementation Plan: SynthGuard `studio-ui`

1. Add a pure Markdown report builder and test its evidence/limitation sections.
2. Build the Streamlit shell, local upload materialization, profile review, and configuration controls.
3. Connect generation, evaluation, and quality-gate public APIs through session state.
4. Render comparison and criterion evidence plus candidate/report downloads.
5. Verify with Streamlit testing, full quality gates, and a real browser at desktop and mobile sizes.

---

# Implementation Plan: SynthGuard `mcp-server`

1. Implement and test a symlink-aware allowlisted path policy.
2. Add typed MCP input contracts and a framework-independent tool adapter over public APIs.
3. Register the exact five-tool FastMCP stdio surface and normalize domain failures as tool errors.
4. Add an installable entry point, client configuration docs, discovery tests, and end-to-end offline verification.
