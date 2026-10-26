# Proposal

## Why

Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces with a specialist visual-design handoff. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces with a specialist visual-design handoff.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

- `map-editor-interaction`: Deliver the complete accessible workspace navigation, inspection, diagnostics and copy-only context surfaces with a specialist visual-design handoff.

### Modified Capabilities

None.

## Impact

editor frontend workspace/navigation/inspection/diagnostics/clipboard/focus modules; docs/design/map-editor-review.md (future specialist deliverable); no game shell imports

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-turn-recovery

code-conflicts: Frontend shell/focus modules are shared with domain editors; keep commands/tools in domain-owned modules. The visual specialist is an apply-time deliverable and never replaces any approved functional requirement.
