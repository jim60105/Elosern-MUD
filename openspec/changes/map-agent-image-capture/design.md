# Design

## Context

See `proposal.md` for motivation. The complete approved contract is `docs/superpowers/specs/2026-10-29-map-agent-image-capture-design.md`; engine ownership follows the approved `2026-07-29-ai-mud-engine-design.md`. This change composes the completed `map-capture-snapshot` and `map-offline-render-surface` prerequisites. Their snapshot and local-entry contracts are fixed below and must not be replaced with another loader or drawing implementation.

Observed tooling anchors:

- The skill currently has `check_map_sources.py` and `regenerate_partition.py`, launched through uv-managed package projects. Its source/reference tables own authoring instructions.
- `tools/map-editor/pyproject.toml` and `uv.lock` provide an independent Python environment with a local map-core dependency. The root game environment already has browser-test infrastructure, but is not the capture runtime owner.
- The editor frontend is built with its own pnpm lock and Vite; the surface prerequisite provides a dedicated classic local-file bundle at `tools/map-editor/frontend/capture-dist/index.html` and `build:capture`.
- Root `tests/` and managed `web/tests/browser/` contain discoverable real-tool evidence patterns and requirement decorators. Keep new managed methods in `.github/browser-shards.json`; test modules under Evennia-owned roots require exact `.github/evennia-shards.json` ownership if added there.

## Goals / Non-Goals

**Goals:** One documented command invocation produces one exact-size map-only image, publishes atomically and reports machine-readable provenance/camera data. Complete skill guidance includes successful capture followed by actual image reading.

**Non-Goals:** Source edits/generation, game services, EditorService, browser-session discovery/synchronization, editor API or HTTP server, file watching/history, player knowledge/game state, batch images, interactive controls, AVIF/JPEG, quality knobs or token-savings claims. No migration or compatibility shim.

## Decisions

### Runtime and dependency ownership

Add `.agents/skills/map-data-authoring/scripts/capture_map.py` as the thin command entry; reusable orchestration belongs to proposed `tools/map-editor/elosern_map_editor/capture.py`. Add optional developer dependency group `capture` containing Playwright and Pillow using `uv add --group capture --project tools/map-editor ...`, with its project lock updated by uv. Do not change root game runtime dependencies. Pillow must have WebP support; check it explicitly and fail with setup guidance when absent.

Document setup separately from execution:

```console
uv sync --locked --project tools/map-editor --group capture
uv run --locked --project tools/map-editor --group capture playwright install chromium
pnpm --dir tools/map-editor/frontend install --frozen-lockfile
pnpm --dir tools/map-editor/frontend run build:capture
```

Canonical runtime from the source workspace root:

```console
uv run --locked --no-sync --project tools/map-editor --group capture python .agents/skills/map-data-authoring/scripts/capture_map.py --view continent --output /tmp/continent.webp
```

`--no-sync` keeps runtime from automatically installing dependencies; missing environment/build/browser/codec produces actionable stderr. Runtime uses neither a pnpm process nor a server. Code/assets resolve from the installed checkout; the current working directory supplies authored sources and relative output. Reject service URL arguments. Locked setup and browser installation are explicit operator actions.

### CLI contract

Use strict argument parsing with no abbreviation and no `--show`. Resolve identity through the loaded projection; document reading source documents to find IDs rather than adding a list API.

| Argument | Accepted values and defaults |
| --- | --- |
| --view | required continent, settlement or interior |
| --map | required settlement/interior document ID; forbidden for continent |
| --bounds | optional MIN_X MIN_Y MAX_X MAX_Y, all finite and axes strictly increasing; absent means full fit |
| --width / --height | positive integer pixels; 1280 / 960 |
| --hide | repeatable LAYER [LAYER ...], deduplicate and sort output names; all applicable layers visible by default |
| --format | webp default, or png; both lossless |
| --output | required path, relative to cwd or absolute, matching selected format extension and existing parent |

Accept `.webp` and `.png` suffixes case-insensitively against normalized format; do not infer format from suffix. This minor spelling policy adds no format. Reject unknown flags/layers, other-view layers, absent/wrong map IDs, non-finite or degenerate bounds, fractional/nonpositive dimensions, missing parent, mismatched extension and unsupported formats. Python-side argument validation precedes browser launch and output publication.

| View | Applicable hide names | Input and result coordinates |
| --- | --- | --- |
| continent | terrain, water, ridge, locations, footprint, partition, labels | km, x east/y north |
| settlement | nodes, roads, labels | authored local m, x east/y north |
| interior | rooms, connections, exterior, labels | layout, x right/y down |

The skill must explain each layer's contents using the full table in the approved design, including forest edge, passability raster, harbours, gate glyphs, road bends, connection indicators and exterior link. Geometry hides its own text; labels hide text without removing glyphs/cards/direction indicators. Nodes/rooms do not implicitly hide links. All-hidden remains valid and preserves camera.

### One-shot browser lifecycle and structured handoff

1. Validate arguments/output location and runtime availability; load sources exactly once using `load_capture_snapshot(cwd, view=..., map_id=..., hidden_layers=...)`.
2. Receive `{world,partition,diagnostics}`. Open a fresh local Chromium browser/context with viewport width/height and device scale factor 1. Deny HTTP/HTTPS/WebSocket traffic; no connection to an operator browser or API session.
3. Navigate to the local built capture entry and invoke fixed `window.renderMapCapture(payload)` with structured browser-evaluation arguments `{world,partition,view,map_id,width,height,bounds,hidden_layers}`. Do not interpolate authored data into executable JS or HTML.
4. Await its promise under a finite render deadline covering fonts, terrain image decode, layout and paint. Reject explicit entry errors and timeouts; do not use fixed sleeps or capture before readiness.
5. Capture exactly the map host rectangle as PNG pixels, encode the selected format with Pillow (`lossless=True` for WebP; PNG lossless), publish output, then emit JSON. Browser automation screenshot WebP defaults are not used as a losslessness claim.
6. Context-managed teardown closes page/context/browser/Playwright and removes temporary capture/output assets on normal and exceptional paths. No browser or process may survive a rendering failure.

The entry returns `{bounds,units,axes}`. Bounds are expanded to aspect ratio in the CLI frame, not reconstructed from requested bounds. Axes objects are `{x:"east",y:"north"}` or `{x:"right",y:"down"}`. The frontend owns kilometre/metre conversion and interior Y inversion, including noninteger bounds. Hide filtering must not alter its unfiltered fit camera.

### Atomic output and result semantics

Capture/encode to memory or private temporary assets. Write the complete encoded bytes to a sibling temporary file in the output directory, close successfully and publish with atomic replacement. Destination replacement is the final file operation that can fail. Never truncate the destination on startup, unlink an existing image as cleanup, or print a result for an old image. Remove sibling temp files on any failure. Same-directory staging avoids cross-filesystem rename behavior.

Serialize the complete success payload before publication so JSON serialization cannot fail after replacing the destination. The one stdout object contains exactly `image_path` (absolute), `view`, `map_id` (null for continent), `format`, `width`, `height`, `bounds`, `units`, `axes`, `hidden_layers` (sorted unique names) and `diagnostics`. No timestamps or session IDs. Route runtime chatter/diagnostics to stderr; source diagnostics also remain in successful structured metadata. Exit 0 establishes image production, never game readiness or visual inspection. Invalid arguments and operational errors exit nonzero with short actionable stderr and no success object.

### Documentation and human review

Update `.agents/skills/map-data-authoring/SKILL.md` and its existing domain/verification references, keeping one authoritative full command/layer reference reachable from the skill. Include defaults/units and examples for every view, regional bounds of differing aspect ratios, multiple hidden layers and PNG. Explain missing/stale/malformed visible partition refusal, explicit regeneration or hiding, missing layout fallback versus malformed layout failure, semantic work-in-progress diagnostics, matching suffixes, replacement semantics and dependency/build/browser setup.

Tell agents to read successful `image_path` using their image-reading tool. If WebP cannot be read, explicitly rerun with `--format png` and a PNG path; no silent conversion. Recommend overview resolution followed by a targeted region for small labels, without generating extra images automatically. Never promise token savings from compressed bytes, claim WebP is always smaller, or lower quality for such claims. Measure bytes if reporting a format comparison and require model-specific evidence for token statements.

Update `docs/development/map-editor.md` with shared offline render/loader ownership, setup, focused checks and a capture review section. Record actual image commands and inspected results for every view and both formats there during implementation. Human judgment of typography, Traditional Chinese readability, map composition and skill prose quality belongs in that review, not requirements with data/copy/markup-pinning tests. No player-command docs change is needed.

## Risks / Trade-offs

- Browser dependencies belong to developer tooling and may be absent. Detect environment, Chromium, built assets and WebP codec support early with explicit setup instructions.
- Successful subprocess execution cannot establish actual vision-tool support. Read representative WebP and PNG files and record whether the tool decoded them; rerun PNG explicitly if needed.
- Output replacement must survive encoding/write failures. Fault-inject before publication with a pre-existing synthetic image and compare its bytes after failure.
- Shared files can conflict across slices. Surface owns frontend/build, snapshot owns loader, command owns Python capture dependency group/lock; serialize documentation and browser ownership integration.

## Verification and requirement evidence

| Requirement | Discoverable behavior evidence planned |
| --- | --- |
| Capture invocation selects exactly one validated map view | `tests/test_map_image_capture.py` subprocess cases for required identity, exact defaults, all input/path failures and repeatable hide normalization |
| Capture publishes exact lossless images atomically | same module, real synthetic raster decode comparison at requested size plus encoding/write/replace fault cases preserving an existing image |
| Successful capture reports one structured result | same module, parse the sole stdout object, check actual decoded image, expanded bounds in every frame and semantic diagnostics |
| One shot capture closes resources and isolates failures | same module and `web/tests/browser/test_map_image_capture.py`, real local bundle, blocked networking, delayed readiness/timeout, no service, teardown and unchanged file digests |

Use adjacent package tests for isolated helpers and root discoverable tests for substantive traced behavior. Resolve canonical IDs using `tools.spec_traceability list` on an equivalent merged spec tree before archive; while active record only meaningful provisional nearest-current associations/reasons. Never hand-compose identifiers or use forwarding/help-text/fixture-copy tests. Register every new managed browser method; if a test lands in an Evennia-owned path register its exact shard ownership too. Full browser/evidence verification stays CI-owned.

Implementation local gates are the focused command module, one affected browser class, existing editor smoke after shared extraction, strict OpenSpec validation and repository contract gate. Actual acceptance includes real synthetic three-view captures (coordinates, bends, layout/fallback/exterior), bounds/aspect/dimensions, every layer, partition matrix, malformed input/runtime/output failures, cleanup and read-only digests. Final repository-map smoke launches the real command with no editor service for every view and actually reads both formats. Do not regenerate a stale repository partition merely to make smoke pass; explicitly hide it and separately establish fresh partition rendering with synthetic data.

## Migration Plan

Apply only after both completed prerequisite changes. Introduce the complete command, locked capture dependencies and skill documentation together; no incomplete public entry, flags, stubs or compatibility aliases. No authored data or database migration. The approved design document remains untouched. Reverting this developer tool does not alter maps or game state.
