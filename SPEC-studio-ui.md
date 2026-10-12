# Spec: SynthGuard `studio-ui`

## Status

Approved for implementation. This module provides a local Streamlit interface over the three implemented domain modules.

## User Experience

One page guides the user through four clear stages: upload one CSV, review its inferred schema, configure generation and thresholds, then compare evidence and download the winning candidate plus a Markdown report.

## Design Contract

- Screen job: make synthetic-data tradeoffs understandable in under five minutes.
- Primary action: **Generate and evaluate candidates**.
- Visual direction: compact technical audit workspace; deep navy, off-white surfaces, teal evidence accent, amber risk accent; no gradients or decorative AI imagery.
- Desktop uses a narrow configuration sidebar and a dense evidence workspace. Mobile collapses to one column.
- Status always includes text and symbols; color is never the only signal.
- Empty, running, success, no-winner, and error states must be explicit.

## Functional Scope

- CSV upload capped at 25 MB and materialized only in a session temporary directory.
- Automatic profile summary and reviewable column table.
- Gaussian Copula and CPU CTGAN selection, output row count, seed, and optional classification target.
- User-editable gate thresholds.
- One action generates, evaluates, and ranks selected candidates using existing public APIs.
- Comparison table, criterion details, weak statistical areas, and privacy/utility summaries.
- Synthetic CSV download for the winner and Markdown evidence-report download.

## Boundaries

- UI contains no metric, threshold, or ranking logic.
- No network calls, accounts, databases, telemetry, or server-side user storage.
- Uploaded source data is never rendered row-by-row.
- A passing candidate is not labeled anonymous, compliant, or safe.

## Verification

- Reporting unit tests and Streamlit application smoke tests.
- Full static and backend test suite.
- Real browser check for initial, uploaded, and results states; desktop and mobile layouts; clean console; accessible labels and heading order.
