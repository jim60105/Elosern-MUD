# Design

## Context

wilderness-travel-planning exclusively owns travel.plan registration, read-only routing, durations/stages, domain errors and result schema. It returns result-only no_presentation outcomes through existing dispatcher support. This slice owns browser request lifecycle and preview only. Route departure is enabled by route-ui after interrupts; no premature multi-step execution is introduced. LegPanel and shared grid/camera are already usable after their prerequisites.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Add destination input, debounced current-only route queries and server-authored route/gauge previews.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Exact consumption
travel.plan input stays exactly {destination:{x:int,y:int},pace:"cautious"|"standard"|"forced",stop_at_night:bool}. Success data stays exactly {origin:{x,y},destination:{x,y},steps:[{cell:{x,y},seconds,fatigue_stage}],total_seconds,nightfall_index,stop_index,stop_reason}; max60, zero-based nullable indices and canonical stop reasons member_asleep|preflight_refused|pace_threshold|nightfall|destination_reached are owned by the prerequisite. Do not introduce a panel, route id, custom websocket channel, client A*, preview duration equation or server-owned walking state. Existing result validators must be reused; add missing bounded frontend result consumption at the common exact data-slot validator without replacing other actions' slots.

### Single-flight supersession
Extend stores/elosern/travel.js with destination/preview state and public hoverTravelCell(cell), lockTravelDestination(cell), clearTravelTarget(). State is {hover:null|cell,lockedDestination:null|cell,plan:null|data,pendingToken:null|token,error:null|{code,message}}. A token records generation,epoch,revision,currentNode,mapPublication,origin,destination,pace,stop_at_night,serial,requestId. Hover on a revealed non-adjacent cell schedules150ms debounce; pointer lock requests immediately when the dispatch gate is available. A newer intent invalidates older serials immediately, clears old preview and stores only the latest desired request. dispatchAction remains the one single-flight sender, so do not send a second read while an earlier query/mutation is in flight. When the gate frees, flush the latest still-valid desired request, never replay the superseded queue. Departure is not inferred from gate availability.

Only a matching requestId, token inputs and still-current origin/map/epoch adopts result data, in success or error. Result-only queries need no artificial presentation revision. Any newer aim/target/preference, committed movement/time/member state, map replacement, disconnect or epoch change invalidates an outstanding token and preview. Pointer leave cancels an unlocked hover preview; a lock survives pointer leave. A locked target stays across legal committed stops and schedules a fresh plan from new origin, but is cleared on map/frame/epoch exit or if no longer disclosed in the current window. Server errors plan_destination_outside_window/unrevealed/unreachable/too_long/party_cannot_travel appear in the intent line and clear preview; use stable zh-TW messages, never parse exception/prose. Other dispatcher refusals keep their server message. No automatic retries after server errors.

### Map and keyboard interactions
Pointer hover previews only revealed non-adjacent cells. Neighbour hover aims; neighbour click retains single-step precedence, including gate action descriptors. Non-adjacent revealed click locks, party/unknown clicks do nothing beyond outline, second click on the locked destination expresses depart only once route-ui has enabled it. Enter with ordinary neighbour aim retains single-step precedence; Esc clears aim first, then lock/preview. To satisfy the design's keyboard reachability despite its pointer-only destination table, Shift+arrows moves a visible destination cursor one cell inside the current window and clears neighbour aim. Enter on that cursor locks/queries a revealed non-party cell; after locking the cursor exits selection mode and a later Enter without aim expresses departure. Unknown cursor cells can be inspected only as unknown and cannot lock. Map aria-label explains ordinary arrow aim and Shift+arrow destination selection. +/- zoom remains independent. Visible focus/selection outline distinguishes cursor, aim and lock without colour. No extra tab stops per cell.

### Preview and leg projection
TravelMap SVG route has one stage-coded mark per server step: normal gold disc, light amber diamond, moderate/severe rust rings, with stage labels in accessible text. Beyond stop_index outline faintly, nightfall and later steps dim, moon on nightfall and camp mark at stop, destination outline. Use shared travel glyph definitions. HTML summary and LegPanel state use supplied total_seconds and plan stages, with stop time derived for display from the token's committed serverTime. An empty same-cell response has no route/departure. Route fit uses the existing safe-rectangle function and minimum14px scaled cells; hover preview does not lock camera, lock does. Departure remains disabled with explicit pending prerequisite reason until route-ui installs the route action; tests/story previews are fully functional and no fake departure is shipped. This slice's tests do not claim executable route walking.

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
| Travel route queries are debounced and current-only | TravelPlanningTests.test_destination_query_supersession |
| Travel destinations and previews remain disclosed and accessible | TravelPlanningTests.test_destination_preview_keyboard_and_pointer |

Focused accompanying tests: tests/travel/{planning,destinations,preview}.test.js; TravelPlanningTests.test_destination_preview_keyboard_and_pointer.
