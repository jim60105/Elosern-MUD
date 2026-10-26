# Tasks

## 1. Closed implementation units

- [ ] 1.1 Implement deterministic game-side export of actual static identifiers/incoming refs/provenance and complete source closure; test real registry construction with live DB access forbidden and document the exporter command.
- [ ] 1.2 Implement independent context decoding and file/membership/hash/version freshness checks; test added/removed/transitive files and exporter changes versus geometry-only changes, plus external-source change with unchanged index/browser causing destructive commands and object-removing undo to refuse without disk/history changes.
- [ ] 1.3 Implement authoritative --check CI enforcement and commit reproducible output; test that stale output fails without rewriting it or using it as game authority.
- [ ] 1.4 Register discoverable mechanism evidence and CI ownership, document index regeneration/deletion limitations and run focused exporter/core and contract checks.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
