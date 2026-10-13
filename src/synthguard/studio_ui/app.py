"""Local Streamlit application for the SynthGuard workflow."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import streamlit as st

from synthguard.data_core import (
    DataCoreError,
    DatasetProfile,
    GenerationMethod,
    ProfileRequest,
    SemanticType,
    profile_csv,
)
from synthguard.evaluation_core import EvaluationCoreError
from synthguard.quality_gate import GatePolicy, QualityGateError
from synthguard.studio_ui.views import render_profile, render_results
from synthguard.workflow import WorkflowRun, run_workflow

_MAX_UPLOAD_BYTES = 25_000_000


def main() -> None:
    st.set_page_config(page_title="SynthGuard", page_icon="SG", layout="wide")
    _inject_styles()
    st.markdown('<p class="eyebrow">LOCAL SYNTHETIC DATA AUDIT</p>', unsafe_allow_html=True)
    st.title("Synthetic data, with receipts.")
    st.write(
        "Generate competing tabular candidates, measure what they preserve, and inspect what they "
        "might copy—all without sending your dataset anywhere."
    )
    st.caption("Local-only · CPU-compatible · No API key · Evidence is not a privacy guarantee")

    upload_column, demo_column = st.columns([3, 1])
    with upload_column:
        uploaded = st.file_uploader(
            "Upload one CSV",
            type=["csv"],
            help="Maximum 25 MB. Source rows are processed locally and never displayed.",
        )
    with demo_column:
        st.write("")
        if st.button("Try the demo dataset", width="stretch"):
            st.session_state["demo_payload"] = _demo_csv()
            st.session_state.pop("studio_run", None)
    payload: object
    if uploaded is not None:
        payload = uploaded.getvalue()
        st.session_state.pop("demo_payload", None)
    else:
        payload = st.session_state.get("demo_payload")
    if not isinstance(payload, bytes):
        st.info("Start with a CSV to reveal schema review, generation controls, and evidence.")
        _render_empty_state()
        return
    if len(payload) > _MAX_UPLOAD_BYTES:
        st.error("This CSV is larger than the 25 MB local limit.")
        return

    source_path = _materialize_upload(payload)
    try:
        profile = profile_csv(ProfileRequest(source_path=source_path))
    except DataCoreError as error:
        st.error(f"{error.code}: {error.message}")
        return
    render_profile(profile)
    config = _render_configuration(profile)
    if st.button(
        "Generate and evaluate candidates",
        type="primary",
        width="stretch",
        disabled=not config[0],
    ):
        try:
            with st.spinner("Training candidates and assembling evidence…"):
                st.session_state["studio_run"] = run_workflow(
                    source_csv=source_path,
                    output_directory=_session_root() / "runs",
                    methods=config[0],
                    row_count=config[1],
                    random_seed=config[2],
                    classification_target=config[3],
                    policy=config[4],
                )
        except (DataCoreError, EvaluationCoreError, QualityGateError) as error:
            st.error(f"{error.code}: {error.message}")
    run = st.session_state.get("studio_run")
    if isinstance(run, WorkflowRun):
        render_results(run)


def _render_configuration(
    profile: DatasetProfile,
) -> tuple[tuple[GenerationMethod, ...], int, int, str | None, GatePolicy]:
    st.subheader("2 · Configure the experiment")
    with st.sidebar:
        st.header("Experiment controls")
        selected = st.multiselect(
            "Candidate methods",
            options=list(GenerationMethod),
            default=[GenerationMethod.GAUSSIAN_COPULA],
            format_func=lambda method: method.value.replace("_", " ").title(),
        )
        row_count = int(st.number_input("Rows per candidate", 10, 100_000, 1_000, step=100))
        seed = int(st.number_input("Random seed", value=42, step=1))
        targets = [
            column.name
            for column in profile.columns
            if column.semantic_type in {SemanticType.CATEGORICAL, SemanticType.BOOLEAN}
        ]
        target_label = st.selectbox("Classification utility target (optional)", ["None", *targets])
        st.divider()
        st.subheader("Pass thresholds")
        statistical = st.slider("Minimum statistical quality", 0.0, 1.0, 0.70, 0.01)
        exact = st.slider("Maximum exact-copy rate", 0.0, 1.0, 0.00, 0.01)
        near = st.slider("Maximum near-copy rate", 0.0, 1.0, 0.05, 0.01)
        dcr = st.slider("Minimum DCR protection", 0.0, 1.0, 0.50, 0.01)
        utility = st.slider("Minimum utility retention", 0.0, 1.0, 0.80, 0.01)
        require_utility = st.checkbox("Require utility evidence", disabled=target_label == "None")
    policy = GatePolicy(
        min_statistical_score=statistical,
        max_exact_match_rate=exact,
        max_near_duplicate_rate=near,
        min_dcr_score=dcr,
        min_utility_retention=utility,
        require_utility=require_utility,
    )
    return (
        tuple(selected),
        row_count,
        seed,
        None if target_label == "None" else target_label,
        policy,
    )


def _session_root() -> Path:
    if "session_root" not in st.session_state:
        st.session_state["session_root"] = tempfile.mkdtemp(prefix="synthguard-")
    return Path(st.session_state["session_root"])


def _materialize_upload(payload: bytes) -> Path:
    fingerprint = hashlib.sha256(payload).hexdigest()
    source_path = _session_root() / f"source-{fingerprint}.csv"
    if not source_path.exists():
        source_path.write_bytes(payload)
        st.session_state.pop("studio_run", None)
    return source_path


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
          <strong>What you will get</strong>
          <span>01 — Reviewable type inference</span>
          <span>02 — Gaussian Copula / CTGAN candidates</span>
          <span>03 — Fidelity, copy-risk, DCR, and optional ML utility</span>
          <span>04 — Explainable gate decision, CSV, and evidence report</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _demo_csv() -> bytes:
    rows = ["customer_id,age,income,is_member,segment,churned"]
    for index in range(120):
        age = 18 + index % 60
        income = 32_000 + (index * 1_375) % 88_000
        is_member = index % 3 != 0
        segment = "premium" if index % 4 == 0 else "standard"
        churned = age < 25 or (not is_member and segment == "standard")
        rows.append(
            f"DEMO-{index + 1:03d},{age},{income},{str(is_member).lower()},"
            f"{segment},{str(churned).lower()}"
        )
    return ("\n".join(rows) + "\n").encode()


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --sg-ink: #132238; --sg-teal: #087e78; --sg-paper: #f5f3ec; }
        .stApp { background: var(--sg-paper); color: var(--sg-ink); }
        .block-container { max-width: 1180px; padding-top: 3rem; }
        .eyebrow { color: var(--sg-teal); font-weight: 750; letter-spacing: .16em;
          font-size: .75rem; }
        h1, h2, h3 { color: var(--sg-ink); letter-spacing: -.025em; }
        h1 { max-width: 760px; }
        .empty-state { border-top: 2px solid var(--sg-ink); margin-top: 2rem; padding-top: 1rem;
          display: grid; gap: .75rem; }
        .empty-state span { border-bottom: 1px solid #c9c7bf; padding: .5rem 0; }
        [data-testid="stSidebar"] { background: #e9e7df; border-right: 1px solid #cbc8be; }
        [data-testid="stMetric"] { border-top: 2px solid var(--sg-teal); padding-top: .75rem; }
        .stButton button[kind="primary"] { background: var(--sg-ink); border-color: var(--sg-ink); }
        .stButton button[kind="primary"]:focus { outline: 3px solid #d39b2a; outline-offset: 2px; }
        @media (max-width: 640px) { .block-container { padding: 1.5rem 1rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
