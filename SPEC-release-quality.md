# Spec: SynthGuard `release-quality`

## Status

Implemented and verified. This module packages and verifies the implemented product without changing its domain behavior.

## Objective

Make SynthGuard safe to publish, easy to evaluate, and reproducibly installable. A reviewer must be able to understand the problem, run a non-sensitive demo, inspect the architecture and threat model, execute every quality gate, and install the built distribution without hidden services or credentials.

## Release Artifacts

- A recruiter-friendly README explains the problem, differentiators, architecture, evidence, quick start, MCP setup, and limitations.
- A committed synthetic demo CSV supports a no-secret first run.
- Architecture, security, contribution, changelog, and license documents are present and linked.
- Project metadata accurately describes Python support, license, and package purpose.
- Source distributions and wheels contain the required package and documentation files.

## Automated Quality Gate

GitHub Actions runs on pull requests and pushes to `main` using Python 3.12 and the committed `uv.lock`. The required gate performs:

1. immutable dependency installation;
2. Ruff lint and format checks;
3. strict mypy checking;
4. the complete pytest suite with at least 85% project coverage;
5. a dependency vulnerability audit;
6. source and wheel builds; and
7. installation and smoke testing of the built wheel in a clean virtual environment.

Dependabot checks Python dependency updates weekly. No release workflow publishes packages or deploys services in the MVP.

## Security and Privacy Evidence

- The threat model covers CSV uploads, local paths, generated artifacts, dependency supply chain, resource exhaustion, and misleading privacy claims.
- Documented controls include bounded inputs, safe errors, allowlisted resolved paths, immutable artifact runs, offline processing, aggregate-only evidence, and explicit non-guarantees.
- A release audit scans tracked content for likely credentials and confirms generated/user data remains ignored.
- The locked dependency graph has no unmitigated reachable critical or high known vulnerabilities at release time.
- No source dataset, generated user artifact, credential, telemetry, remote data transfer, or claim of anonymization is added.

## Verification

- Release-asset tests prove the demo dataset is structurally usable, documentation links resolve, required metadata is present, and MCP package imports have no server-construction side effect.
- The demo dataset completes the fast Gaussian workflow locally.
- `uv build` succeeds and a clean environment can import `synthguard` and discover the five MCP tools from the wheel.
- Full pytest, Ruff, formatting, and mypy gates pass.
- A five-axis review covers correctness, readability, architecture, security, and performance; at least one mutation check proves a relevant test detects a changed condition.

## Boundaries

- Release work does not change synthesis methods, evaluation formulas, gate thresholds, public domain contracts, resource limits, or artifact formats.
- CI and documentation must not require paid services, API keys, hosted databases, or network access at product runtime.
- Security and privacy documentation describes controls and residual risk; it does not claim certification, regulatory compliance, anonymity, or formal privacy.

