# Proposal

## Why

Implement continuous workspace file following: directory watching, own-write recognition, automatic adoption of loadable external changes, stale preview retention and reconnect/restart recovery, with no explicit AI handoff. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md`, its companion `2026-10-26-map-editor-frontend-requirements.md` and the frontend specialist deliverable `2026-10-26-map-editor-frontend-design.md`, whose decision D3 replaces the explicit turn-taking state machine with continuous file following. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement continuous workspace file following: directory watching, own-write recognition, automatic adoption of loadable external changes, stale preview retention and reconnect/restart recovery, with no explicit AI handoff.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-file-following`: Implement continuous workspace file following: directory watching, own-write recognition, automatic adoption of loadable external changes, stale preview retention and reconnect/restart recovery, with no explicit AI handoff.

### Modified Capabilities

None.

## Impact

elosern_map_editor watch coordinator/write-pause state/SSE; frontend connection/preview state, priority banner conditions and draft-held adoption; all mutation guards; independent real-filesystem tests

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. Visual direction, states and copy follow the approved frontend design and the `docs/design/map-editor/` prototype; fidelity is human-reviewed per scenario in `docs/design/map-editor-review.md`, and tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-document-commands

code-conflicts: Sequence after writer integration. Generation later adds its mutation guard beside this write-pause state; no second watcher, session owner, turn state machine or merge protocol.
