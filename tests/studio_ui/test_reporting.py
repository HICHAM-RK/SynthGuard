from __future__ import annotations

from synthguard.evaluation_core import (
    EvaluationResult,
    PrivacyEvidenceResult,
    StatisticalQualityResult,
)
from synthguard.quality_gate import CandidateEvidence, GateRequest, apply_quality_gate
from synthguard.studio_ui import build_markdown_report


def test_report_contains_decisions_evidence_and_limits() -> None:
    evaluation = _evaluation()
    gate = apply_quality_gate(
        GateRequest(candidates=(CandidateEvidence(candidate_id="gaussian", evaluation=evaluation),))
    )

    report = build_markdown_report(gate, {"gaussian": evaluation})

    assert "# SynthGuard evidence report" in report
    assert "Winner: `gaussian`" in report
    assert "Statistical quality: 0.900" in report
    assert "Exact-match rate: 0.000" in report
    assert "Criteria:" in report
    assert "not an anonymity or compliance guarantee" in report
    assert "A pass applies only to the policy" in report


def _evaluation() -> EvaluationResult:
    return EvaluationResult(
        real_fingerprint="a" * 64,
        synthetic_fingerprint="b" * 64,
        real_row_count=100,
        synthetic_row_count=100,
        column_count=2,
        statistical=StatisticalQualityResult(
            overall_score=0.9,
            column_shapes_score=0.9,
            column_pair_trends_score=0.9,
            column_scores=(),
            weakest_areas=(),
            metric_provenance="test",
        ),
        privacy=PrivacyEvidenceResult(
            exact_match_count=0,
            exact_match_rate=0.0,
            near_duplicate_count=0,
            nearest_distance_min=0.2,
            nearest_distance_fifth_percentile=0.3,
            nearest_distance_median=0.7,
            distance_threshold=0.05,
            dcr_baseline_protection_score=0.8,
            sampled_real_rows=100,
            sampled_synthetic_rows=100,
            sampling_seed=42,
            metric_provenance="test",
        ),
        evaluation_duration_seconds=0.1,
    )
