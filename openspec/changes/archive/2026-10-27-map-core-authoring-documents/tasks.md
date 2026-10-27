# Tasks

## 1. Closed implementation units

- [x] 1.1 Implement the full machine-readable versioned document schema and sorted discovery with provenance; test unknown fields/versions/kinds, duplicates and file-stem mismatch, and document every source owner.
- [x] 1.2 Implement restricted round-trip parsing/serialization; test rejected YAML constructs/types and retained multiline prose, masks, bends and comments without golden shipped data.
- [x] 1.3 Implement AuthoringWorld diagnostics and RuntimeMapSnapshot gates using explicit external/freshness inputs; test empty and unreachable worlds as saveable while runtime adoption rejects.
- [x] 1.4 Expose the schema and a real read-only authoring inspection entry point, register independent package tests and substantive discoverable contract coverage, and run focused gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
