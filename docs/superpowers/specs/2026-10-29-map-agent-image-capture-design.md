# Map Authoring Images for Vision-Capable Agents

**Date:** 2026-10-29
**Status:** Approved by the user on 2026-10-29, including written-spec review.
**Implementation status:** Not implemented by this document.
**Scope:** Extend `.agents/skills/map-data-authoring/` with an offline, read-only image command for continent, settlement, and interior maps.

## 1. Goal and boundaries

A vision-capable agent can request one map view, choose its extent and hidden layers, produce an image, and read that image through its image-reading tool. The image contains the map without editor chrome. The existing YAML remains the source of truth for identities, coordinates, relationships, and edits.

The command does not depend on a running game or editor service. It never connects to the operator's browser or learns the operator's current view. Current domain, selected map, hidden layers, and camera are frontend-local state today; this change does not introduce view-state synchronization.

Exclude editing, source regeneration, file watching, history, player knowledge, game state, batch captures, interactive controls, and a second implementation of map drawing. One invocation produces one image of one view. Supporting all three views is required.

This design preserves the ownership boundaries in the [engine design](2026-07-29-ai-mud-engine-design.md), [map editor design](2026-10-26-map-editor-design.md), and [editor frontend design](2026-10-26-map-editor-frontend-design.md). The capture command's all-layers-visible default applies only to capture; the interactive editor's preferences remain unchanged.

## 2. Chosen approach

Reuse the editor's source projection and scene builders, its map drawing, and the neutral `@elosern/map-view` primitives. Introduce a separate, map-only render entry that accepts an in-memory capture payload and has no editor client, network transport, or mutation handlers.

A short-lived headless browser renders that entry. A command under `.agents/skills/map-data-authoring/scripts/` owns argument parsing, loading, browser lifetime, image encoding, and reporting. Reusable loading and rendering logic stays with its existing package owners rather than being copied into the skill.

The alternatives were an independent Python renderer and starting the full editor then cropping its canvas. The former duplicates geometry and drawing rules; the latter introduces an unnecessary service lifecycle and editor interaction. Neither is selected.

### 2.1 Component responsibilities

| Unit | Responsibility | Dependencies |
| --- | --- | --- |
| Skill command | Validate arguments, obtain a read-only snapshot, invoke rendering, encode the image, report its location | Existing map/editor loading utilities and local capture dependencies |
| Snapshot adapter | Supply the world projection, interior layouts, diagnostics, and requested partition outlines | Map core and the editor's confined source reader/projection |
| Map-only entry | Assemble the selected scene, apply visibility and camera, draw without chrome, signal readiness | Existing scene builders, shared drawing, `@elosern/map-view`, bundled styles/fonts |
| Headless capture runner | Open a disposable browser, wait for readiness, capture at the requested pixel size, close resources | Local browser automation runtime |

Separate the reusable map surface from workbench behavior where necessary. Do not introduce a `capture` branch throughout the editor application or duplicate its SVG markup. Preserve the editor's interactive behavior during extraction.

Build the map-only entry with the editor frontend's existing pnpm toolchain. Its built assets must be loadable locally by the runner without launching an HTTP server. Pass source data as structured data, not interpolated executable code or HTML. Authored labels remain text, never raw HTML.

Runtime needs no pnpm process, dev server, API session, remote fonts, or network assets. Capture dependencies belong to developer tooling, not the game runtime. Document locked-environment setup and browser installation in the skill; missing dependencies produce actionable errors, not automatic installation. Exact dependency placement and build commands belong to implementation planning.

## 3. Command contract

The command is named `capture_map.py` under the skill's `scripts/` directory. Run it from the repository root in a documented uv-managed, locked environment. The current working directory supplies the source workspace; do not add a service URL parameter.

| Argument | Contract |
| --- | --- |
| `--view` | Required; `continent`, `settlement`, or `interior` |
| `--map` | Required settlement/interior document ID for those views; rejected for continent |
| `--bounds MIN_X MIN_Y MAX_X MAX_Y` | Optional finite numbers with strictly increasing axes; otherwise fit the complete selected map |
| `--width` | Positive integer output width in pixels; default 1280 |
| `--height` | Positive integer output height in pixels; default 960 |
| `--hide LAYER [LAYER ...]` | Optional; repeatable, with repeated names deduplicated; all applicable layers are visible by default |
| `--format` | `webp` or `png`; default `webp` |
| `--output` | Required image path, resolved relative to the working directory |

There is no `--show`. Reject unknown flags, unknown layers, and layers belonging to another view. Reject a filename extension that does not match the selected format. The output parent directory must exist. Reusing an output filename replaces it only after a complete image has been encoded; failure must not damage an existing image or report it as this invocation's result.

Use device scale factor 1 so the encoded dimensions equal the requested width and height. Both WebP and PNG output are lossless; do not expose a quality slider. Do not add AVIF or JPEG output.

The skill must document the entire argument and per-view layer lists, including defaults and units. Its examples must cover each view, a regional capture, multiple hidden layers, and PNG output. A missing map ID is resolved by reading the source documents, without inventing a new map-list API.

### 3.1 Coordinate frames and fitting

| View | CLI bounds and reported bounds | Axis convention |
| --- | --- | --- |
| Continent | Continental kilometres, not wilderness cell indices; convert to scene metres at the boundary | X east, Y north |
| Settlement | Authored local metres, not continental/world metres | X east, Y north |
| Interior | Editor layout grid units, not physical distances | X right, Y down, matching stored layout `x`/`y` |

Interior scene points currently invert stored layout Y through `toScene()`. The capture boundary converts input bounds to scene points and converts reported bounds back to layout units. It must not label interior axes as geographic directions or metres.

Default fitting uses the full unfiltered scene's extent, including interior exterior cards and road bends, plus padding for visible glyphs and labels. Hiding a layer does not move the camera. Missing room layout entries use the existing deterministic fallback positions; capture never persists a fallback or runs the arrange command.

Explicit bounds select a minimum visible extent. Keep a uniform scale and the requested centre. Expand the narrower axis to match the image aspect ratio; never stretch the map or crop any part of the requested extent. Return the expanded extent. Explicit bounds may extend beyond the map and may intentionally contain no objects. No automatic recentering or clamping occurs.

Rendering clips at the image edge. In a tightly bounded regional view, labels or cards extending beyond that edge can be clipped; agents can request a larger extent. Default full-map fitting must accommodate the map's visible cards and labels.

## 4. Layers and visual content

All applicable layers, including footprint and labels, are enabled unless listed in `--hide`.

| View | Layer key | Content |
| --- | --- | --- |
| Continent | `terrain` | Mainland, terrain/passability raster, forest edge |
| Continent | `water` | Waterways |
| Continent | `ridge` | Ridge walls, passes, fords |
| Continent | `locations` | Locations and reserved harbour sites |
| Continent | `footprint` | Settlement wilderness footprints |
| Continent | `partition` | Derived national boundaries and district outlines |
| Settlement | `nodes` | Street nodes, including existing gate glyphs |
| Settlement | `roads` | Authored directed roads and bends as drawn by the shared renderer |
| Interior | `rooms` | Room cards |
| Interior | `connections` | Within-interior connections and their existing direction indicators |
| Interior | `exterior` | Existing exterior doorway card and its link |
| All | `labels` | Object names, IDs, and connection text normally drawn on the map |

Hiding a geometry layer also hides its labels. Hiding `labels` preserves glyph/card geometry and connection direction indicators. Geometry layers are independent; hiding nodes or rooms does not implicitly hide roads or connections. Hiding all layers is allowed and produces the map background at the same camera.

Use existing editor map colors, glyphs, and local fonts. Retain existing connection topology and label content. This change does not add currently undrawn relationships, new road arrows, or new geographical information.

Exclude header, navigation, inspector, diagnostics strip, tools, zoom controls, frame/status pills, selection highlights, control points, hover effects, and focus rings. The image is the map surface alone. The normal map background remains; coordinate units and capture metadata are reported outside the image. No metric scale or north indicator is invented for interiors.

## 5. Loading and derived artifacts

Read current disk sources once for the invocation, through existing confined source discovery, YAML loading, layout projection, and terrain preview logic. Do not instantiate `EditorService`, its watcher, command writer, or application lifespan just to obtain a snapshot. Reuse or extract its pure read/projection boundary as needed.

Structural source or layout failures prevent capture; never silently replace malformed authored layouts with fallback placement. Loadable semantic work in progress can still be visualized. Include its diagnostics in the result and do not describe a successful capture as game-ready validation. A missing or stale external-reference index does not prevent viewing and does not authorize editing or deletion.

Partition requirements apply only to a continent capture where `partition` is visible. Read the existing artifact through the shared decoder and check freshness against the loaded world's partition signature. Missing, malformed, or stale output fails with instructions to regenerate it explicitly or use `--hide partition`. Do not draw outdated boundaries as current.

A hidden partition, or a settlement/interior view, does not require a valid partition artifact. Do not regenerate the artifact, write the reference index, or require game startup. Terrain preview still derives from the current source through the existing core, independently of partition visibility.

## 6. Execution and output

Execution is a one-shot pipeline:

1. Validate the invocation and read the source snapshot.
2. Resolve the requested map, visible scene, coordinate frame, and camera.
3. Load the local map-only bundle in a disposable headless browser and pass the payload.
4. Wait for the map render, local fonts, terrain image, and layout to finish. Use an explicit ready signal and a bounded wait rather than a fixed sleep.
5. Capture exactly the map rectangle, encode the chosen image format, and publish the output file.
6. Close the browser and remove temporary capture assets on success or failure.
7. Emit one success JSON object on standard output. Diagnostics and failures must not contaminate the success JSON stream.

The success object contains `image_path` (absolute), `view`, `map_id` (null for continent), `format`, `width`, `height`, `bounds`, `units`, `axes`, `hidden_layers`, and `diagnostics`. Bounds use the same ordered four-number representation and coordinate frame as the input. Units are `km`, `m`, or `layout`; axes distinguish north-up geography from down-positive interior layout. Hidden layers are normalized and deduplicated. No timestamps or session IDs are needed.

Exit code 0 means image production succeeded, not that game-adoption validation passed. Use nonzero exits with a short diagnostic on standard error for invalid arguments, unreadable sources, unavailable partition, missing dependencies/build/browser, render timeout, encoding failure, or output failure. No success object is emitted on failure.

The skill directs a vision-capable agent to read `image_path` with its image-reading tool after capture. Never claim visual inspection from a successful subprocess alone. If its tool cannot read WebP, the agent explicitly reruns with `--format png`; the capture command does not silently change format.

## 7. Image size and vision support

The default is lossless WebP, with PNG available for tool compatibility. OpenAI's [image-input documentation](https://developers.openai.com/api/docs/guides/images-vision#image-input-requirements) lists PNG, JPEG, WebP, and non-animated GIF; it does not list AVIF. Other agents and tool wrappers can have different support, so actual WebP reading is an acceptance check.

Compressed byte size and image token use are different measurements. Token accounting depends on the model's processed dimensions and detail mode. The skill must not promise fewer tokens merely from WebP encoding. Recommend an overview at an appropriate resolution followed by a targeted regional view when small labels need inspection. Do not lower image quality to claim token savings or automatically produce extra images.

## 8. Verification and documentation acceptance

Implementation must establish these behaviors through focused checks and actual rendered images:

- Capture all three views from deterministic synthetic source data. Verify the correct map, coordinate orientation, road bends, room layout/fallback, and exterior-card placement.
- Exercise explicit regional bounds with differing aspect ratios. Verify uniform scale, requested-extent containment, reported expanded bounds, exact pixel dimensions, and interior Y conversion.
- Exercise each layer's substantive visibility behavior. Check labels independently, camera stability when hiding layers, all-layers-visible defaults, and rejection of cross-view/unknown names.
- Exercise missing, malformed, and stale partition output with partition visible; confirm hiding it permits a continent capture and it does not block settlement/interior capture.
- Exercise malformed sources/layouts, missing IDs, invalid bounds/sizes, missing runtime assets, and output failure. Failure cannot publish a partial image or report an old image as success.
- Launch the real one-shot command with no editor service running, render representative repository maps for every view, and read the resulting images. Inspect map-only composition, readable Traditional Chinese labels, correct geography/topology, and absence of editor chrome.
- Produce and actually read lossless WebP and PNG. Measure byte sizes only if reporting a size comparison; do not assert WebP is always smaller or claim a token reduction without model-specific evidence.
- Confirm source YAML, layouts, partition, and reference index remain untouched by capture. Temporary assets and the browser must be cleaned up after normal completion and rendering failure.
- Smoke the interactive editor after any shared map-surface extraction to preserve its map display and interactions.

Permanent tests target consumer-visible rendering, boundaries, and errors, not copies of help text, source layout, or forwarding calls. Follow existing synthetic fixture, shard ownership, focused-run, and traceability rules. Browser registration applies to any new managed browser tests. Full managed browser runs remain CI-owned.

Update the existing skill and its relevant references with command setup, examples, the complete layer/parameter tables, coordinate conventions, partition refusal, and the capture-then-read workflow. Update existing map-editor developer documentation for the shared offline render entry and developer dependencies. No player command documentation changes are needed because no player command changes.

Before implementation handoff, run focused behavior checks and the repository contract gate. Design-only delivery validates the document and runs the contract gate without claiming capture runtime verification.

## 9. Review and implementation transition

This document is the design deliverable, not an implementation plan or an implemented feature. Obtain user review of this written specification before planning implementation. Subsequent planning must respect the repository's specification-driven workflow and preserve every approved view, parameter, and acceptance condition.
