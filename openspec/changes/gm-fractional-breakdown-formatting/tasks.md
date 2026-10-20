# Tasks

## 1. Reader formatting and immutable API regression

- [ ] 1.1 Replace integer-only percentage formatting with existing numeric presentation semantics or a local equivalent that retains sign and fraction; add focused reader controls for +12.5/-2.5 percent, integral percentages, multiplier and fractional flat values, and update the GM inspection guide with percentage-point semantics; verify exact readable values and unchanged authoritative totals.
- [ ] 1.2 Extend the protected character-detail API regression with a real valid fractional contribution source; verify breakdown availability, layer provenance, unchanged persisted state, existing auth protection and genuine source-failure isolation, annotate the curated-summary requirement and register a new module only in its exact manifest owner if introduced.

## 2. Integration handoff

- [ ] 2.1 Run focused reader/API tests, exact ownership contracts and `openspec validate gm-fractional-breakdown-formatting --strict`; record results and confirm the fix changes neither rule arithmetic nor the separate lineage error handling.

## Workflow follow-up

- Synchronization/archive owner runs the ordinary post-sync contract gate. No party acceptance task is completed by this reader fix alone.
