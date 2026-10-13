# Spec: SynthGuard `mcp-server`

## Status

Implemented and verified. This module exposes the implemented local workflow to MCP clients through FastMCP over stdio.

## Objective

Let coding agents and MCP-capable applications profile, generate, evaluate, gate, and run the complete SynthGuard workflow using the same domain services as the Studio.

## Tools

- `profile_dataset`: safely profile one allowed CSV.
- `generate_synthetic_data`: generate one Gaussian Copula or CPU CTGAN artifact run.
- `evaluate_synthetic_data`: evaluate a real/synthetic/metadata artifact set.
- `gate_candidates`: apply a typed policy to supplied evaluation results.
- `run_synthguard_workflow`: generate selected methods, evaluate them, rank them, and return a Markdown report.

Every successful tool returns JSON-serializable typed evidence. Expected failures become MCP tool errors containing a stable code and safe message; partial workflow output is never returned as success.

## Filesystem Boundary

- `SYNTHGUARD_ALLOWED_ROOTS` is an OS-path-separator-delimited allowlist.
- When unset, the server allows only its resolved current working directory.
- Every source, metadata, synthetic, and output path is resolved before use and must remain under one allowed root.
- Symlink escapes, missing input files, empty allowlists, and outside output paths fail before domain work.
- Successful artifact paths may be returned because they have already passed the allowlist.

## Transport and Runtime

- FastMCP stdio is the default and only documented MVP transport.
- The server makes no network calls and requires no credentials.
- Entry point: `uv run synthguard-mcp`.
- Tool definitions contain concise descriptions and typed parameters suitable for agent discovery.

## Boundaries

- No duplicated profiling, synthesis, metric, gate, or report logic.
- No arbitrary file reads, directory listing, deletion, shell execution, HTTP server, authentication, or remote storage.
- No raw source rows in tool results or errors.
- No privacy, anonymity, or compliance claims.

## Verification

- Unit tests for allowlisted, outside, traversal, and symlink paths.
- Direct tool-adapter tests for profile, generation/evaluation, gating, and complete workflow.
- FastMCP discovery test proves the exact five-tool surface.
- Full repository tests, Ruff, formatting, and mypy pass offline.
