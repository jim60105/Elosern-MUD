# Design

## Context

wilderness-area-map-reveal owns schema2 rows, unknown runs, sparse nodes, bounded transport, the shared lib/area_map_view.js decoder and existing AreaMapView cutover. wilderness-sight-rules/ground-reveal/map-disclosure own all visibility and disclosure decisions. This slice consumes those results; it does not redefine radii, permanent reveal, distant ranges, hidden entries or population. The base temporary adapter must be removed, not retained as a second wire version.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Replace the temporary node adapter with the shared run-length decoder and display live sight, phase tint and disclosed annotations.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Shared decoder cutover
Refactor the schema2 decoder already introduced by area-map-reveal into lib/wilderness-grid.js::decodeWildernessGrid(area), used by both lib/area_map_view.js and lib/travel-grid.js. Preserve its row totals, integer/enum/bool bounds, exact unknown-run rejection and south-to-north origin convention. TravelGrid shape remains base design's shape; band/tier/flags now come directly from rows, phase/radius/entities/sightings from committed window. Remove the node15 implementation and its fixtures/imports. Do not accept schema1 wilderness at this point; map schema2->3 below is a clean cutover across server and both consumers, with no alternate decoder. Unknown cells contain no fabricated metadata. The ordinary drawer remains otherwise unchanged, including non-wilderness graphs and canonical adjacent actions. Existing live-stage map.view refresh stays on-demand; do not push area maps on movement or enlarge generic frame limits.

### Display-only additions missing from schema2
The approved appearance needs district edges, settlement walls, terrain/ford labels, landmark names and hostile count/threat; none is fully represented by schema2's exact terrain run/entity shape. Add them as a schema3 presentation-only extension, using the exact already-revealed predicate before reading any display metadata. Do not add rule functions to sub-project1 or send hidden identities.

Revealed run exact fields are the schema2 fields plus display:{terrain_label,district_key,district_name,settlement,ford_label}. terrain_label and district_name are bounded nonblank<=256 strings; district_key is nullable bounded ASCII<=128 with district_name nullable together; settlement:boolean identifies a disclosed non-hidden footprint; ford_label is nullable bounded<=256. Unknown runs stay exactly {length,kind:"unknown"}. Display values participate in adjacent-run equality. Draw a district edge only between two disclosed cells whose non-null keys differ; walls follow disclosed settlement footprint edges only, never continue into unknown space. Labels select registered canonical display names, never guess from terrain enums/coordinates. Ford uses its permitted authored label, or a server-owned generic terrain label when no proper name exists.

Sparse nodes keep their current shape plus landmark:null|{name}, name nonblank<=256, emitted only for permitted actual landmark metadata. Current/visited-only ordinary nodes keep landmark:null. Entities keep schema2 fields plus count:positive safe integer and threat:null|string<=128; currently each entity observation has count1, never group unknown entities or infer threat from HP. Prospective population threat comes from its canonical expected variant tier, materialized entities from resolve_individual_tier/individual_danger_grade. Nullable unavailable threat shows an explicit unknown-threat label, never a guessed grade. Map cap remains393216 UTF8 bytes; over-bound maps use existing unavailable handling. Update schema constants, Python/JS exact validators, common map fixtures and shared decoder in one cutover; other-layer field shapes are unchanged.

### Current observations and chips
Feed painter and overlay only after a correlated complete current window; stale/unreadable retains last dimmed committed bitmap and disables LegPanel and all map actions until a valid next snapshot refresh. Light phase and ground radius are authoritative; do not compute phase from hour or radius from terrain. PlaceCard label comes from current run district_name and terrain_label, and its time line includes the supplied light phase. Reuse existing server time formatting. Memory/light/night disc use interface §4.2 cosmetic constants. Live hostiles get label/count/supplied threat and halo; landmarks get the shared ornament plus supplied name; ford/aim/hover readouts use permitted labels, unknown says 未探明. Distant markers have only bearing,distance_km,silhouette_zh,name, so project cards/rays by bearing from measured open-stage centre and never manufacture source coordinates or hidden names. Canopy/night filtering remains the server's job.

### Complete sight/phase event producers
Replace log-ui's limited current-view sight comparison with immutable before/after observations read from the same sight/population functions consumed by area-map-reveal. Compare internal observation/source identities before serialization, then render only allowed parameters. Emit hostile_sighted and landmark_sighted for newly present canonical observations, preserving optional anonymous landmark names; no permanent sighting memory. Reuse the capture boundary if interrupts has already landed; if it has not, keep log event capture in travel_events and route-ui later reuses it when composing the interrupt collector, without changing interrupt ownership. Internal source keys never reach events or browser data. Dusk/nightfall events use sight.light_phase and interval boundary enumeration over a positive committed charged step/skip, so same-phase endpoints spanning a boundary still produce its event; zero-charge steps produce none. Multiple transitions in a skip keep chronological order. Existing fatigue/region/woodland/ford/look producers remain. No new interrupt flag or threshold rule is defined here.

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
| Travel consumes the shared current wilderness window | TravelWindowTests.test_live_memory_and_distant_cards |
| Travel observations follow canonical sight and phase facts | TravelWindowTests.test_live_memory_and_distant_cards + test_travel_events |

Focused accompanying tests: tests/travel/window.test.js; existing area-map and travel-event suites; TravelWindowTests.test_live_memory_and_distant_cards.
