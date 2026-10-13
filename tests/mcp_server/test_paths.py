from pathlib import Path

import pytest

from synthguard.mcp_server.paths import McpServerError, PathPolicy


def test_policy_accepts_contained_input_and_output(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    policy = PathPolicy((tmp_path,))

    assert policy.input_file(source) == source.resolve()
    assert policy.output_directory(tmp_path / "runs") == (tmp_path / "runs").resolve()


def test_policy_rejects_outside_and_traversal_paths(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("a\n1\n", encoding="utf-8")
    policy = PathPolicy((allowed,))

    for candidate in (outside, allowed / ".." / "outside.csv"):
        with pytest.raises(McpServerError) as caught:
            policy.input_file(candidate)
        assert caught.value.code == "PATH_NOT_ALLOWED"
        assert str(tmp_path) not in str(caught.value)


def test_policy_rejects_symlink_escape(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    source = outside / "source.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    link = allowed / "linked"
    link.symlink_to(outside, target_is_directory=True)
    policy = PathPolicy((allowed,))

    with pytest.raises(McpServerError) as caught:
        policy.input_file(link / "source.csv")

    assert caught.value.code == "PATH_NOT_ALLOWED"


def test_policy_requires_existing_input_file(tmp_path: Path) -> None:
    policy = PathPolicy((tmp_path,))

    with pytest.raises(McpServerError) as caught:
        policy.input_file(tmp_path / "missing.csv")

    assert caught.value.code == "FILE_NOT_FOUND"


def test_environment_defaults_to_current_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SYNTHGUARD_ALLOWED_ROOTS", raising=False)

    assert PathPolicy.from_environment(current_directory=tmp_path).roots == (tmp_path.resolve(),)


def test_environment_parses_multiple_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setenv("SYNTHGUARD_ALLOWED_ROOTS", f"{first}:{second}")

    policy = PathPolicy.from_environment(current_directory=tmp_path)

    assert policy.roots == (first.resolve(), second.resolve())


def test_empty_explicit_allowlist_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SYNTHGUARD_ALLOWED_ROOTS", ":")

    with pytest.raises(McpServerError) as caught:
        PathPolicy.from_environment(current_directory=tmp_path)

    assert caught.value.code == "INVALID_ALLOWED_ROOTS"
