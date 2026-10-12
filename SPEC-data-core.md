# Spec: SynthGuard `data-core`

## Status

Approved for implementation. This specification is the contract for the first module in `CAPABILITY_MAP.md`.

## Assumptions

1. The one-week MVP processes one local CSV table per run; relational and multi-table synthesis are deferred.
2. All data processing remains local. The module makes no network calls and requires no paid API.
3. Python 3.12 and `uv` are the supported development environment.
4. SDV is the synthesis library. The MVP compares a fast Gaussian-copula candidate with a CTGAN candidate.
5. The default limit is a 25 MB CSV and 100,000 input rows so a local machine cannot be overwhelmed accidentally.
6. Sensitive-column detection is advisory. Users must review inferred types before generation; the product does not claim regulatory compliance.
7. Reproducibility requires a dataset fingerprint, configuration manifest, library versions, and caller-provided random seed.

## Objective

Build a local, framework-independent Python module that safely ingests one CSV, produces a reviewable dataset profile, and generates reproducible synthetic candidates using two synthesis methods. Both the future Streamlit UI and MCP server must consume the same typed interface.

The module serves data scientists and developers who need realistic test data without handing the product a cloud credential or uploading their source dataset to a third party.

### User stories

- As a user, I can inspect an uploaded CSV before training so incorrect inferred types do not silently affect generation.
- As a user, I can override inferred column types and mark columns as identifiers or sensitive candidates.
- As a user, I can generate a requested number of rows with a chosen method and random seed.
- As a user, I can reproduce a generation run from its saved manifest.
- As an interface developer, I receive typed success results and stable machine-readable errors.

## In Scope

- CSV parsing with explicit size, row, encoding, and structural validation.
- Dataset fingerprinting without persisting raw source values in logs.
- Column profiling: physical type, semantic type candidate, null rate, uniqueness, cardinality, and safe summary statistics.
- Reviewable SDV metadata generation plus validated caller overrides.
- Synthetic generation with Gaussian copula and CTGAN methods.
- Deterministic artifact layout for synthetic CSV, metadata, and run manifest.
- Typed Python contracts and structured domain errors.
- Unit and integration tests with committed non-sensitive fixtures.

## Out of Scope

- Quality, privacy, or ML-utility scoring; these belong to `evaluation-core`.
- Pass/fail decisions and candidate ranking; these belong to `quality-gate`.
- Charts, Streamlit pages, MCP tools, authentication, hosted storage, and background workers.
- Excel, JSON, Parquet, image, audio, text, or relational multi-table generation.
- Claims of anonymization, differential privacy, GDPR, HIPAA, or other regulatory compliance.

## Tech Stack

- Python `>=3.12,<3.13`
- `uv` for dependency and command management
- `pandas` for CSV processing and profiling
- `pydantic` v2 for input/output contracts
- `sdv` for metadata and synthesis
- `pytest` and `pytest-cov` for tests
- `ruff` for formatting and linting
- `mypy` for static type checking

Dependency versions will be locked in `uv.lock`. Application modules import only public APIs from their dependencies.

## Commands

These commands become mandatory once the project scaffold is implemented:

```bash
# Install all development dependencies
uv sync --all-extras

# Run focused data-core tests
uv run pytest tests/data_core -q

# Run the complete test suite with coverage
uv run pytest --cov=synthguard --cov-report=term-missing

# Lint and formatting verification
uv run ruff check .
uv run ruff format --check .

# Static type checking
uv run mypy src/synthguard
```

## Project Structure

```text
src/synthguard/data_core/
├── __init__.py       # Public exports only
├── contracts.py      # Pydantic inputs, outputs, enums, and errors
├── ingestion.py      # CSV validation, parsing, and fingerprinting
├── profiling.py      # Column inference and safe summaries
├── metadata.py       # SDV metadata construction and override validation
├── synthesis.py      # Synthesizer adapters and generation orchestration
└── artifacts.py      # Atomic artifact persistence and manifest creation

tests/data_core/
├── fixtures/         # Small, non-sensitive CSV fixtures
├── test_ingestion.py
├── test_profiling.py
├── test_metadata.py
├── test_synthesis.py
└── test_artifacts.py
```

## Public Interface

Only names exported from `synthguard.data_core` are public. Consumers must not import internal implementation modules directly.

```python
from pathlib import Path

from pydantic import BaseModel, Field


class ProfileRequest(BaseModel):
    source_path: Path
    max_bytes: int = 25_000_000
    max_rows: int = 100_000


class GenerationRequest(BaseModel):
    source_path: Path
    output_directory: Path
    method: str
    row_count: int = Field(ge=1, le=100_000)
    random_seed: int
    column_overrides: dict[str, str] = {}


def profile_csv(request: ProfileRequest) -> "DatasetProfile": ...


def generate_candidate(request: GenerationRequest) -> "GenerationResult": ...
```

The implementation must replace mutable defaults with safe factories. The example above communicates the consumer-facing shape, not final implementation syntax.

### Core contracts

`DatasetProfile` contains:

- `dataset_fingerprint`: SHA-256 of the source bytes.
- `row_count` and `column_count`.
- `columns`: ordered column profiles.
- `warnings`: structured inference and data-quality warnings.
- `inferred_metadata`: reviewable SDV-compatible metadata.

Each column profile contains:

- `name`.
- `physical_type`: integer, float, boolean, string, datetime, or unknown.
- `semantic_type`: numerical, categorical, datetime, boolean, identifier, or unknown.
- `is_sensitive_candidate` and non-authoritative `sensitivity_reason`.
- `null_rate`, `unique_rate`, and `cardinality`.
- Safe summaries that do not include complete raw rows or secret-like values.

`GenerationResult` contains:

- `run_id`: stable UUID generated once per generation intent.
- `method`: `GAUSSIAN_COPULA` or `CTGAN`.
- `row_count`, `random_seed`, and dataset fingerprint.
- Paths to the synthetic CSV, reviewed metadata JSON, and run manifest.
- Training duration and structured warnings.

### Error contract

Every expected failure raises `DataCoreError` with:

```python
class DataCoreError(Exception):
    code: str
    message: str
    details: dict[str, object]
```

Stable error codes include:

- `FILE_NOT_FOUND`
- `FILE_TOO_LARGE`
- `ROW_LIMIT_EXCEEDED`
- `UNSUPPORTED_ENCODING`
- `INVALID_CSV`
- `EMPTY_DATASET`
- `INVALID_OVERRIDE`
- `UNSUPPORTED_METHOD`
- `TRAINING_FAILED`
- `ARTIFACT_WRITE_FAILED`

Errors must not include raw rows, stack traces, credentials, or unrestricted filesystem details in their public message.

## Behavioral Requirements

### Ingestion

- Reject missing, empty, malformed, oversized, or structurally inconsistent CSV files before synthesis.
- Accept UTF-8 and UTF-8 with BOM. Other encodings fail explicitly in the MVP.
- Preserve source column order.
- Never modify the source file.
- Do not log source rows or full cell values.

### Profiling and metadata

- Inference must be deterministic for the same source bytes and configuration.
- Identifier and sensitive-column detection must be labelled as suggestions, never guarantees.
- Overrides may change known columns only and must reject incompatible or unknown values.
- Profiles must remain JSON serializable.

### Synthesis

- Both supported methods implement one internal adapter protocol.
- Generation must honor the requested row count or fail explicitly.
- The same source, reviewed metadata, method, seed, and dependency versions should reproduce the same result where the underlying library supports determinism; limitations must be recorded in the manifest.
- A failed candidate must not leave a partial artifact set that appears successful.

### Artifact safety

- Write artifacts to a temporary run directory and atomically finalize them after all required files succeed.
- Refuse output paths outside the caller-provided output root after path resolution.
- Never overwrite an existing completed run directory.
- Use generated run IDs for directories instead of user-controlled names.

## Code Style

- Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for enum values.
- Type every public function and avoid `Any` at module boundaries.
- Keep I/O at the edges and keep profiling transformations pure where practical.
- Prefer small adapters over condition-heavy orchestration.
- Use structured domain errors rather than returning error strings.

```python
def profile_csv(request: ProfileRequest) -> DatasetProfile:
    source = validate_source(request)
    frame = read_csv(source, max_rows=request.max_rows)
    return build_profile(frame, fingerprint=source.fingerprint)
```

## Testing Strategy

### Unit tests

- Validate request bounds and override schemas.
- Exercise type inference, null handling, high-cardinality detection, and deterministic profiles.
- Test path containment and artifact finalization.
- Test structured errors without matching fragile full message text.

### Integration tests

- Profile a committed fixture and validate the complete contract.
- Generate small Gaussian-copula and CTGAN candidates on CPU.
- Confirm requested row counts and required artifact files.
- Confirm source files remain unchanged.
- Re-run a seeded fast-method fixture and verify reproducibility where supported.

### Test quality bar

- At least 90% statement coverage for `src/synthguard/data_core`.
- No test may require network access, paid credentials, or a GPU.
- CTGAN tests use a tiny fixture and constrained epochs to keep the suite practical.
- Security-sensitive path and data-leakage behavior requires explicit regression tests.

## Boundaries

### Always

- Validate untrusted file paths, CSV content, overrides, and row counts at the public boundary.
- Preserve input files and store generation metadata with each candidate.
- Keep processing local and tests offline.
- Run focused tests, linting, formatting checks, and type checks before committing.
- Document observable contract changes before implementation.

### Ask first

- Add or replace a synthesis method.
- Increase default file, row, or generated-row limits.
- Change artifact formats or public contract fields.
- Add network access, telemetry, a database, or a background worker.
- Introduce a dependency outside the approved stack.

### Never

- Upload user data or generated data to an external service.
- Log raw datasets, source rows, credentials, or complete identifier values.
- Claim generated data is anonymous, compliant, or safe without supporting evidence.
- Silently coerce malformed data, ignore failed overrides, or return partial runs as successful.
- Read or write outside validated source and output roots.
- Commit real sensitive data, generated user artifacts, or local environment files.

## Success Criteria

- A valid CSV up to the documented limits produces a deterministic, JSON-serializable profile.
- Users can review and override inferred semantic types before generation.
- Both Gaussian-copula and CTGAN candidates can be generated locally on CPU with an exact requested row count.
- Every successful run creates a synthetic CSV, metadata JSON, and reproducibility manifest in an isolated run directory.
- Invalid files, invalid overrides, unsupported methods, training failures, and unsafe paths produce stable structured errors.
- Focused tests pass offline with at least 90% statement coverage.
- Source datasets remain unchanged and raw values do not appear in logs or public errors.

## Open Questions

No blocking questions. The approved MVP uses CTGAN as the slower comparison method, keeps resource limits in Python configuration, and caps generated output at 100,000 rows.
