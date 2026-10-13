"""Streamlit presentation components for profile and evidence states."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from synthguard.data_core import DatasetProfile
from synthguard.workflow import WorkflowRun


def render_profile(profile: DatasetProfile) -> None:
    st.subheader("1 · Review the inferred schema")
    first, second, third = st.columns(3)
    first.metric("Rows", f"{profile.row_count:,}")
    second.metric("Columns", profile.column_count)
    third.metric(
        "Review flags",
        sum(column.is_sensitive_candidate for column in profile.columns),
    )
    frame = pd.DataFrame(
        [
            {
                "Column": column.name,
                "Detected type": column.semantic_type.value,
                "Null rate": column.null_rate,
                "Unique rate": column.unique_rate,
                "Review": column.sensitivity_reason or "—",
            }
            for column in profile.columns
        ]
    )
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            "Null rate": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0),
            "Unique rate": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0),
        },
    )
    if profile.warnings:
        with st.expander(f"{len(profile.warnings)} profiling note(s)"):
            for warning in profile.warnings:
                st.write(f"**{warning.code}** — {warning.message}")


def render_results(run: WorkflowRun) -> None:
    st.subheader("3 · Compare the evidence")
    if run.gate.winner_candidate_id:
        st.success(
            f"Passing candidate: {run.gate.winner_candidate_id.replace('_', ' ').title()}",
            icon=":material/check_circle:",
        )
    else:
        st.warning(
            "No candidate passed every configured threshold.",
            icon=":material/warning:",
        )

    rows = []
    for decision in run.gate.candidates:
        evaluation = run.evaluations[decision.candidate_id]
        rows.append(
            {
                "Rank": decision.rank,
                "Candidate": decision.candidate_id.replace("_", " ").title(),
                "Decision": decision.status.value.upper(),
                "Composite": decision.composite_score,
                "Statistical": evaluation.statistical.overall_score,
                "Exact copies": evaluation.privacy.exact_match_rate,
                "Near copies": (
                    evaluation.privacy.near_duplicate_count
                    / evaluation.privacy.sampled_synthetic_rows
                ),
                "DCR": evaluation.privacy.dcr_baseline_protection_score,
                "Utility": (
                    evaluation.utility.utility_retention if evaluation.utility is not None else None
                ),
            }
        )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            name: st.column_config.NumberColumn(format="%.3f")
            for name in (
                "Composite",
                "Statistical",
                "Exact copies",
                "Near copies",
                "DCR",
                "Utility",
            )
        },
    )

    tabs = st.tabs([item.candidate_id.replace("_", " ").title() for item in run.gate.candidates])
    for tab, decision in zip(tabs, run.gate.candidates, strict=True):
        with tab:
            _render_candidate_details(run, decision.candidate_id)

    st.subheader("4 · Export the evidence")
    left, right = st.columns(2)
    winner = run.gate.winner_candidate_id
    if winner:
        csv_path = run.generations[winner].artifacts.synthetic_csv
        left.download_button(
            "Download passing synthetic CSV",
            data=csv_path.read_bytes(),
            file_name=f"synthguard-{winner}.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        left.caption("A CSV download appears when a candidate passes the policy.")
    right.download_button(
        "Download Markdown evidence report",
        data=run.report_markdown,
        file_name="synthguard-evidence-report.md",
        mime="text/markdown",
        width="stretch",
    )


def _render_candidate_details(run: WorkflowRun, candidate_id: str) -> None:
    decision = next(item for item in run.gate.candidates if item.candidate_id == candidate_id)
    evaluation = run.evaluations[candidate_id]
    st.markdown("#### Gate criteria")
    criteria = pd.DataFrame(
        [
            {
                "Status": criterion.status.value.upper(),
                "Criterion": criterion.name.replace("_", " ").title(),
                "Observed": criterion.observed_value,
                "Rule": f"{criterion.comparator} {criterion.threshold:.3f}",
                "Explanation": criterion.explanation,
            }
            for criterion in decision.criteria
        ]
    )
    st.dataframe(criteria, hide_index=True, width="stretch")
    st.markdown("#### Weakest statistical areas")
    if evaluation.statistical.weakest_areas:
        st.dataframe(
            pd.DataFrame([area.model_dump() for area in evaluation.statistical.weakest_areas[:5]]),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No finite weak-area details were returned for this candidate.")
    st.caption(
        "These are comparative risk indicators and baseline measurements, not a privacy guarantee."
    )
