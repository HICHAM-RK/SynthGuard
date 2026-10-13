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

- [x] Repeated profiling of the same fixture produces the same ordered contract.
- [x] Nulls, booleans, dates, categories, numerical fields, and high-cardinality identifiers are represented correctly in fixtures.
- [x] Sensitive-column flags are explicitly advisory and include a reason.

**Verification:**

- [x] `uv run pytest tests/data_core/test_profiling.py -q` — 5 passed.
- [x] A complete profile serializes through Pydantic JSON output.

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

- [x] Every input column appears exactly once in generated metadata.
- [x] Valid overrides update known columns without mutating the original profile.
- [x] Unknown columns and unsupported overrides fail with `INVALID_OVERRIDE`.

**Verification:**

- [x] `uv run pytest tests/data_core/test_metadata.py -q` — 5 passed.
- [x] Generated metadata validates through the locked SDV API.

**Dependencies:** Task 3

**Files likely touched:**

- `src/synthguard/data_core/metadata.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_metadata.py`

**Estimated scope:** Medium

## Checkpoint: Reviewable metadata

- [x] Tasks 3-4 acceptance criteria are checked with evidence.
- [x] A caller can profile, review, and override a fixture before training.
- [x] All quality commands pass.

## Task 5: Generate a Gaussian-copula candidate

**Description:** Define the internal synthesizer protocol and implement the fast Gaussian-copula path through the public `generate_candidate` contract.

**Acceptance criteria:**

- [x] The Gaussian adapter trains from reviewed metadata and produces exactly the requested rows.
- [x] Unsupported methods and training failures preserve stable public errors.
- [x] Method-specific objects do not leak through the public result contract.

**Verification:**

- [x] `uv run pytest tests/data_core/test_synthesis.py -k gaussian -q` — 3 passed.
- [x] Generated a 50-row in-memory candidate from the committed fixture.

**Dependencies:** Task 4

**Files likely touched:**

- `src/synthguard/data_core/synthesis.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_synthesis.py`

**Estimated scope:** Medium

## Task 6: Add the CTGAN candidate

**Description:** Add CTGAN behind the same adapter boundary, with configurable test epochs and explicit reproducibility warnings where necessary.

**Acceptance criteria:**

- [x] CTGAN produces exactly the requested row count on CPU.
- [x] Test configuration limits training time without changing production defaults silently.
- [x] The generation contract remains unchanged from Task 5.

**Verification:**

- [x] `uv run pytest tests/data_core/test_synthesis.py -k ctgan -q` — 2 passed.
- [x] One tiny CPU generation records its duration in the result.

**Dependencies:** Task 5

**Files likely touched:**

- `src/synthguard/data_core/synthesis.py`
- `tests/data_core/test_synthesis.py`

**Estimated scope:** Small

## Checkpoint: Two generation methods

- [x] Tasks 5-6 acceptance criteria are checked with evidence.
- [x] Both adapters satisfy the same contract and run offline.
- [x] All quality commands pass.

## Task 7: Persist atomic run artifacts

**Description:** Save each successful candidate as an immutable run containing synthetic CSV, reviewed metadata, and a complete reproducibility manifest with checksums.

**Acceptance criteria:**

- [x] Successful runs finalize all three required artifacts beneath the validated output root.
- [x] Existing completed runs are never overwritten.
- [x] Simulated write failures leave no directory that appears complete.

**Verification:**

- [x] `uv run pytest tests/data_core/test_artifacts.py -q` — 5 passed.
- [x] Automated manifest checks verify synthetic CSV and metadata checksums.

**Dependencies:** Tasks 5-6

**Files likely touched:**

- `src/synthguard/data_core/artifacts.py`
- `src/synthguard/data_core/contracts.py`
- `tests/data_core/test_artifacts.py`

**Estimated scope:** Medium

## Task 8: Harden and verify the module

**Description:** Add end-to-end regression tests, close coverage gaps, verify no-network operation and path containment, and document the implemented public interface.

**Acceptance criteria:**

- [x] Every success criterion in `SPEC-data-core.md` has direct test evidence.
- [x] `src/synthguard/data_core` reaches at least 90% statement coverage.
- [x] The complete module works offline and never writes outside its validated root.

**Verification:**

- [x] `uv run pytest --cov=synthguard.data_core --cov-report=term-missing --cov-fail-under=90` — 41 passed, 93% coverage.
- [x] `uv run ruff check . && uv run ruff format --check .` — passed.
- [x] `uv run mypy src/synthguard` — passed with no issues.

**Dependencies:** Task 7

**Files likely touched:**

- `tests/data_core/test_end_to_end.py`
- `README.md`
- `SPEC-data-core.md`
- `tasks/todo.md`

**Estimated scope:** Medium

## Checkpoint: `data-core` complete

- [x] All tasks and checkpoints are complete with verification evidence.
- [x] All module tests and quality gates pass offline.
- [x] Source fixtures remain unchanged and contain no sensitive data.
- [x] The next module, `evaluation-core`, may begin specification review.

---

# SynthGuard `evaluation-core` Task List

## Evaluation Task 1: Establish evaluator contracts

**Description:** Add the evaluation package, immutable request/result models, metric evidence contracts, structured warnings, and `EvaluationCoreError`.

**Acceptance criteria:**

- [x] Requests reject empty paths and out-of-range privacy sampling limits.
- [x] Result score fields reject values outside `[0, 1]` while distances remain non-negative.
- [x] Only intended public names are exported from `synthguard.evaluation_core`.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_contracts.py -q`
- [x] `uv run ruff check . && uv run ruff format --check .`
- [x] `uv run mypy src/synthguard`

**Dependencies:** Implemented `data-core`

**Files likely touched:**

- `src/synthguard/evaluation_core/__init__.py`
- `src/synthguard/evaluation_core/contracts.py`
- `tests/evaluation_core/test_contracts.py`

**Estimated scope:** Medium

## Evaluation Task 2: Validate artifact pairs

**Description:** Load bounded real/synthetic CSVs and current metadata, verify exact ordered schema equality, calculate fingerprints, and validate optional targets.

**Acceptance criteria:**

- [x] Valid artifacts produce one immutable internal pair without modifying inputs.
- [x] Missing, empty, malformed, mismatched, and invalid-metadata artifacts return stable errors.
- [x] Unknown or unusable classification targets fail before metric work starts.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_validation.py -q`
- [x] Automated checks confirm all source checksums remain unchanged.

**Dependencies:** Evaluation Task 1

**Files likely touched:**

- `src/synthguard/evaluation_core/validation.py`
- `src/synthguard/evaluation_core/contracts.py`
- `tests/evaluation_core/test_validation.py`
- `tests/evaluation_core/fixtures/real.csv`

**Estimated scope:** Medium

## Checkpoint: Trusted evaluation inputs

- [x] Evaluation Tasks 1-2 have evidence for every acceptance criterion.
- [x] Tests, Ruff, formatting, and mypy pass.
- [x] Errors contain no fixture values or unrestricted paths.

## Evaluation Task 3: Measure statistical fidelity

**Description:** Adapt the current SDMetrics quality report into overall, property, per-column, and deterministic weakest-area evidence.

**Acceptance criteria:**

- [x] Scores are typed, bounded, and derived without deprecated imports or verbose output.
- [x] Controlled realistic data scores above deliberately collapsed data.
- [x] SDMetrics failures return `STATISTICAL_EVALUATION_FAILED` without internal details.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_statistical.py -q -W error`

**Dependencies:** Evaluation Task 2

**Files likely touched:**

- `src/synthguard/evaluation_core/statistical.py`
- `src/synthguard/evaluation_core/contracts.py`
- `tests/evaluation_core/test_statistical.py`

**Estimated scope:** Medium

## Evaluation Task 4: Measure privacy-risk evidence

**Description:** Calculate null-safe exact matches, deterministic mixed-type nearest-neighbor aggregates, near-duplicate counts, and SDMetrics DCR baseline protection.

**Acceptance criteria:**

- [x] Exact copied rows, including normalized nulls, are counted correctly.
- [x] Identifier columns are excluded from bounded distance calculations and sampling is reproducible.
- [x] DCR and distance failures return `PRIVACY_EVALUATION_FAILED` without leaking rows.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_privacy.py -q -W error`

**Dependencies:** Evaluation Task 2

**Files likely touched:**

- `src/synthguard/evaluation_core/privacy.py`
- `src/synthguard/evaluation_core/contracts.py`
- `tests/evaluation_core/test_privacy.py`

**Estimated scope:** Medium

## Checkpoint: Statistical and privacy evidence

- [x] Evaluation Tasks 3-4 pass independently and together.
- [x] Metrics expose methodology and bounded sampling details.
- [x] No pass/fail decision exists in evaluation-core.

## Evaluation Task 5: Measure classification utility

**Description:** Compare fixed real-trained and synthetic-trained logistic-regression pipelines on the same held-out real test set using weighted F1.

**Acceptance criteria:**

- [x] Real data is split before preprocessing and the test labels are untouched during both fits.
- [x] Deterministic results expose scores, utility retention, class count, and split sizes.
- [x] Invalid targets and insufficient classes fail with stable value-safe errors.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_utility.py -q`

**Dependencies:** Evaluation Task 2

**Files likely touched:**

- `src/synthguard/evaluation_core/utility.py`
- `src/synthguard/evaluation_core/contracts.py`
- `tests/evaluation_core/test_utility.py`

**Estimated scope:** Medium

## Evaluation Task 6: Orchestrate complete evaluations

**Description:** Compose validation and metric adapters into the public `evaluate_candidate` service with deterministic timing-independent output.

**Acceptance criteria:**

- [x] A valid request returns JSON-serializable statistical and privacy evidence.
- [x] Utility is present only when a target is requested.
- [x] Fingerprints, row counts, warnings, and elapsed time are returned without raw values.

**Verification:**

- [x] `uv run pytest tests/evaluation_core/test_service.py -q`

**Dependencies:** Evaluation Tasks 3-5

**Files likely touched:**

- `src/synthguard/evaluation_core/service.py`
- `src/synthguard/evaluation_core/__init__.py`
- `tests/evaluation_core/test_service.py`

**Estimated scope:** Medium

## Evaluation Task 7: Harden the evaluator end to end

**Description:** Evaluate real data-core artifacts, deny network access, close coverage gaps, and document the public evaluation workflow and limitations.

**Acceptance criteria:**

- [x] Gaussian and constrained CTGAN artifacts can be evaluated end to end.
- [x] Evaluation-core reaches at least 90% statement coverage with all project tests passing offline.
- [x] Documentation distinguishes risk evidence from privacy guarantees and evaluation from quality-gate decisions.

**Verification:**

- [x] `uv run pytest --cov=synthguard.evaluation_core --cov-report=term-missing --cov-fail-under=90`
- [x] `uv run ruff check . && uv run ruff format --check .`
- [x] `uv run mypy src/synthguard`

**Dependencies:** Evaluation Task 6

**Files likely touched:**

- `tests/evaluation_core/test_end_to_end.py`
- `README.md`
- `SPEC-evaluation-core.md`
- `tasks/todo.md`

**Estimated scope:** Medium

## Checkpoint: `evaluation-core` complete

- [x] Every specification success criterion has direct verification evidence.
- [x] Full project tests and static quality gates pass offline.
- [x] The next module, `quality-gate`, may begin specification review.

---

# SynthGuard `quality-gate` Task List

## Gate Task 1: Contracts

- [x] Immutable policy and result contracts validate bounds and non-empty candidates.
- [x] Package exports only the intended public surface.
- [x] Stable `QualityGateError` payloads are value-safe.

## Gate Task 2: Decisions

- [x] All five criteria use documented inclusive comparisons.
- [x] Optional utility is skipped explicitly; required utility fails explicitly.
- [x] Every criterion exposes observed value, threshold, comparator, and explanation.

## Gate Task 3: Ranking

- [x] Composite score follows documented fixed weights.
- [x] Passed candidates rank before failed candidates.
- [x] Repeated runs and candidate permutations produce identical order and winner.

## Gate Task 4: Hardening

- [x] JSON serialization, duplicate ids, and no-winner behavior are tested.
- [x] Quality-gate reaches at least 95% statement coverage.
- [x] Full tests and static quality gates pass offline.
- [x] README documents configurable decisions and their limitations.

---

# SynthGuard `studio-ui` Task List

- [x] Upload and profile one bounded CSV without rendering source rows.
- [x] Configure methods, rows, seed, target, and all gate thresholds.
- [x] Generate, evaluate, and rank candidates through public domain APIs only.
- [x] Render comparison, criterion, weak-area, privacy, and utility evidence.
- [x] Download the winning CSV and a Markdown evidence report.
- [x] Cover report generation and initial app rendering with automated tests.
- [x] Verify desktop/mobile browser states, accessibility structure, and clean console.
- [x] Full tests, Ruff, formatting, and mypy pass.

---

# SynthGuard `mcp-server` Task List

- [x] Path allowlist accepts contained paths and rejects outside, traversal, and symlink escapes.
- [x] Five typed tools expose profile, generation, evaluation, gating, and full workflow.
- [x] Tool adapters import public domain APIs and never duplicate calculations.
- [x] Expected failures surface stable safe MCP tool errors without partial success.
- [x] FastMCP discovery returns exactly the documented tool names.
- [x] README includes a ready-to-use stdio configuration and allowlist instructions.
- [x] MCP tests and all repository quality gates pass offline.
