"""Pure threshold decisions and ranking for evaluated candidates."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    CandidateDecision,
    CandidateEvidence,
    CriterionResult,
    CriterionStatus,
    GatePolicy,
    GateRequest,
    GateResult,
    GateStatus,
    QualityGateError,
)

_STATISTICAL_WEIGHT = 0.40
_PRIVACY_WEIGHT = 0.35
_UTILITY_WEIGHT = 0.25


@dataclass(frozen=True, slots=True)
class _UnrankedDecision:
    candidate_id: str
    status: GateStatus
    composite_score: float
    criteria: tuple[CriterionResult, ...]
    failed_criteria: tuple[str, ...]


def apply_quality_gate(request: GateRequest) -> GateResult:
    """Apply one explicit policy and return stable ranked decisions."""

    _validate_unique_ids(request.candidates)
    decisions = [_decide(candidate, request.policy) for candidate in request.candidates]
    decisions.sort(
        key=lambda item: (
            0 if item.status is GateStatus.PASS else 1,
            -item.composite_score,
            item.candidate_id,
        )
    )
    ranked = tuple(
        CandidateDecision(
            candidate_id=decision.candidate_id,
            rank=index,
            status=decision.status,
            composite_score=decision.composite_score,
            criteria=decision.criteria,
            failed_criteria=decision.failed_criteria,
        )
        for index, decision in enumerate(decisions, start=1)
    )
    winner = next(
        (decision.candidate_id for decision in ranked if decision.status is GateStatus.PASS),
        None,
    )
    return GateResult(policy=request.policy, candidates=ranked, winner_candidate_id=winner)


def _validate_unique_ids(candidates: tuple[CandidateEvidence, ...]) -> None:
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.candidate_id in seen:
            raise QualityGateError(
                "DUPLICATE_CANDIDATE_ID",
                "Candidate identifiers must be unique.",
                {"candidate_id": candidate.candidate_id},
            )
        seen.add(candidate.candidate_id)


def _decide(candidate: CandidateEvidence, policy: GatePolicy) -> _UnrankedDecision:
    evidence = candidate.evaluation
    near_duplicate_rate = (
        evidence.privacy.near_duplicate_count / evidence.privacy.sampled_synthetic_rows
    )
    criteria = (
        _minimum_criterion(
            "statistical_quality",
            evidence.statistical.overall_score,
            policy.min_statistical_score,
            "Overall statistical fidelity",
        ),
        _maximum_criterion(
            "exact_match_rate",
            evidence.privacy.exact_match_rate,
            policy.max_exact_match_rate,
            "Exact copied-row rate",
        ),
        _maximum_criterion(
            "near_duplicate_rate",
            near_duplicate_rate,
            policy.max_near_duplicate_rate,
            "Sampled near-duplicate rate",
        ),
        _minimum_criterion(
            "dcr_baseline_protection",
            evidence.privacy.dcr_baseline_protection_score,
            policy.min_dcr_score,
            "DCR baseline protection",
        ),
        _utility_criterion(candidate, policy),
    )
    failed = tuple(item.name for item in criteria if item.status is CriterionStatus.FAIL)
    status = GateStatus.FAIL if failed else GateStatus.PASS
    return _UnrankedDecision(
        candidate_id=candidate.candidate_id,
        status=status,
        composite_score=_composite_score(candidate),
        criteria=criteria,
        failed_criteria=failed,
    )


def _minimum_criterion(
    name: str,
    observed: float,
    threshold: float,
    label: str,
) -> CriterionResult:
    passed = observed >= threshold
    return CriterionResult(
        name=name,
        status=CriterionStatus.PASS if passed else CriterionStatus.FAIL,
        observed_value=observed,
        threshold=threshold,
        comparator=">=",
        explanation=f"{label} must be at least the configured threshold.",
    )


def _maximum_criterion(
    name: str,
    observed: float,
    threshold: float,
    label: str,
) -> CriterionResult:
    passed = observed <= threshold
    return CriterionResult(
        name=name,
        status=CriterionStatus.PASS if passed else CriterionStatus.FAIL,
        observed_value=observed,
        threshold=threshold,
        comparator="<=",
        explanation=f"{label} must not exceed the configured threshold.",
    )


def _utility_criterion(
    candidate: CandidateEvidence,
    policy: GatePolicy,
) -> CriterionResult:
    utility = candidate.evaluation.utility
    if utility is None:
        status = CriterionStatus.FAIL if policy.require_utility else CriterionStatus.SKIPPED
        wording = (
            "required but unavailable" if policy.require_utility else "optional and not requested"
        )
        return CriterionResult(
            name="utility_retention",
            status=status,
            observed_value=None,
            threshold=policy.min_utility_retention,
            comparator=">=",
            explanation=f"Classification utility is {wording}.",
        )
    if utility.utility_retention is None:
        return CriterionResult(
            name="utility_retention",
            status=CriterionStatus.FAIL,
            observed_value=None,
            threshold=policy.min_utility_retention,
            comparator=">=",
            explanation="Utility retention is undefined because the real baseline scored zero.",
        )
    return _minimum_criterion(
        "utility_retention",
        utility.utility_retention,
        policy.min_utility_retention,
        "Classification utility retention",
    )


def _composite_score(candidate: CandidateEvidence) -> float:
    evidence = candidate.evaluation
    near_rate = evidence.privacy.near_duplicate_count / evidence.privacy.sampled_synthetic_rows
    privacy_score = (
        (1.0 - evidence.privacy.exact_match_rate)
        + (1.0 - min(near_rate, 1.0))
        + evidence.privacy.dcr_baseline_protection_score
    ) / 3.0
    weighted = (
        evidence.statistical.overall_score * _STATISTICAL_WEIGHT + privacy_score * _PRIVACY_WEIGHT
    )
    total_weight = _STATISTICAL_WEIGHT + _PRIVACY_WEIGHT
    utility = evidence.utility
    if utility is not None and utility.utility_retention is not None:
        weighted += min(utility.utility_retention, 1.0) * _UTILITY_WEIGHT
        total_weight += _UTILITY_WEIGHT
    return min(max(weighted / total_weight, 0.0), 1.0)
