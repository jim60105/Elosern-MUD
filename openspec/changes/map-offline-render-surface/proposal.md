# Proposal

## Why

The approved [capture design](../../../docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md) needs offline images of all three map views without a second drawing implementation. Current drawing and workbench interactions share `MapCanvas.vue`.

## What Changes

- Extract reusable map drawing and keep the interactive host's controls and preferences unchanged.
- Add a local-file-loadable map-only entry accepting structured in-memory data, layer visibility and a camera request, with an explicit completion signal.
- Implement capture coordinate conversion, aspect-preserving bounds and full-map fitting, including card/label extents.
- Verify rendered layer behavior and offline assets with synthetic inputs. Visual polish and Traditional Chinese readability are human-reviewed, recorded in `docs/development/map-editor.md`, rather than wording or markup tests.

## Capabilities

### New Capabilities

- `map-offline-rendering`: Service-free rendering, capture camera semantics and independent per-view visibility through shared map drawing.

### Modified Capabilities

None. Existing interactive editor and neutral geometry contracts remain unchanged.

## Impact

Own `tools/map-editor/frontend/` drawing extraction, capture build configuration, package scripts and lock if needed, shared local styles/fonts, focused Node tests and `web/tests/browser/test_map_capture_surface.py`. Update `docs/development/map-editor.md` and browser ownership registration. Keep neutral primitives under `packages/map-view/` only when truly host-neutral. No game dependency, player command, compatibility layer or migration.

## Batch:

No dependencies.

One engineer-day slice: one frontend surface extraction and directly executable offline render entry, with camera/layer behavior tests. This slice is independently usable through a synthetic in-memory payload; it does not expose an unfinished capture command.

Code-conflict notes: no production-code overlap with `map-capture-snapshot`. Serialize `docs/development/map-editor.md`, `.github/browser-shards.json` and traceability integration. `map-agent-image-capture` depends on this entry and owns the final command; it must not duplicate drawing or alter this payload contract silently.
