# Design

## Context

TravelMap.vue is the working stage wrapper introduced by the base change. Existing lib/area_map_view.js and AreaMapView.vue remain the drawer renderer; do not redesign them. The approved prototype supplies appearance only. lib/travel-grid.js is the single cell-grid input. Shared glyph sources are MapNodeGlyph.vue, WorldMapGlyph.vue, WorldHatchPattern.vue and styles/area-map-ink.css; the band ornament is shared HUD chrome.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Paint the production ink map from committed decoded cells, with independent overlays, follow camera and zoom.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Drawing contract
Replace the wrapper's area drawing with components/travel/TravelMap.vue plus lib/travel-paint.js::paintTravelMap(ctx, grid, {samplesPerCell:12}) and lib/travel-camera.js::{followCamera,fitRouteCamera,projectSightings}. Painting is deterministic from grid facts and world-coordinate cosmetic noise. No import from docs/design/wilderness-travel/travel-model.js. No world-sized allocation. Cache sample fields in typed arrays per map/frame and content signature, at twelve samples per cell, canvas dimensions grid.width*12 by grid.height*12; CSS transforms scale it. Reuse buffers while dimensions agree. A world-coordinate avalanche hash produces texture only, never factual elevations, terrain, sight or entities. New map content, reveal/light/party sight changes repaint once, coalesced per animation frame; aim/hover, route/progress, camera/zoom and chip geometry update overlays/transforms only. An arbitrary view publish does not invalidate painting.

Implement interface design §4.2 passes in order. Bilinear elevation uses supplied band; absent bands produce flat neutral shading. NW hillshade, band-change contours with every third band darker, warped terrain lookup, umber/ochre/moss/slate palette. Bilinear reveal mask with deterministic jitter and pooled-dark edge keeps unknown pixels transparent against the one root hatch. Roads/rivers connect adjacent explicitly flagged cells via Chaikin smoothing (river bank/body/current and road dark/gold dash); woods get three deterministic conifer dabs, ford stones, prominence local-max rings with stable tie resolution, dotted district edges and settlement footprint walls only where display facts exist, faint grid only in supplied live sight. All strokes clip to the reveal mask. Memory desaturation and phase washes use source-atop; night moonlit disc uses supplied radius. Copy phase-look starting values from approved interface §4.2 into one cosmetic constant, with human tuning permitted. Missing adapter fields suppress their decoration; no fabricated river, district, light phase or sight ring. Window-ui later supplies them.

### Overlay and shared glyph ownership
SVG holds live-sight dashed ring, party travel-state red/gold seal, eight neighbour targets, aimed fill/highlight, landmark ornament diamonds, live hostile seals/halos, bearing rays and hover outline (dashed for unknown). HTML holds names, hostile count/threat when supplied, ford/aim/hover labels, distant cards, north and 5km scale. Route rendering is added by planning-ui. Reuse or extend existing shared glyph definitions with named travel states; TravelMap must not copy a current/gateway/landmark/commission glyph. Add travel-party state to MapNodeGlyph and a shared travel ornament renderer under components/travel/TravelGlyph.vue for new neighbour/hostile/route concepts. One source owns each concept/state; existing drawer/minimap states remain unchanged. This explicitly extends the shared glyph contract rather than privately redrawing the same state.

### Camera and measurements
TravelMap props are {grid,aim:null,walking:null,plan:null,locked:false,motionLevel,uiScale}; nullable props describe actual absence, not mock state. Expose focus() and emit {aim,hover,pick,step,confirm,cancel,hold,release,zoom} intents only. Read actual HudFrame header/band and medallion/place-card bounds through ResizeObserver, compute the open-stage rectangle, and disconnect observers on unmount. Follow camera centres the party between header and band; 380ms multiplied by --motion-travel governs glide and token halo stops at off. Zoom cellPx is 18..46 in increments4, default30, multiplied once by --ui-scale. Wheel and +/- clamp without repaint. fitRouteCamera includes party, full route and destination in the free rectangle between side columns, with minimum14*scale; walking always follows again. If the rectangle is too small to fit at minimum, retain minimum and clip to open stage without covering controls. projectSightings projects bearing-only rays from open-stage centre to its inset edge; it never fabricates a distant source coordinate. Inputs to it are the actual safe rectangle, cards and bearing, not prototype fixed pixel columns.

### Performance evidence
Add a browser benchmark helper used by the managed travel test, without production telemetry. Measure paintTravelMap only after warmup for20 state changes, record development hardware/browser/DPR and every sample at 1451x790 and2560x1440. Each repaint must be <=50ms. Count paint calls to prove camera/zoom/hover changes do not repaint. Keep any benchmark helper in tests, not a throwaway production script. Human review compares the seven required production story states to the approved visual reference; performance and cache invalidation have executable checks.

## Dependency contracts and overlap audit

| Existing active change inspected | Its owned behavior | Interface boundary |
| --- | --- | --- |
| wilderness-sight-rules | phase/radius policy, ground disc, current anonymous distant markers | consume policy/results after window-ui; no client sight formula |
| wilderness-ground-reveal | maximum observed sight, committed arrival/skip writes, bounded pure reveal | no new knowledge writer or storage; log hooks observe the existing transaction |
| wilderness-map-disclosure | eager local-map/exit anti-peek, nullable opaque directions, schema6 exploration | reuse committed control rows including null destinations; no alternate target inference |
| wilderness-area-map-reveal | schema2 RLE window, anti-peek, bounds/chunk transport, existing drawer decode | window-ui extracts/reuses its decoder and adds display-only schema3 metadata; never duplicates schema2 routing/reveal rules |
| wilderness-travel-planning | exact read-only query, admitted prediction, indices/errors, result-only completion | planning-ui consumes the exact result and owns debounce/currentness only |
| wilderness-travel-interrupts | optional walk union, commit-qualified seven flags, collector/Deferred result | route-ui consumes flags and composes event capture; never re-specifies server flag rules |


## Batch dependency/conflict matrix

| Order | Change | Direct prerequisites in this batch | Existing active prerequisites | Shared-code integration conflicts |
| --- | --- | --- | --- | --- |
| 1 | wilderness-travel-interface | none | none | AppClient, HudFrame, view/store, MapDrawer, status schema5, protocol/audits |
| 2 | wilderness-travel-map-ui | interface | none | TravelMap/shared glyphs, camera, stories/browser manifest; serialize after base |
| 3 | wilderness-travel-walking-ui | interface | none | travel store, input, AppClient; serialize with map-ui despite no build dependency |
| 4 | wilderness-travel-log-ui | interface | none | movement/clock/look publication, coordinator, protocol; serialize shared server files with ground-reveal/interrupts |
| 5 | wilderness-travel-leg-ui | walking-ui, log-ui | none | status schema6 after base5, travel_cost pure charge seam shared with planner, preferences, AppClient |
| 6 | wilderness-travel-window-ui | map-ui, log-ui | wilderness-area-map-reveal | area_map/schema3 after prerequisite2, shared decoder, travel events; serialize after map-disclosure/ground-reveal transitively |
| 7 | wilderness-travel-planning-ui | leg-ui, window-ui | wilderness-travel-planning | travel store, input, result validators, route overlays; no server routing edits |
| 8 | wilderness-travel-route-ui | planning-ui | wilderness-travel-interrupts | activateExit, travel queue, choices, collector integration and events; no server interrupt-rule edits |

The displayed order is a safe serialized implementation order, not eight artificial build edges. Map-ui, walking-ui and log-ui share a base but can start independently with one integration owner for shared AppClient/store/docs/manifests. Every server/browser test-manifest and protocol-audit edit is serialized. Window consumes area-map-reveal, which transitively depends on sight-rules, ground-reveal and map-disclosure. Planning additionally consumes travel-planning; route additionally consumes travel-interrupts. Log-ui and leg-ui have shared-code conflicts with ground-reveal and planning/interrupts but no requirement on their not-yet-applied rules. Reuse any already-landed pure helper instead of creating a second one.


## One-day implementation boundary

Eight-hour envelope: 2h core mechanism, 2h consumer integration, 2h focused mechanism evidence, 1h existing docs/traceability and 1h integration allowance. Reuse the named existing helpers; do not expand into a new rules subsystem.

## Evidence and requirement shape

Every new requirement is a mechanism/state-transition contract with a body below500 characters. Appearance, copy, tone and visual-reference fidelity are human-reviewed against [the approved interface design](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-interface-design.md) and `docs/design/wilderness-travel/`, rather than tested as wording, markup or shipped-data snapshots. Numeric motion/input/size/performance bounds are executable behavior. Tests use synthetic payloads/policies with independent expected outcomes; no test pins the shipped world, names, counts or prose. Existing copied MODIFIED scenarios retain their semantics under the explicit travel/non-travel scope.

Obtain canonical IDs through tools.spec_traceability list on the equivalent merged spec tree, using the exact command in docs/development/spec-test-traceability.md. Never hand-compose IDs or add uncovered main requirements. Before sync, use nearest existing canonical requirements (webclient-contextual-hud for shell/log, webclient-map-drawer for rendering, webclient-exit-compass for inputs/queue, webclient-status-presentation for capacity/medallions, webclient-action-dispatch for request correlation), record each temporary association, and remount generated IDs on sync. The named Python browser/server tests below are discoverable requirement evidence; Vitest alone does not satisfy this project's Python traceability gate. Add substantive assertions, not screenshot-only or skipped tests. Existing MODIFIED requirements retain IDs and their earlier test coverage.

All commands run from repository root. Focused frontend command is `pnpm test -- <test-path>`; server labels use the exact root AGENTS.md focused runner and an approved environment file. Browser methods use the exact managed unittest_driver invocation in AGENTS.md with the full dotted label web.tests.browser.test_wilderness_travel.<Class>.<method>. Register every new server module in exactly one .github/evennia-shards.json shard and every new browser method in exactly one .github/browser-shards.json shard. Unmount AppClient between suites. Run focused checks after the slice is complete, not while another worker edits shared owners. Production showcase uses `pnpm run build-storybook && pnpm run showcase-coverage`.

## Risks / Trade-offs

[Shared exact schemas] -> apply the cumulative deltas in dependency/conflict order and update both validators, fixtures, registrations and protocol documentation together. Observed runtime status4 supersedes stale main-spec version3 wording; base deliberately cuts to5 and leg to6, preserving physiological identity and all non-travel semantics. [Prototype rules] -> production imports only real protocol data and existing deterministic helpers. [Asynchronous commits] -> match request, epoch and committed revision before queue progress or current-map adoption. [One engineer-day] -> each slice owns one runnable vertical behavior, with focused evidence/docs included; no offline rules/camping work is hidden in a task.

## Migration Plan

Pre-release clean cutover. No database migration, compatibility aliases or alternative wire schemas. The requested temporary node-grid adapter exists only until window-ui replaces it with the shared validated RLE decoder. Rollback is source reversal of the slice and its dependent slices together. Do not apply, sync or archive in the proposal workflow. Update existing developer guidance and control reference during implementation; these proposal artifacts are the requested documentation deliverable now.


## Requirement-to-evidence mapping

| Requirement | Discoverable mechanism evidence to implement |
| --- | --- |
| Travel painting uses disclosed cell facts | TravelMapTests.test_repaint_budget / test_map_fact_layers |
| Travel camera preserves the open stage | TravelMapTests.test_map_viewports |

Focused accompanying tests: tests/travel/{paint,camera}.test.js; TravelMapTests.{test_repaint_budget,test_map_viewports}.
