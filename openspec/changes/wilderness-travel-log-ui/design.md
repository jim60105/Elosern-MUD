# Design

## Context

world/rules/movement_settlement.py::settle_movement and map_discovery.py::publish_traversal_narrative already preserve ordinary traversal prose after commit. world/rules/presentation_events.py owns publication_group/on_publication_commit; web/webclient/presentation/{alignment,push,coordinator,registry}.py fan out committed presentation. Existing raw narrative is retained for FullLogOverlay. No active sub-project1 change owns a structured travel log or travel card.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Publish commit-qualified structured travel notices and render the travel band log without parsing room prose.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Commit-qualified event transport
Add world/rules/travel_events.py with frozen TravelEvent(kind,params,text,tick,day,time) and TravelLogFact(actor_id,group_id,events). capture_travel_facts(actor) copies primitive before facts at the movement/explicit-skip owner; build_travel_events(before,after,cause) returns immutable events and a server template renders their text. Register delivery with on_publication_commit inside the owning transaction, never after it has already committed. Failure to deliver logs via observability facade and cannot roll back successful movement. Capture source coordinates before pooled room mutation. Include possessed actor/authorized owner using the existing movement audience policy. No persistent event store, new game clock, reveal writer or walking session.

Add presentation/travel_log.py presenter/validator and travel_log_push.py fan-out following push.py. Each coordinator retains only its latest committed batch for its current puppet/epoch, initially empty. Add coordinator.record_travel_events(fact); it assigns entry IDs group_id + ":" + ordinal, merges facts from the same causal group in emission order, deduplicates exact IDs and invalidates only travel_log. Expose the frozen batch via an explicit travel_events field on PresentationContext, supplied by the coordinator. Duplicate delivery is inert. New epoch/puppet clears it; repeated reads/snapshots never generate events. Register one eager travel_log panel in registry.py and mirrored protocol panel registry. Available form is exactly {schema_version:1,available:true,entries:[entry]}; outside wilderness or with no batch entries is empty, not fabricated plain narration. Use the existing unavailable form on malformed/oversize batches.

Each entry is exactly {id,kind,tick,day,time,text,params}. id bounded ASCII1..80, tick/day nonnegative safe integers, time server-rendered nonblank<=32 codepoints, text nonblank<=1024 codepoints, at most64 entries and canonical UTF8<=65536 bytes. The kind/params discriminated union is closed:

| kind | exact params |
| --- | --- |
| region_entered | {name} |
| woodland_entered | {name} |
| ford_crossed | {name} |
| hostile_sighted | {name,count,threat} |
| landmark_sighted | {name,bearing,distance_km} |
| landmark_reached | {name,lit_district,prose,artwork} |
| fatigue_stage | {member_id,name,stage,label} |
| dusk / nightfall | {} |
| camp_result | {summary} |
| look | {prose} |

All names/labels/bearing/summary bounded<=256; nullable name permitted only for landmark_sighted, threat and lit_district are nullable bounded strings. Count positive safe integer, distance nonnegative safe integer. member_id opaque<=64 ASCII; stage is canonical fatigue enum; prose<=8192. artwork is the existing validated descriptor or null, never a URL invented by client. Look text is a one-line server summary while prose retains the full appearance. Literal prose is rendered through existing safe text/markup primitives, never v-html. Card art uses existing descriptor attempt lifecycle. Payload byte ceiling is enforced independently of field bounds. Do not truncate a malformed event into apparent validity.

### Producers and early adapter boundary
Movement captures region/terrain/ford before and after from current provider; emit region_entered only on region identity change, woodland_entered only on entering the woodland family from outside it, ford_crossed only on an actual ford step. Actual landmark arrival uses exact landmark membership and the existing persisted lighting change, including repeat arrival but lit_district only when newly lit. Use the existing landmark description and room art descriptor for the card facts. Fatigue events come from canonical settled subject stage/posture transitions, including explicit wait/rest and sleep continuation; do not infer from rounded percentages. Room explore.look and ordinary room look call the same emitter after successful at_look, carrying full appearance, without an extra time charge. Hook shared command room-look seam as well as _look_adapter without double emitting.

Before sub-project1, hostile_sighted is limited to newly visible current-room hostiles with existing stable runtime identities; landmark_sighted is limited to a newly visible disclosed landmark in the existing local view. There is no invented remote sight, light phase or radius. When canonical phase/sight facts become available, window-ui switches these comparisons to sight/population before/after inputs and adds dusk/nightfall boundary events; it deletes the limited current-view comparison. camp_result is a closed consumer contract for sub-project3, with no camp emitter/command or mocked camp outcome in this batch. Later route-ui consumes landmark_reached to open the real card. Tests for all kinds use injected fact payloads; later producer acceptance belongs to window-ui and route-ui.

### Client retention and presentation
Add stores/elosern/travel_log.js::applyTravelLog(ctx), exposing view.travel.entries and appendTravelRefusal(requestId,message). Retain128 entries per generation/epoch, dedupe by stable entry ID before appending, reset on epoch retirement, preserve chronological order and day grouping. A refusal is a local entry keyed by its requestId, using committed server time and server refusal text, never a fabricated server event. Use existing full-log append primitive for structured text exactly once; ordinary room narration remains untouched in full log. Suppress MessageWindow rendering only in travel layout, and mount TravelLog.vue in band-message with polite live region, newest at bottom, day headings, time and glyphs (landmark diamond, hostile triangle, fatigue half-disc, night moon, camp tent, ford wave, plain dot). Region/woodland/look are plain. Do not parse messages to decide importance; do not move the raw narrative stream into travel entries. New entries scroll to bottom only when the log was at bottom; full-log opener remains available. Multi-line look prose is available in the existing full log and expanded entry text without changing its event kind.

During travel log-ui can ship before walking-ui; later walking-ui/route-ui call appendTravelRefusal. Shared full-log and MessageWindow behavior outside travel remains unchanged.

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
| Travel notices are committed structured events | TravelLogTests.test_committed_log_and_full_prose + world.rules.tests.test_travel_events |
| Travel log retains typed chronological entries | TravelLogTests.test_committed_log_and_full_prose |

Focused accompanying tests: world.rules.tests.test_travel_events; web.webclient.presentation.tests.test_travel_log; tests/travel/log.test.js; TravelLogTests.test_committed_log_and_full_prose.
