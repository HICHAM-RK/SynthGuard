# Security Policy

## Supported version

Security fixes currently target the latest `0.1.x` release line.

## Report a vulnerability

Do not open a public issue containing sensitive details. Use GitHub's private vulnerability-reporting feature for the repository. Include the affected version, a minimal reproduction, impact, and any suggested mitigation. Do not include real customer data or credentials.

## Product boundary

SynthGuard processes files locally and has no authentication, hosted API, telemetry, or remote storage. MCP access is intentionally limited to resolved paths beneath configured local roots. This reduces exposure but does not make arbitrary datasets safe to release.

Synthetic output is not automatically anonymous, private, compliant, or fit for production. The privacy measurements are risk indicators. Review the [threat model](docs/THREAT_MODEL.md) before using generated data.
