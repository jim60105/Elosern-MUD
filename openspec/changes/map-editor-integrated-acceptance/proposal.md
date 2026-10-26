# Proposal

## Why

Prove the complete independent editor and preserved game behavior through real browser/file/game consumer acceptance without inventing new behavior. The approved architecture needs a closed, runnable slice with one source owner and complete consumer coverage.

Source documents are `docs/superpowers/specs/2026-10-26-map-editor-design.md` and its companion `2026-10-26-map-editor-frontend-requirements.md`, read afresh for this batch. Their status remains written-spec review pending. The current request authorizes proposal creation only, not implementation approval or a change to design substance.

## What Changes

- **BREAKING** Prove the complete independent editor and preserved game behavior through real browser/file/game consumer acceptance without inventing new behavior.
- Deliver the exact producer/consumer/error-state contracts in design.md and worker-contract.md; no incomplete viewer or one-domain completion claim.
- Preserve geography, canonical prose, balance, player commands and existing game transaction/observability owners; no generated Python, compatibility layers, migrations or merge machinery.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

No executable behavior changes; `.openspec.yaml` declares `skip_specs: true`. Existing behavior gets integrated evidence, not a duplicate requirement.

## Impact

proposed web/tests/browser/test_map_editor_workflows.py and test_map_editor_accessibility.py; tests/test_map_editor_independent_environment.py; map runtime integration tests; CI/package evidence entry points; docs/development/map-editor.md and docs/design/map-editor-review.md

This is one bounded engineer-day within the mandatory complete batch. `batch-plan.md` in map-core-sparse-geometry contains the dependency/conflict matrix and source coverage. Tests/docs are included with each task. The frontend specialist's visual polish, copy quality and design fidelity are human-reviewed in `docs/design/map-editor-review.md`; tests establish mechanisms and interactions rather than shipped wording or markup.

## Batch:

depends-on: map-editor-partition-jobs

code-conflicts: Final gate depends transitively on every functional batch slice; serialize browser/Python shard manifests, source signatures and traceability claims. It does not supersede or waive earlier focused evidence.
