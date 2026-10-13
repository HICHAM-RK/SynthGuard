"""Portable Markdown evidence reports for Studio and MCP consumers."""

from __future__ import annotations

from collections.abc import Mapping

from synthguard.evaluation_core import EvaluationResult
from synthguard.quality_gate import GateResult


def build_markdown_report(
    gate: GateResult,
    evaluations: Mapping[str, EvaluationResult],
) -> str:
    """Render a deterministic, value-safe evidence report."""

    lines = [
        "# SynthGuard evidence report",
        "",
        "> Risk evidence and threshold decisions—not an anonymity or compliance guarantee.",
        "",
        "## Decision summary",
        "",
        f"- Winner: `{gate.winner_candidate_id or 'No passing candidate'}`",
        f"- Candidates evaluated: {len(gate.candidates)}",
        "",
        "## Gate policy",
        "",
        f"- Statistical score ≥ {gate.policy.min_statistical_score:.3f}",
        f"- Exact-match rate ≤ {gate.policy.max_exact_match_rate:.3f}",
        f"- Near-duplicate rate ≤ {gate.policy.max_near_duplicate_rate:.3f}",
        f"- DCR baseline protection ≥ {gate.policy.min_dcr_score:.3f}",
        f"- Utility retention ≥ {gate.policy.min_utility_retention:.3f}",
        f"- Utility required: {'yes' if gate.policy.require_utility else 'no'}",
        "",
        "## Ranked candidates",
        "",
    ]
    for decision in gate.candidates:
        evaluation = evaluations[decision.candidate_id]
        near_duplicate_rate = (
            evaluation.privacy.near_duplicate_count / evaluation.privacy.sampled_synthetic_rows
        )
        lines.extend(
            [
                f"### {decision.rank}. {decision.candidate_id} — {decision.status.value.upper()}",
                "",
                f"- Composite score: {decision.composite_score:.3f}",
                f"- Statistical quality: {evaluation.statistical.overall_score:.3f}",
                f"- Exact-match rate: {evaluation.privacy.exact_match_rate:.3f}",
                (f"- Near-duplicate rate: {near_duplicate_rate:.3f}"),
                (
                    "- DCR baseline protection: "
                    f"{evaluation.privacy.dcr_baseline_protection_score:.3f}"
                ),
            ]
        )
        if evaluation.utility is not None:
            retention = evaluation.utility.utility_retention
            lines.append(
                "- Utility retention: "
                + (f"{retention:.3f}" if retention is not None else "undefined")
            )
        lines.extend(["", "Criteria:", ""])
        for criterion in decision.criteria:
            observed = (
                f"{criterion.observed_value:.3f}"
                if criterion.observed_value is not None
                else "not available"
            )
            lines.append(
                f"- **{criterion.status.value.upper()}** `{criterion.name}`: "
                f"{observed} {criterion.comparator} {criterion.threshold:.3f}. "
                f"{criterion.explanation}"
            )
        lines.append("")
    lines.extend(
        [
            "## Interpretation limits",
            "",
            "- Exact copies, proximity, and DCR are privacy-risk indicators, "
            "not formal privacy proofs.",
            "- Utility uses one fixed classification baseline and may not represent "
            "every workload.",
            "- A pass applies only to the policy and artifacts recorded in this report.",
            "",
        ]
    )
    return "\n".join(lines)
