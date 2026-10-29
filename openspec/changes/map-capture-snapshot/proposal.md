# Proposal

## Why

The approved [capture design](../../../docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md) requires one current, read-only disk snapshot without editor lifecycle. Existing confined loading and projection can supply it, but malformed layouts currently leave a loadable editor read with diagnostics and partition handling is unconditional.

## What Changes

- Add a pure capture snapshot adapter owned by `elosern_map_editor`, reusing confined discovery, core YAML loading, layout projection and terrain preview.
- Reject source/layout structure failures while preserving loadable semantic work in progress and diagnostics.
- Decode and freshness-check partition outlines only for continent captures with partition visible; refuse unavailable output with explicit regeneration or hide guidance.
- Preserve source files, layouts and generated artifacts; never instantiate editor service, writers, watchers or game state.

## Capabilities

### New Capabilities

- `map-capture-snapshots`: One-shot confined authoring snapshots with capture-specific structure rejection and conditional partition admission.

### Modified Capabilities

None. Interactive editor stale-preview, editing and older-partition policies remain intact.

## Impact

Own `tools/map-editor/elosern_map_editor/snapshot.py`, proposed `capture_snapshot.py`, adjacent synthetic tests and `tests/test_map_capture_snapshot.py` for discoverable real consumer evidence. Reuse map-core codecs without game imports. Update `docs/development/map-editor.md`. No browser, image encoder, game dependency, compatibility layer or migration.

## Batch:

No dependencies.

One engineer-day slice: extract the existing pure read/projection seam and add one concrete read-only consumer with failure-matrix coverage. This is a complete callable loader, independent of browser rendering.

Code-conflict notes: no production-code overlap with `map-offline-render-surface`; serialize shared developer documentation and traceability work. `map-agent-image-capture` consumes the adapter unchanged. Its command must not reload sources for scene selection or partition freshness.
