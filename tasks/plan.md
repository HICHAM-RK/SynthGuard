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
