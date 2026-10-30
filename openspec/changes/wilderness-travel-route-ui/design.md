# Design

## Context

wilderness-travel-interrupts exclusively owns the exact optional walk payload, committed interrupt flags, before/after comparison and movement collector. planning-ui owns the exact query and preview; walking-ui owns one pending step and commit/dwell timing. travel_events owns typed notices, while window-ui enriches their canonical observation inputs. Existing AppClient choices ordering already prioritizes sleep handoff/dream/dialogue/combat; landmark cards must join that host without replacing higher-priority flows.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Execute locked plans through the commit/dwell queue, consume every server interrupt and present landmark arrival cards.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Departed plan and guarded dispatch
Enable departTravel() in the travel store, expose it through the facade and wire LegPanel Enter/no-aim/Depart and second locked-cell click to that same action. Require connected active travel layout, current available map, no blocking card, no aim, no pending query/mutation and a token-current nonempty locked plan. Capture an immutable departedPlan and preferences, with walking={kind:"route",departedPlan,progress:0,pending:null,commitSeen:false,dwellUntil:null,generation,epoch}; never replace it with new preview responses during a walk. Queue indices0..stop_index inclusive. Empty/null-stop plans cannot depart; stop_index is never interpreted as a count. Beyond-stop preview marks remain visible as the supplied planned future, while remaining executable prefix shrinks and leg spent ticks increase with qualifying commits.

Before each send, compare the next supplied step with current party cell, derive its direction geometrically and select the corresponding CURRENT server move row through compass-model resolution. Require its disclosed destination/action to match the next canonical cell; never infer an Exit or movement permission from a route coordinate. Settlement gateway actions remain ordinary neighbour movement, not route nodes. If the expected step no longer has a current legal descriptor, stop with its supplied reason and keep the lock for a fresh query. Extend interaction.js::activateExit(exitRef, walk = null) through the existing activateExplorationRow guard so payload adds exactly walk:{pace,stop_at_night}; omitted null keeps all ordinary exploration callers unchanged. Do not bypass stale-row, epoch, mutation or current_node checks.

Both direction and route walking now send that exact walk context using frozen departure preferences; discrete neighbour steps keep the ordinary two-field payload. Consume result.data.interrupts only for this pending explore.move. All seven prerequisite flags landmark_reached,district_lit,landmark_sighted,hostile_in_sight,pace_threshold,nightfall,member_asleep stop the queue, including combined flags and empty-array continuation. Their server meaning stays owned by wilderness-travel-interrupts. Successful move completion must still satisfy walking-ui's correlated commit, canonical node change, fresh map, one-step progress and350ms dwell (0 off). Stop flags never wait out dwell to permit another step. Compare or decode no server rules in the client. Stop on refusal, disconnect, epoch/generation change, any new key, Stop, blur/layout exit, event card or depleted prefix. The initial departure event cannot also stop; a later Enter stops without departing again. No timers/replies may restart a stopped walk.

### Stop state and replanning
On short stop keep lockedDestination and discard preview token, request a fresh travel.plan from the new committed position only once the move publication/map are ready and no blocking event card owns focus. Never auto-depart that new plan. Reaching destination clears the lock; leaving window/frame/epoch clears it. During walking the camera follows, hover/neighbour nodes hide, and LegPanel displays the departed immutable plan with committed progress. A stopped refused move emits exactly one server refusal line into intent and travel log, with existing local requestId dedup. Focus returns to map unless a real card/dialogue/drawer has taken it.

### Landmark card
Add components/travel/LandmarkCard.vue, bound to a committed landmark_reached entry {id,params:{name,lit_district,prose,artwork}}. Never open from parsed narration or from interrupt flag alone (flags have no card content). Card is a dialog in choices, contains ArtworkPreview in a16:6 frame, arrival title, supplied name, diamond district disclosure only when lit_district is non-null, supplied prose and Continue. Focus initially on Continue, trap Tab using the existing focus-trap composable, Enter/Escape close and restore map focus. Use the supplied canonical descriptor or its truthful absent state, not new art. Dedupe entry IDs across publications. Close on epoch/room/layout change. Existing higher-priority sleep/dream/combat/dialogue cards win; keep one pending arrival for the same current cell/epoch and show it only if that cell remains current after the higher-priority card closes. Clear pending when location changes. A card that opens during a walk stops it before any next send. No camp/campfire cards or new sleep choices are implemented here.

### Observation collector integration
Where both window-ui's travel event capture and prerequisite interrupt collector touch movement, use one immutable before/after observation read per traversal and fan it to their two existing pure comparisons. Keep capture_movement_observation(actor) and its Deferred/on_publication_commit completion semantics from the interrupt proposal. Extend its internal observation value to expose the primitive facts needed by travel_events; do not replace collector actor scoping or swallow real movement failure. Typed events are delivered only on publication commit and interrupt data is composed with other result data, never substituted wholesale. This is an integration of the two consumers, with no new server interrupt rule.

### End-to-end acceptance
Complete the seven production states Morning, Route Preview, Dusk, Night, Woodland, Landmark Arrival and Motion Off with real components and exact protocol fixtures. Prototype camp/campfire stories remain reference-only and outside the production showcase. All text>=16px*scale, visible map/control focus, glyph/text stage distinctions and polite log/intent channels apply. Browser acceptance includes settlement gate enter/leave, hostile_in_sight route interruption, keyboard-only stepping and both viewport screenshots; repaint benchmark continues to prove <=50ms per content repaint and zero camera-only paints. Test late-result cancellation, every individual flag and combinations, short-stop replanning without departure, refusal, frame/epoch changes, current-node remapping and event focus priority. Existing ordinary exploration compass, dialogue and combat behavior must retain their focused test coverage.

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
| Route walking consumes plans and committed interrupts | TravelRouteTests.test_hostile_interrupt / test_all_interrupt_flags |
| Landmark arrivals own focus through committed typed events | TravelRouteTests.test_landmark_focus |

Focused accompanying tests: tests/travel/{route-walking,landmark}.test.js; existing travel-event/interrupt suites; TravelRouteTests.{test_hostile_interrupt,test_landmark_focus}.
