# Design

## Context

Status currently supplies resources/fatigue, with schema5 asleep facts from the base slice. No active planner proposal supplies a status capacity gauge or adjacent duration quotes. travel_cost.py owns plan_traversal, source_present_members and actual rounded foot durations; fatigue.py owns detached prediction. TravelWalkControls is the working intermediate command surface. preferences.js and layout_store.js own persisted view preferences.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Supply server-authored foot capacity and neighbour duration facts, then present the leg gauge and persisted travel preferences.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Read-only status additions
Add world/rules/travel_capacity.py::build_travel_status(actor) -> dict|None and pure capacity_by_stage(snapshot,terrain) -> {normal,light,moderate,severe}. Return null outside wilderness exploration. Inside, exact object is {capacity:{normal,light,moderate,severe},neighbours:[{exit_ref,seconds}],at_pace:{cautious,standard}}. Counts are nonnegative safe integers, at_pace values booleans from exact current worst stage, neighbours at most12 with opaque exit_ref1..64 ASCII and seconds nullable nonnegative safe integer. No names, coordinates or hidden target metadata are added by quotes. Disabled/unreadable neighbour duration is null; the authoritative move row continues to supply enabled/reason. Do not add a second admission decision.

Capacity means hypothetical orthogonal FOOT_TRAVEL steps on uniform current terrain, with source-present travellers moving at their canonical slowest speed, including each existing rounded step and detached reserve prediction until preflight would refuse or a member sleeps. Count each admitted step by worst after-step stage. This is a terrain capacity estimate with no path/reveal/road lookahead. It never promises actual movement eligibility. Use a detached physical one-kilometre TraversalSegment through canonical plan_traversal and prediction; do not import the future route planner or inspect neighbouring terrain. Capacity is explicitly foot travel, so a flight waiver cannot produce an infinite count; name the estimate accordingly in the intent/legend. Asleep/refused first step gives zero counts. Reading invokes no lazy handler, movement hook, object preparation, clock writer or knowledge writer. Neighbour seconds is the existing preflight physical duration with the canonical existing charge waiver applied, copied before any traverse, including0 for allowed flight. Extract a pure charge-decision helper from the current movement owner if needed; planning later must reuse it rather than duplicate it.

Add required status.travel_capacity (the exact object or null), schema5->6 clean Python/JS cutover. Preserve every unrelated status field and asleep facts. New status-capacity failure yields null while ordinary status still renders, with a logged diagnostic; malformed wire data rejects the panel. Test canonical state unchanged. No server pace/interrupt rule is reimplemented here; at_pace is an advisory projection of exact fatigue state for the intent line, never the queue's stop engine.

### Preferences and panel
Extend the existing preferences wrapper validation/persistence with travelPace:cautious|standard|forced defaultstandard and travelStopAtNight:boolean defaulttrue. Missing keys use defaults, malformed values use existing preference validation policy, no version migration or alternate store. Expose store.setTravelPace(value), setTravelStopAtNight(value) and view.travel preferences. Walking freezes them and both setters reject changes while walking. Before route/interrupt prerequisites, preferences remain saved intent and gauge markers; do not claim that old two-field server moves enforce them. Route-ui activates their server walk form.

Replace TravelWalkControls with LegPanel.vue, migrating all callers/tests/stories and deleting that intermediate component. Pure components/travel/leg-model.js::legView({aim,plan,locked,walking,progress,capacity,preferences,phase,error,serverTime}) returns intent, ticks, legend and actions. Pending/stale/unavailable capacity is explicit and disables travel actions; do not calculate capacity from displayed percent. Intent priority is error, walking, aim (quote minutes or blocked reason), locked/hover plan, current pace threshold, night advisory, idle. Night advisory uses only supplied phase. Display foot capacity when no plan; plan ticks use each supplied fatigue_stage, vary height and shape besides colour, moon at nightfall and camp line at stop, travelled ticks spent. Plan durations use total_seconds (already through stop_index), and display stop time by adding it to committed serverTime, never advance any gameplay time. Interpret plan shapes only when planning-ui supplies them; absence is a working no-plan state.

Radio labels are 保守/標準/強行, night switch is 入夜停步. 出發 is disabled without a current locked plan, becomes 停步 while walking; 環顧 dispatches existing explore.look {room:true} through the ordinary guard and uses structured look event. 紮營 remains the real existing sleep entry before sub-project3, opening the existing sleep-choice card, with no new camp API or placeholder button; expose the single client openTravelCamp() action so sub-project3 replaces this destination with its camp card. Keep forced-sleep handoff priority unchanged. Text remains at least16px*scale and every control has a focus ring, disabled reason and semantic radio/switch role.

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
| Travel status supplies bounded foot capacity and quotes | world.rules.tests.test_travel_capacity (discoverable test_sequential_capacity_and_quotes) |
| Leg panel projects supplied state and persisted preferences | TravelLegTests.test_gauge_preferences_and_actions |

Focused accompanying tests: world.rules.tests.test_travel_capacity; tests/travel/{preferences,leg}.test.js; TravelLegTests.test_gauge_preferences_and_actions.
