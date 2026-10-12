# Spec: SynthGuard `quality-gate`

## Status

Approved for implementation. This specification defines the third module in `CAPABILITY_MAP.md` and consumes only the public `evaluation-core` contract.

## Objective

Convert independent evaluation evidence into transparent, deterministic candidate decisions. Users configure explicit thresholds; the gate evaluates every criterion, explains failures, ranks candidates, and names a winner only when at least one candidate passes.

## In Scope

- Immutable threshold policy with safe defaults.
- Statistical, exact-copy, near-copy, DCR, and optional utility criteria.
- Per-criterion observed value, comparator, threshold, status, and plain-language explanation.
- Deterministic composite score and candidate ranking.
- Passed candidates rank before failed candidates; stable fingerprint tie-breaking.
- Typed JSON-serializable results and stable errors.

## Out of Scope

- Recalculating evaluation metrics.
- Claiming anonymity, compliance, or universal model fitness.
- Automatic threshold tuning or hidden policy changes.
- UI, MCP, persistence, authentication, or hosted services.

## Public Interface

```python
from synthguard.quality_gate import (
    CandidateEvidence,
    GatePolicy,
    GateRequest,
    apply_quality_gate,
)

result = apply_quality_gate(
    GateRequest(
        candidates=(CandidateEvidence(candidate_id="gaussian", evaluation=evaluation),),
        policy=GatePolicy(),
    )
)
```

Default policy:

- Minimum overall statistical score: `0.70`.
- Maximum exact-match rate: `0.00`.
- Maximum sampled near-duplicate rate: `0.05`.
- Minimum DCR baseline protection: `0.50`.
- Minimum utility retention: `0.80` when utility is present.
- Utility is optional unless `require_utility=True`.

## Ranking Method

The composite score is evidence for comparison, not a privacy guarantee:

- Statistical fidelity: 40%.
- Privacy evidence: 35%, averaging exact-copy safety, near-copy safety, and DCR protection.
- ML utility: 25% when available; otherwise remaining weights are normalized.

Scores are clamped to `[0, 1]`. A utility retention above `1` contributes `1`. Ranking order is pass before fail, composite score descending, then candidate id ascending.

## Errors

- Pydantic `ValidationError` for malformed policies and requests.
- `QualityGateError("DUPLICATE_CANDIDATE_ID", ...)` for duplicate ids.
- `QualityGateError("INCONSISTENT_UTILITY", ...)` when a required utility result is absent.

Failures never include raw source rows or cell values.

## Success Criteria

- Threshold boundaries use inclusive comparisons and are directly tested.
- Every decision is explainable by ordered criterion records.
- Rankings remain identical across repeated runs and input permutations.
- Missing optional utility is handled explicitly; required utility fails clearly.
- The module is framework-independent, offline, typed, and at least 95% covered.
