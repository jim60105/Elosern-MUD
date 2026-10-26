# Proposal

## Why

Implement external AI turn-taking, directory watching, stale preview adoption and explicit reconnect/restart recovery. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Implement external AI turn-taking, directory watching, stale preview adoption and explicit reconnect/restart recovery.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-turn-taking`: Implement external AI turn-taking, directory watching, stale preview adoption and explicit reconnect/restart recovery.

### Modified Capabilities

None.

## Impact

elosern_map_editor session state machine/watch coordinator/SSE; frontend connection/preview/turn state and handoff dialogs; all mutation guards; independent real-filesystem tests

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-document-commands

code-conflicts: Sequence after writer integration. Generation later adds a state guard to this same state machine; no second watcher, session owner or merge protocol.
