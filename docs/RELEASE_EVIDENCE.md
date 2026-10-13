# Release Evidence: 0.1.0

Verified locally on 2026-10-13 with Python 3.12 and the committed `uv.lock`.

## Automated quality

| Gate | Result |
|---|---|
| Full test suite | 126 passed |
| Project statement coverage | 86.46% (85% release floor) |
| Ruff lint | Passed |
| Ruff format check | Passed |
| Strict mypy | Passed for 28 source files |
| Locked-environment vulnerability audit | No known vulnerabilities found |
| Source and wheel build | Passed |
| Clean wheel installation | Passed in a new Python 3.12 virtual environment |
| Installed-package smoke test | Public import, console entry point, and five MCP tools verified |

The vulnerability scanner skipped only the local `synthguard` distribution because version `0.1.0` is not published on PyPI. Project code is covered by tests, static analysis, path-boundary tests, and the tracked-file credential scan.

## Demo evidence

The committed fictional dataset completed the Gaussian workflow with seed `42` and 100 generated rows:

| Evidence | Observed |
|---|---:|
| Gate status | Pass |
| Statistical quality | 0.7966 |
| Exact copied rows | 0 |
| Near-duplicate rate | 0.0000 |
| DCR baseline protection | 0.7977 |
| Artifacts | `synthetic.csv`, `metadata.json`, `manifest.json` |

These numbers prove that the release path executes; they are not a universal benchmark or privacy guarantee.

## Interface verification

- Streamlit initial, demo, and completed-result states were exercised in a real browser.
- Layouts were checked at 320, 768, 1024, and 1440 pixels without horizontal overflow.
- The completed state exposed comparison evidence and both CSV/report downloads.
- FastMCP discovery returned exactly the five documented tools.
- Outside-root, traversal, and symlink-escape MCP paths were rejected in automated tests.

## Review evidence

- An inclusive-threshold condition was deliberately changed from `>=` to `>`; the boundary regression test failed, so the mutation was detected and then restored.
- The five-axis review covered correctness, readability, architecture, security, and performance.
- The review removed MCP server construction from helper-package imports and added a regression test for that boundary.
- Tracked files contained no private-key header, AWS access-key pattern, GitHub token pattern, or OpenAI-style secret-key pattern.

Re-run every release gate using the commands in [CONTRIBUTING.md](../CONTRIBUTING.md).
