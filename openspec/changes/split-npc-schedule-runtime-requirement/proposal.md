# Proposal: Split the NPC Schedule Runtime Requirement

## Why

The synchronized `npc-schedule-runtime` requirement combines independent settlement, occurrence arithmetic, silence, and persisted exam-hold contracts in one requirement exceeding OpenSpec's 500-character strict-validation limit. Split it into cohesive, independently traceable requirements while preserving every current behavioral clause and schedule-hold detail.

## What Changes

- Replace the oversized clock-source requirement with eight concise requirements covering source selection, due-window boundaries, cycle arithmetic/order, state entries, movement/events, service-gate silencing, exam-hold deferral, and hold release.
- Preserve all existing scenarios and semantic clauses, including absolute daily/weekly phase, assignment and reload/calendar boundary behavior, due-start exception, stable primary-key ordering, JSON-safe events, real Exit traversal, byte-identical unaffected NPC settlement, and held-interval recovery/release without clock advancement.
- Update substantive `covers_requirement` annotations to the new canonical requirement IDs; maintain coverage for each resulting requirement and do not leave stale IDs.
- Require `openspec validate --all --strict`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked python -m tools.contract_gate` to pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-schedule-runtime`: split the oversized requirement into testable requirements without changing runtime behavior or weakening any existing contract.

## Impact

- OpenSpec capability spec: `openspec/specs/npc-schedule-runtime/spec.md` (modified on apply).
- Traceability annotations in schedule runtime tests (modified on apply where their existing canonical ID is replaced).
- The archived guild exam schedule-hold synchronization is the source of the added hold clauses; this proposal is only a validation-driven clarification/split, not a new hold behavior or an implementation/archive action.

## Batch

depends-on: none

Code-conflict notes: no dependency on another in-flight change; the apply phase edits the shared `npc-schedule-runtime` capability spec and its schedule-runtime test annotations. Coordinate with any concurrent change editing those same files. This proposal itself touches only this change directory.