from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[2] / "src" / "synthguard" / "studio_ui" / "app.py"


def test_initial_app_state_is_actionable_and_error_free() -> None:
    app = AppTest.from_file(str(APP)).run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "Synthetic data, with receipts."
    assert app.file_uploader[0].label == "Upload one CSV"
    assert app.button[0].label == "Try the demo dataset"
    assert "Start with a CSV" in app.info[0].value


def test_demo_dataset_reaches_configured_profile_state() -> None:
    app = AppTest.from_file(str(APP)).run(timeout=15)

    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert any(item.value == "1 · Review the inferred schema" for item in app.subheader)
    assert app.metric[0].value == "120"
    assert app.button[-1].label == "Generate and evaluate candidates"


def test_demo_dataset_completes_the_evidence_workflow() -> None:
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.button[0].click().run(timeout=15)
    app.number_input[0].set_value(100)

    app.button[-1].click().run(timeout=30)

    assert not app.exception
    assert any(item.value == "3 · Compare the evidence" for item in app.subheader)
    assert any(item.value == "4 · Export the evidence" for item in app.subheader)
    assert app.download_button[-1].label == "Download Markdown evidence report"
