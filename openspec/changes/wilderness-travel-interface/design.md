# Design

## Context

Existing owners are AppClient.vue (slot composition), components/HudFrame.vue (anchor geometry), composables/use-map-drawer.js (on-demand maps), stores/elosern/view.js (committed projection), stores/elosern.js (public facade), components/CompanionLineup.vue and AvatarArtwork.vue (identity/art projection). All frontend paths below are relative to web/webclient-app/. Server status.py currently emits schema4 fatigue rows; world/rules/status_query/fatigue.py reads exact physiology without materializing it. Logical wilderness identity is already art.scene.artwork.subject_id, produced by world/maps/room_art.py::wilderness_scene_identity; there is no separate room panel.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Select the wilderness presentation, remap HUD slots, refresh the live area map and show committed party medallions without waiting for sight rules.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Committed selection and shell
Add stores/elosern/travel.js::applyTravel(ctx), called by the composed store, and components/travel/travel-model.js pure projections. Publish view.travel = {mode, layout, room, map, mapReady}; room is {subject_id} projected from the committed available art.scene.artwork descriptor. mode is rs.mode === "exploration" && room.subject_id.startsWith("wilderness:"). layout is mode && no active committed dialogue panel && no existing combat/dream/creation surface. Dialogue currently also uses its committed panel, so do not wait for a nonexistent server "travel" mode or force dialogue mode into the reducer. A missing room descriptor disables travel selection; no prose, local click or cached scene can select it. Dialogue/combat use existing region art and actor composition and return to travel on exit.

In AppClient remap backdrop to TravelMap, vitals to existing StatusPanel above PartyMedallions, map to unchanged PlaceCard, presence to unchanged same-cell PresenceRail, choices to existing event-card host, band-message to existing MessageWindow until log-ui, band-command to existing movement controls until walking/leg-ui. Both actor anchors are empty only while travel.layout. Add a travel presentation prop/data hook to HudFrame, never change its mode enum. TravelMap.vue initially wraps the existing AreaMapView using decoded current-protocol data; it is a working map before map-ui replaces its drawing surface. Travel is full-bleed, lighter vignette, existing two-thirds/one-third band. Live enter/leave crossfades use --motion-scene; off commits in the same frame; outgoing visual copies are inert. No new standing portraits in medallions.

### Current-protocol adapter and refresh owner
Add lib/travel-grid.js::decodeTravelGrid(area) returning {mapId,frame,currentNode,origin:{x,y},width,height,cells,party,lightPhase:null,groundRadius:null,entities:[],sightings:[]}. Cells are row-major south-to-north, each {x,y,known,terrain,band:null,tier:null,road:false,ford:false,node:null,display:null}; party is the committed current node's coordinates. Today's wilderness area_map is already the schema-2 41x41 run-length window (wilderness-area-map-reveal has landed since this proposal), so the adapter reads it through the existing lib/area_map_view.js decodeWindow helper rather than a node-form decoder, emitting a full row-major grid with known only on revealed terrain runs and keeping band/tier/road/ford/display, lightPhase, groundRadius, entities and sightings at the shape's empty values until window-ui supplies them, keeping action/gateway identity verbatim and treating absent positions as unknown. Terrain comes only from an explicit canonical field; a label is not parsed into terrain. Missing terrain uses an untextured known-cell wash, never guessed elevation, phase, reveal radius or passability. This is the explicitly approved temporary adapter, not a wire-version compatibility decoder. Window-ui replaces and deletes it at the schema2/3 cutover.

Add composables/use-travel-map.js as the sole active-stage area request owner. While travel.layout, request map.view {scope:"area"} on entry and after each committed canonical current-node/time change or completed room look, even with the drawer closed. Coalesce changes into one pending latest refresh, send only through store.dispatchAction when the one dispatch lock is free, and never refresh from aim, hover, resize, render or failed movement. Correlate requestId, generation, epoch, frame and publication revision using useMapDrawer's result/body ordering pattern. Publish mapStatus as ready|refreshing|unavailable|invalid|retired, with mapReady true only at ready. A matching complete available response sets ready. A committed step or ordinary map refresh sets refreshing, retains the last committed map dimmed and disables new movement controls while keeping Stop usable; it suspends the queue rather than cancelling it. First load shows hatched fog. An unavailable response sets unavailable, unreadable data sets invalid and an epoch/frame retirement sets retired; these states stop a walk. Record accepted external full snapshots and explicit-sync completions at the transport acceptance seam, including unchanged position/time, and schedule exactly one area refresh for each accepted recovery publication. Deduplicate by its generation/epoch/publication identity; tracked map.view completion publications never recursively trigger refresh. Failed map reads stay disabled until such an external snapshot, explicit sync or another normal committed refresh cause, with no polling/retry loop. Old-epoch maps are discarded. Drawer requests stay drawer-owned; it never issues area requests in travel, and travel refresh pauses while a modal/drawer owns input. Clarify the existing closed-map contract as drawer-only.

### Medallions and bounded sleep fact
PartyMedallions.vue reuses current controlled/party identity projection and AvatarArtwork with committed portrait_ref, no URL construction. Include controlled body once, then present companions in existing party order, excluding absent members. Join string-normalized identities to status.fatigue, never use owner resources as a possessed body's reserve. Show name, supplied reserve_percent, 70/40/20 percent notches, supplied stage label when non-normal, controlled ring and sleep crescent; saturation/brightness and label supplement colour. Accessible name includes member name, reserve percentage and supplied stage label. Missing physiology shows unavailable, never 100%.

Extend status read-model fatigue membership through travel_cost.source_present_members so every present traveller has its own row; deduplicate owner/controlled identities and keep unrelated owner resources unchanged. Extend FatigueSubjectView and _fatigue_entry with asleep:boolean from canonical SleepPosture, including forced sleep. Clean status schema4->5 on Python/JS registered available/unavailable forms; no migration/dual schema. Existing resources/conditions/possession authority stay unchanged. This field supports presentation only.

MapDrawer gets travelMode prop. Its allowed tabs become world-only in travel, keyboard shortcut 1 cannot select a hidden area tab, an already-open area tab coerces to world, and leaving travel restores ordinary per-layer choice and frame-scoped area memory. Keep world discovery readiness unchanged.

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

## Blocking review disposition

B2 adopted. Explicit ready/refreshing/failure states separate normal queue suspension from cancellation; accepted same-position snapshot/sync schedules one non-recursive area recovery request. All six blocking findings were addressed across the batch; no requirement was replaced with human-judged copy/appearance evidence. This records remediation, not an unperformed second review.

## Migration Plan

Pre-release clean cutover. No database migration, compatibility aliases or alternative wire schemas. The requested temporary node-grid adapter exists only until window-ui replaces it with the shared validated RLE decoder. Rollback is source reversal of the slice and its dependent slices together. Do not apply, sync or archive in the proposal workflow. Update existing developer guidance and control reference during implementation; these proposal artifacts are the requested documentation deliverable now.


## Requirement-to-evidence mapping

| Requirement | Discoverable mechanism evidence to implement |
| --- | --- |
| Wilderness presentation follows committed room identity | TravelLayoutTests.test_settlement_gate_layout |
| Travel area refresh follows committed state | TravelLayoutTests.test_refresh_adoption |
| Medallions identify committed physiological subjects | TravelLayoutTests.test_medallion_subjects |

Focused accompanying tests: tests/travel/{layout,grid,refresh,medallions}.test.js; web.webclient.presentation.tests.test_status_panel; TravelLayoutTests.test_settlement_gate_layout.
