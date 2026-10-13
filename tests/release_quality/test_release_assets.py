"""Executable expectations for the public release surface."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parents[2]
REQUIRED_DOCUMENTS = (
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/RELEASE_EVIDENCE.md",
    "docs/THREAT_MODEL.md",
)


def test_public_release_assets_exist_and_are_linked_from_readme() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    for relative_path in REQUIRED_DOCUMENTS:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path
        assert f"]({relative_path})" in readme, relative_path


def test_readme_local_markdown_links_resolve() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    destinations = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
    local_destinations = [
        destination.split("#", maxsplit=1)[0]
        for destination in destinations
        if "://" not in destination and not destination.startswith("#")
    ]

    assert local_destinations
    for destination in local_destinations:
        assert (PROJECT_ROOT / destination).exists(), destination


def test_demo_dataset_is_fictional_and_workflow_ready() -> None:
    demo_path = PROJECT_ROOT / "examples/demo_customers.csv"
    frame = pd.read_csv(demo_path)

    assert list(frame.columns) == [
        "customer_id",
        "age",
        "region",
        "plan",
        "monthly_spend",
        "tenure_months",
        "churned",
    ]
    assert len(frame) >= 60
    assert frame["customer_id"].is_unique
    assert set(frame["churned"]) == {False, True}
    assert frame["churned"].value_counts().min() >= 10
    assert not frame.isna().any().any()


def test_project_metadata_is_release_ready() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
        metadata = tomllib.load(project_file)
    project = metadata["project"]

    assert project["license"] == "MIT"
    assert "synthetic-data" in project["keywords"]
    assert "License :: OSI Approved :: MIT License" in project["classifiers"]
    assert project["scripts"]["synthguard-mcp"]

    sdist_includes = metadata["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    assert "/docs" in sdist_includes
    assert "/SPEC-*.md" in sdist_includes


def test_ci_enforces_every_release_gate() -> None:
    workflow = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    dependabot = (PROJECT_ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")

    for command in (
        "uv sync --locked --all-extras",
        "ruff check .",
        "ruff format --check .",
        "mypy src/synthguard",
        "pytest --cov=synthguard",
        "pip-audit",
        "uv build",
        "smoke_distribution.py",
    ):
        assert command in workflow
    assert "package-ecosystem: uv" in dependabot
    assert "package-ecosystem: github-actions" in dependabot


def test_importing_mcp_path_helpers_does_not_construct_the_server() -> None:
    command = (
        "import sys; import synthguard.mcp_server.paths; "
        "assert 'synthguard.mcp_server.server' not in sys.modules"
    )

    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
