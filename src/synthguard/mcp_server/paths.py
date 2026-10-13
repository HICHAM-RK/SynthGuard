"""Allowlisted path resolution for every MCP filesystem argument."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class McpServerError(Exception):
    """Expected MCP adapter failure with a stable safe payload."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass(frozen=True, slots=True)
class PathPolicy:
    roots: tuple[Path, ...]

    def __post_init__(self) -> None:
        resolved = tuple(root.expanduser().resolve() for root in self.roots)
        if not resolved or any(not root.is_dir() for root in resolved):
            raise McpServerError(
                "INVALID_ALLOWED_ROOTS",
                "The configured filesystem allowlist is invalid.",
            )
        object.__setattr__(self, "roots", resolved)

    @classmethod
    def from_environment(cls, *, current_directory: Path | None = None) -> PathPolicy:
        configured = os.environ.get("SYNTHGUARD_ALLOWED_ROOTS")
        if configured is None:
            return cls(((current_directory or Path.cwd()).resolve(),))
        roots = tuple(Path(value) for value in configured.split(os.pathsep) if value.strip())
        return cls(roots)

    def input_file(self, value: str | Path) -> Path:
        candidate = Path(value).expanduser().resolve()
        self._assert_allowed(candidate)
        if not candidate.is_file():
            raise McpServerError("FILE_NOT_FOUND", "The requested input file was not found.")
        return candidate

    def output_directory(self, value: str | Path) -> Path:
        candidate = Path(value).expanduser().resolve()
        self._assert_allowed(candidate)
        return candidate

    def _assert_allowed(self, candidate: Path) -> None:
        if not any(candidate.is_relative_to(root) for root in self.roots):
            raise McpServerError(
                "PATH_NOT_ALLOWED",
                "The requested path is outside the configured allowlist.",
            )
