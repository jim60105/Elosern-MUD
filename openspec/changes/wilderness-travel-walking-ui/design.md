# Design

## Context

ExitCompass.vue currently owns hold timers and a component-local walk loop. components/compass-model.js owns aimFromKeys and resolveTargets; stores/elosern/interaction.js::activateExit re-resolves exit_ref and current_node through the common guarded activation. stores/elosern/transport.js::dispatchAction is single-flight and lastActionResult is not proof that its declared revision committed. The base change owns current map freshness.

The approved scope is the interface design §§2-13 and blueprint §§4-6/7.2. Read web/webclient-app/AGENTS.md and the engine architecture §§2/3/6.5/10 before apply. Source documents were read during proposal discovery; the six existing active proposals remain authoritative owners of sub-project1.

## Goals / Non-Goals

Provide persistent neighbour aim and commit-paced held walking through the existing guarded movement path.

Allowed edits are the files/symbols explicitly named by this design/tasks plus their protocol constants, registration/parity fixtures, focused tests, shard manifests and existing developer/control documentation. MUST NOT edit authored content/maps, generated elevation, sight/reveal/route/interrupt rule semantics, camping implementation, dialogue/combat layout or unrelated windows. A named shared owner is an integration seam, not permission to refactor that subsystem. All new travel components live under components/travel/. No production import of prototype rules.

## Decisions

### Store state and activation
Add walking state to applyTravel, with view.travel.aim and view.travel.walking. Internal walking is {kind:"direction",direction,departedPlan:null,progress:0,pending:null,commitSeen:false,dwellUntil:null,generation,epoch}. Export aimTravel(direction), stepTravel(), holdTravel(direction), releaseTravel(), stopTravel(reason) through stores/elosern.js. Actual timers live in this store module and are cancelled on disconnect, epoch/generation changes and disposal; components never own a second queue. Use existing compass-model key combination and committed target resolution, including directional rows with null destinations after map-disclosure. No destination identity or Exit is manufactured. Re-resolve the current direction's row on every dispatch through activateExit. Extend activateExit with an internal optional walk argument only when route-ui later enables the exact server union; old callers keep their unchanged payload.

One pending explore.move at a time. Match its requestId and successful outcome, then wait until reducer revision >= its presentation_revision in the same epoch and the canonical current node changed from the sent node. Support result-before-publication and publication-before-result. A foreign result, same-room object identity, unrelated revision or an available dispatch gate alone cannot acknowledge a step. Increment progress exactly once on qualifying commit. Then wait STEP_DWELL_MS=350 from commit (0 at effective motion off) and current fresh map readiness/dispatch availability before the next send. mapStatus=refreshing is ordinary post-step waiting: preserve the walk and progress and resume only after ready. unavailable, invalid or retired maps cancel it; they never resume it automatically. Never make a repeat from animationend, elapsed dwell alone or a map response. Off still requires a committed step. Refused/stale/failed results stop and preserve the server message. A step already sent is never undone or resent after stop; a late commit only updates committed state.

### Input ownership
TravelMap is one role=application focus stop with a control aria-label and inset focus ring. Its arrows persist aim after release and combine two pressed arrows for diagonal aim. Enter with aim sends one step, neighbour click sends one step, party/unknown-cell clicks send no move (opaque directional keyboard controls remain usable where undisclosed neighbours cannot be clicked). A400ms arrow hold starts direction walking; releasing the originating arrows stops it. Native repeat must not send discrete moves. Aim persists after a short release. Escape clears aim; off-map/blocked clicks show supplied reason. Stop on refusal, disconnect, epoch/generation change, loss of travel layout, overlay/card opening, map becoming unreadable, blur, Stop and any new key press. Exception for held walk: originating held-arrow auto-repeat is continuation, not a new stop key. Another key or direction stops first and does not also step; the initial departure event cannot stop itself. A route walk later stops even on arrow repeats. Listeners ignore modified/composing keys for aiming and never steal input from text entries, existing dialogs or drawers. A document capture listener only cancels an active walk before existing hotkeys run; do not replace the shared keyboard bridge.

### Working intermediate surface
TravelMap emits the intents above and existing ExitCompass is removed from travel layout only; it remains the ordinary exploration/dialogue implementation. Add components/travel/TravelWalkControls.vue with the real intent line and Stop button as the travel band-command content until LegPanel replaces it. Base MessageWindow remains until log-ui. During walking hide neighbours/hover, retain following party token; stop restores map focus unless an existing event card/dialogue/drawer owns it. No paces, threshold prediction or local route search are introduced here. Before server interrupts land, held walking uses existing physical refusal/lifecycle stops only; route-ui adds server-reported stops and walk context.

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

B2 adopted. The cancellation scenario names actual unavailable/invalid/retired maps and a new two-step-refresh scenario proves ordinary refreshing can continue after dwell. All six blocking findings were addressed across the batch; no requirement was replaced with human-judged copy/appearance evidence. This records remediation, not an unperformed second review.

## Migration Plan

Pre-release clean cutover. No database migration, compatibility aliases or alternative wire schemas. The requested temporary node-grid adapter exists only until window-ui replaces it with the shared validated RLE decoder. Rollback is source reversal of the slice and its dependent slices together. Do not apply, sync or archive in the proposal workflow. Update existing developer guidance and control reference during implementation; these proposal artifacts are the requested documentation deliverable now.


## Requirement-to-evidence mapping

| Requirement | Discoverable mechanism evidence to implement |
| --- | --- |
| Travel aim maps to guarded neighbour movement | TravelWalkingTests.test_keyboard_only_step |
| Held walking waits for committed steps and dwell | TravelWalkingTests.test_held_walk_release |

Focused accompanying tests: tests/travel/{walking,input}.test.js; TravelWalkingTests.{test_keyboard_only_step,test_held_walk_release}.
