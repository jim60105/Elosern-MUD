# Design

## Context

See `proposal.md` for motivation and `specs/map-offline-rendering/spec.md` for the behavioral contract. The approved source is `docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md`. Engine ownership follows `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, including its bounded static-map YAML exception and view-only presentation boundary.

Observed code anchors:

- `tools/map-editor/frontend/src/components/MapCanvas.vue` combines SVG drawing, terrain raster encoding, cards/curved links, fitting and workbench interactions. Its current fit uses point bounds and a fixed 72-pixel margin; this alone does not establish capture label containment.
- `src/lib/map_scene.js` exports `sceneFor`, `continentScene`, `settlementScene` and `interiorScene`. Settlement bounds include road bends; interior bounds include exterior cards. Empty selections omit selected-road arrows and bend handles.
- `src/lib/layout_edit.js` uses stored layout positions or a deterministic three-column fallback and `toScene([x,y]) = {x,y:-y}`.
- `@elosern/map-view` supplies neutral projection/fit/glyph primitives. The frontend has Node tests, an import-boundary gate, Vite 7/Vue 3 and pnpm 12.5.1. Current Vite assets use root URLs and ES modules for an HTTP-served SPA, so its existing dist cannot simply be opened as a local capture page.
- Managed editor browser tests live in `web/tests/browser/`; `test_map_editor_standalone.py` already exercises inert authored text and local fonts. Keep new browser methods registered in `.github/browser-shards.json`.

## Goals / Non-Goals

**Goals:** A fully runnable frontend entry receiving a synthetic or real projected world in memory and rendering all three views through the same drawing as the editor. Camera and visibility decisions stay independent of browser workbench state.

**Non-Goals:** Python loading/encoding/CLI, a dev server, full-editor cropping, new map glyphs, new road arrows, additional relationships, a capture mode spread through App.vue, or game-runtime dependencies. No interactive preference changes or compatibility paths.

## Decisions

### Shared surface, separate hosts

Extract the map drawing into proposed `src/components/MapSurface.vue` and focused pure presentation helpers. `MapCanvas.vue` remains the interactive host owning selection, pointer/keyboard behavior, control points, controls and workbench overlays. Both hosts consume a single SVG/drawing implementation; extract event/mark coordinate plumbing only where needed to retain interaction. The capture host passes an empty selection, no mutation handlers and no workbench decorations. Do not copy SVG into a second component.

Use the existing editor theme CSS and locally emitted fonts through its import allowlist. Keep background/dot field as shared map content. Keep coordinate metadata outside the image. Interiors gain no metric scale or north indicator. The map-only entry omits all controls and highlights rather than relying on screenshot cropping to hide them.

### Stable cross-change interface

The snapshot prerequisite returns JSON-ready `{world, partition, diagnostics}`. `world` preserves the existing projection including layouts and terrain preview; `partition` is null or `{outlines}` in scene metres, decoded and freshness-admitted by the loader. The frontend accepts a structured request:

`{world, partition, view, map_id, width, height, bounds, hidden_layers}`

`view` is continent/settlement/interior; `map_id` is null only for continent; `bounds` is null or the ordered CLI-frame array; hidden layers are normalized names. Diagnostics remain Python result data and are not painted. The capture entry exposes proposed `window.renderMapCapture(payload)` returning a Promise of `{bounds, units, axes}` only after successful readiness. Rejections expose an error to the runner; do not resolve partial renders. Use axes objects `{x:"east",y:"north"}` for geography and `{x:"right",y:"down"}` for interiors. These are internal interfaces shared with the other two change designs, not a new service API.

### Local-file build, no runtime server

Add a dedicated Vite capture config and `pnpm --dir tools/map-editor/frontend run build:capture`. Build `frontend/capture-dist/index.html` with relative local CSS/font paths and a classic IIFE entry (no dynamic chunks, runtime ES-module imports or module-preload fetch). Reuse the existing Vue plugin and alias/import-boundary rules. Preserve the normal `build` and `dist/` unchanged. The generated HTML contains only the map host and fixed build assets; authored payload is never embedded in HTML/script text.

The runner opens that file and passes an object via browser evaluation to the fixed function. Await Vue mount/update, `document.fonts.ready`, terrain image decode, measured layout and paint before resolving readiness. Any asset/decode/render error rejects; a Python-side bounded wait handles hangs. A real local-file browser test with HTTP requests blocked proves this asset arrangement, including fonts, rather than assuming `base: './'` solves module CORS.

### Camera computation and painted extents

Use neutral projection primitives and one capture camera helper near the editor scene owners. At the capture boundary multiply continent kilometres by 1000; settlement bounds already use scene metres. Interior CLI rectangle `[minX,minY,maxX,maxY]` becomes scene `[minX,-maxY,maxX,-minY]`, and reported scene bounds convert back in reverse Y order. Keep floats; do not route capture bounds through integer-snapping `fromScene()`.

For explicit extent, keep its centre and choose the larger required per-pixel scale, expanding the narrower axis. For `[0,0,10,20]` at 200x100 the result is `[-15,0,25,20]`; for interior `[1,2,5,8]` at 100x100 it is `[0,2,6,8]`. Do not apply the editor minimum span to explicit bounds or clamp/recenter empty/outside regions.

For automatic fit, derive geometry from the complete unfiltered scene and include bent links, curve excursions, room/exterior card dimensions, glyph sizes and actual rendered label extents after local fonts load. Fit using measured painted extents with bounded layout convergence. Positive dimensions remain accepted even when tiny; scale the full map surface uniformly, including its glyph/label padding when necessary, instead of introducing an undocumented minimum output size. Human-readable detail at tiny dimensions is not promised. Layer filtering must not alter the reference geometry or camera. Regional captures deliberately clip at the image edge.

### Layer ownership

| View | Geometry layers | Labels |
| --- | --- | --- |
| continent | terrain (mainland/raster/forest edge), water (waterways), ridge (walls/passes/fords), locations (locations/harbour sites), footprint (settlement masks), partition (national borders/district outlines) | labels |
| settlement | nodes (including gate glyphs), roads (existing directed bent links) | labels |
| interior | rooms (cards), connections (within-interior links/indicators), exterior (doorway card/link) | labels |

Classify every existing drawable at its scene/presentation boundary, including national-border paths from terrain preview under partition. Geometry hiding suppresses its own labels; label hiding removes text only and preserves direction indicators/cards. Nodes/rooms and links remain independent. Default capture visibility enables every applicable layer, including footprints and labels, without reading or changing editor preference storage. An all-hidden scene draws only its normal background at the original camera.

## Risks / Trade-offs

- Shared-surface extraction can change drag/selection behavior. Keep interactions host-owned and run a focused real editor selection/pan/zoom/move smoke after extraction.
- Local file origin differs from HTTP, especially fonts/module assets. Use the separate classic bundle and test actual file navigation with network denied.
- Very long text and small pixel dimensions challenge fixed-size full-map fitting. Measure after fonts, bound convergence and uniformly scale the complete surface for small outputs; normal 1280x960 captures must include labels/cards.
- Browser evidence can become source/markup snapshots. Assert synthetic rendered positions, visibility, containment and inert execution; never pin shipped names, literal SVG or counts from repository data.

## Verification and requirement evidence

Proposed `web/tests/browser/test_map_capture_surface.py` owns discoverable mechanism tests for each new requirement, using synthetic projected worlds and real local-file rendering. Node tests in `frontend/tests/capture.test.mjs` cover coordinate arithmetic/layer transforms; browser assertions independently establish final painted geometry and network behavior. Use existing synthetic fixture builders, never permanent shipped-data snapshots. Register every browser method in the existing ownership manifest.

Before archive, resolve new canonical requirement IDs using `tools.spec_traceability list` against an equivalent merged spec tree, associate only substantive discoverable tests, and record any provisional nearest-current association/reason while active. Do not guess IDs. Full managed browser/evidence runs remain CI-owned. Local checks are the focused Node file, capture build/import boundary, one browser class and `tools.contract_gate`.

Human review of composition, local Traditional Chinese glyph readability and visual equivalence belongs in the existing `docs/development/map-editor.md` capture review section with inspected images/commands. Those qualities are deliberately absent as standalone requirements. Update that document for the shared surface/build entry in this slice.

## Migration Plan

Land the shared-surface cutover and its runnable capture entry together. Preserve the editor entry and its interactions. No persisted data changes, migrations, compatibility aliases or temporary implementation flags. Rollback is a normal code revert before command integration; the downstream command must wait for this complete change.
