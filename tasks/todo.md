# SynthGuard `data-core` Task List

## Task 1: Establish package and public contracts

**Description:** Create the Python package scaffold, development configuration, enums, Pydantic request/result models, and structured `DataCoreError` contract.

**Acceptance criteria:**

- [x] `uv sync --all-extras` installs a locked Python 3.12 environment.
- [x] Public contracts reject invalid method names, row counts, and empty paths.
- [x] Only intended names are exported from `synthguard.data_core`.

**Verification:**

- [x] `uv run pytest tests/data_core/test_contracts.py -q` — 7 passed.
- [x] `uv run ruff check . && uv run ruff format --check .` — passed.
- [x] `uv run mypy src/synthguard` — passed with no issues.

**Dependencies:** None

**Files likely touched:**

- `pyproject.toml`
- `src/synthguard/data_core/__init__.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_contracts.py`

**Estimated scope:** Medium

## Task 2: Deliver safe CSV ingestion

**Description:** Validate file location, size, encoding, structure, and row limits; load a frame without modifying the source; calculate a SHA-256 source fingerprint.

**Acceptance criteria:**

- [x] Valid UTF-8 and UTF-8 BOM fixtures load with column order preserved.
- [x] Missing, empty, oversized, malformed, unsupported-encoding, and over-row-limit sources return stable error codes.
- [x] Errors and logs contain no source rows or complete cell values.

**Verification:**

- [x] `uv run pytest tests/data_core/test_ingestion.py -q` — 11 passed.
- [x] Automated before/after SHA-256 comparison confirms the source fixture remains unchanged.

**Dependencies:** Task 1

**Files likely touched:**

- `src/synthguard/data_core/ingestion.py`
- `tests/data_core/test_ingestion.py`
- `tests/data_core/fixtures/customers.csv`

**Estimated scope:** Medium

## Checkpoint: Contract and ingestion

- [x] Tasks 1-2 acceptance criteria are checked with evidence.
- [x] Focused tests, Ruff, and mypy pass.
- [x] Public errors are structured and do not leak fixture values.

## Task 3: Produce deterministic dataset profiles

**Description:** Infer physical and semantic type candidates, calculate safe summary metrics, flag likely identifiers/sensitive columns, and return a JSON-serializable profile.

**Acceptance criteria:**

- [ ] Repeated profiling of the same fixture produces the same ordered contract.
- [ ] Nulls, booleans, dates, categories, numerical fields, and high-cardinality identifiers are represented correctly in fixtures.
- [ ] Sensitive-column flags are explicitly advisory and include a reason.

**Verification:**

- [ ] `uv run pytest tests/data_core/test_profiling.py -q`
- [ ] Serialize a complete profile with Pydantic JSON output.

**Dependencies:** Task 2

**Files likely touched:**

- `src/synthguard/data_core/profiling.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_profiling.py`
- `tests/data_core/fixtures/mixed_types.csv`

**Estimated scope:** Medium

## Task 4: Build reviewable SDV metadata

**Description:** Translate a dataset profile into SDV metadata and apply validated semantic-type overrides before synthesis.

**Acceptance criteria:**

- [ ] Every input column appears exactly once in generated metadata.
- [ ] Valid overrides update known columns without mutating the original profile.
- [ ] Unknown columns and unsupported overrides fail with `INVALID_OVERRIDE`.

**Verification:**

- [ ] `uv run pytest tests/data_core/test_metadata.py -q`
- [ ] Validate generated metadata through the locked SDV API.

**Dependencies:** Task 3

**Files likely touched:**

- `src/synthguard/data_core/metadata.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_metadata.py`

**Estimated scope:** Medium

## Checkpoint: Reviewable metadata

- [ ] Tasks 3-4 acceptance criteria are checked with evidence.
- [ ] A caller can profile, review, and override a fixture before training.
- [ ] All quality commands pass.

## Task 5: Generate a Gaussian-copula candidate

**Description:** Define the internal synthesizer protocol and implement the fast Gaussian-copula path through the public `generate_candidate` contract.

**Acceptance criteria:**

- [ ] The adapter trains from reviewed metadata and produces exactly the requested rows.
- [ ] Unsupported methods and training failures preserve stable public errors.
- [ ] Method-specific objects do not leak through the public result contract.

**Verification:**

- [ ] `uv run pytest tests/data_core/test_synthesis.py -k gaussian -q`
- [ ] Generate a 50-row candidate from the committed customer fixture.

**Dependencies:** Task 4

**Files likely touched:**

- `src/synthguard/data_core/synthesis.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_synthesis.py`

**Estimated scope:** Medium

## Task 6: Add the CTGAN candidate

**Description:** Add CTGAN behind the same adapter boundary, with configurable test epochs and explicit reproducibility warnings where necessary.

**Acceptance criteria:**

- [ ] CTGAN produces exactly the requested row count on CPU.
- [ ] Test configuration limits training time without changing production defaults silently.
- [ ] The public contract remains unchanged from Task 5.

**Verification:**

- [ ] `uv run pytest tests/data_core/test_synthesis.py -k ctgan -q`
- [ ] Run one tiny CPU generation and record its duration in the result.

**Dependencies:** Task 5

**Files likely touched:**

- `src/synthguard/data_core/synthesis.py`
- `tests/data_core/test_synthesis.py`

**Estimated scope:** Small

## Checkpoint: Two generation methods

- [ ] Tasks 5-6 acceptance criteria are checked with evidence.
- [ ] Both adapters satisfy the same contract and run offline.
- [ ] All quality commands pass.

## Task 7: Persist atomic run artifacts

**Description:** Save each successful candidate as an immutable run containing synthetic CSV, reviewed metadata, and a complete reproducibility manifest with checksums.

**Acceptance criteria:**

- [ ] Successful runs finalize all three required artifacts beneath the validated output root.
- [ ] Existing completed runs are never overwritten.
- [ ] Simulated write failures leave no directory that appears complete.

**Verification:**

- [ ] `uv run pytest tests/data_core/test_artifacts.py -q`
- [ ] Inspect one manifest and verify artifact checksums.

**Dependencies:** Tasks 5-6

**Files likely touched:**

- `src/synthguard/data_core/artifacts.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_artifacts.py`

**Estimated scope:** Medium

## Task 8: Harden and verify the module

**Description:** Add end-to-end regression tests, close coverage gaps, verify no-network operation and path containment, and document the implemented public interface.

**Acceptance criteria:**

- [ ] Every success criterion in `SPEC-data-core.md` has direct test evidence.
- [ ] `src/synthguard/data_core` reaches at least 90% statement coverage.
- [ ] The complete module works offline and never writes outside its validated root.

**Verification:**

- [ ] `uv run pytest --cov=synthguard.data_core --cov-report=term-missing --cov-fail-under=90`
- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run mypy src/synthguard`

**Dependencies:** Task 7

**Files likely touched:**

- `tests/data_core/test_end_to_end.py`
- `README.md`
- `SPEC-data-core.md`
- `tasks/todo.md`

**Estimated scope:** Medium

## Checkpoint: `data-core` complete

- [ ] All tasks and checkpoints are complete with verification evidence.
- [ ] All module tests and quality gates pass offline.
- [ ] Source fixtures remain unchanged and contain no sensitive data.
- [ ] The next module, `evaluation-core`, may begin specification review.
