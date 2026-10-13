# Threat Model

## Scope and assets

SynthGuard is a single-user, local process. The protected assets are source datasets, local filesystem contents, generated artifacts, and the integrity of evaluation evidence. There is no hosted service, account system, database, or remote model call.

## Trust boundaries

| Boundary | Abuse case | Control | Residual risk |
|---|---|---|---|
| Uploaded/source CSV | Oversized or malformed content exhausts memory or leaks values through errors | Byte/row limits, UTF-8 parsing, structured value-safe errors | Allowed files are loaded in memory; limits must fit the machine |
| Inferred metadata | Identifier or sensitive field is misclassified | Advisory flags, human review, validated overrides | Automated inference is imperfect |
| SDV training | Candidate memorizes or closely copies records | Exact-copy, near-neighbor, and DCR evidence | Metrics are indicators, not formal privacy guarantees |
| Output paths | Traversal or symlink escapes allowed roots | Resolve first, require containment, immutable UUID run paths | A user who controls an allowed root can read its artifacts |
| MCP inputs | Agent requests arbitrary local files | Explicit root allowlist, typed arguments, no listing/deletion/shell tools | The operator must configure narrow roots |
| Resource use | CTGAN or pairwise distance consumes excessive CPU/RAM | Bounded rows, privacy sampling cap, CPU-oriented controls | CTGAN can still be slow on modest hardware |
| Dependencies | Known vulnerability or compromised package | Locked graph, CI audit, minimal direct dependencies, Dependabot | Audits cannot detect every supply-chain attack |
| Interpretation | A passing badge is treated as anonymous/compliant | Criterion-level evidence, stored policy, repeated non-guarantee | Final release judgment remains human responsibility |

## Data handling

- Processing and model training stay on the local machine.
- Source rows are not displayed by the studio, returned by MCP tools, or written to logs.
- Source files are read without modification.
- Generated runs remain local and are ignored by Git.
- No telemetry, API key, URL import, remote storage, or background worker exists.

## Out of scope

SynthGuard does not provide differential privacy, k-anonymity, regulatory certification, access control for shared machines, malware scanning, encrypted storage, or a guarantee that synthetic data cannot reveal source information. Those require separate product and security decisions.

## Release review

Before release: run the locked dependency audit, scan tracked files for credentials, verify path-containment tests, execute the full test/static gate, and install the built wheel in a clean environment.
