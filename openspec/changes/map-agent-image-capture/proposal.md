# Proposal

## Why

Vision-capable map-authoring agents need a reproducible image of a chosen disk-backed map without starting the editor or reading an operator's browser state. The approved [capture design](../../../docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md) defines the complete command and acceptance contract.

## What Changes

- Add `.agents/skills/map-data-authoring/scripts/capture_map.py`, composing the completed snapshot adapter and offline shared-renderer entry for continent, settlement and interior.
- Support explicit bounds, exact dimensions, all-layers-on defaults with repeatable `--hide`, lossless WebP by default and optional PNG.
- Own disposable browser lifetime, bounded readiness, lossless encoding, atomic output publication and one success JSON object.
- Document locked setup, every parameter/layer, coordinate units, refusal behavior and capture-then-read examples in the skill and relevant references.
- Perform actual three-view repository captures and read both formats. Composition, label readability and documentation quality are human-reviewed in `docs/development/map-editor.md`; tests establish executable mechanisms, not shipped copy or visual taste.

## Capabilities

### New Capabilities

- `map-image-capture`: Validated offline capture invocation, lossless atomic publication, structured results and failure/resource semantics.

### Modified Capabilities

None. Capture defaults do not change interactive editor preferences or game behavior.

## Impact

Own the skill command/docs, `elosern_map_editor/capture.py`, an optional developer capture dependency group and its `tools/map-editor/uv.lock`, focused package/top-level/browser tests and ownership registration. Use Playwright Chromium and Pillow in the independent editor tooling environment, never game runtime dependencies. Update existing map-editor developer documentation. No player command docs, source generation, browser synchronization, compatibility layer or migration.

## Batch:

depends-on: map-offline-render-surface
depends-on: map-capture-snapshot

One engineer-day integration slice after both runnable prerequisites: argument validation, browser orchestration, encoding/publication and complete skill documentation with end-to-end acceptance. No drawing or source-loading reimplementation is included.

Code-conflict notes: serialize developer documentation, `.github/browser-shards.json`, traceability associations and any frontend payload integration with the prerequisite owners. The command owns Python capture dependencies/lock; the surface owns frontend scripts/build/lock; the snapshot owns loader modules. No other active changes were present when proposed.
