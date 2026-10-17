# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Parameterize the existing UMD menu and frame resolver by actor, implement actor/progress/revisit frames and pending result handling; test selection edits and disabled members.
  - `web/static/webclient/js/elosern/combat_menu.js` adds `actorItems`/`progressLine`/`commandEnvelope` and the `menus.actor` frame; `stores/frame-resolvers.js` registers `combat.actor` and `resetCombatSelection`; `stores/elosern/frames.js` owns the pending `combat.actor_choices` query, the one-root transition and the pending-result settle.
  - Evidence: Node gate `combat_menu.test.js` (actor order, confirmed/needs-selection, reselection reason, noncommandable reason, token disambiguation, progress line, envelope); Vitest `tests/store/party_command_selection.test.js` (switch, same-actor return, selection drop, revisit/replacement).

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Migrate all skill payload producers to combat.command with current session/round/draft versions; test every TargetSpec, scale and final versus partial results.
  - Every producer (Attack, Skills master-detail, scale step, NONE, SELF, SINGLE, AREA explicit/shorthand, keyboard/pointer/digit) routes through `submitCombatCommand`/`submitCombatEnvelope`; the versions are read from the committed panel at submit time.
  - Evidence: Node `combat_menu.test.js` ("every TargetSpec keeps its exact inner skill payload inside the command"); Vitest envelope versions, four-form parity, final (`round_committed`) versus partial (`draft_saved`), stale and `needs_selection`.

## 3. Bounded implementation and evidence (1h)

- [x] 3.1 Bind SELF stage lighting and cross-side confirmation to commanded actor; test companion SELF, mixed AREA, actor switch while targeting and warning cancellation.
  - `stageTargetModel` takes `actorIdentity` (the committed `choices.actor_id`); `stage-targeting.onStage` is a fallback only; `evaluateCrossSide`/`askCrossSide` use the commanded actor and hold the full envelope.
  - Evidence: Vitest companion SELF position and SINGLE-target distinction, companion SELF question wording with 是/否, draft-version cancellation, AREA cross-side cases in `tests/store/cross_side_confirm.test.js` (migrated to the envelope).

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Integrate reconnect, stale replacement, focus restoration and playback lock; test no automatic send or draft erasure on reconnect.
  - `settleCombatActorSelection` drops unconfirmed local selection on any generation/session/actor change and never touches committed draft entries; the advance is a one-shot record that survives no reconnect; `openCombatActor` requests dock focus; the playback lock keeps gating submissions and the stage step.
  - Evidence: Vitest reconnect cases (no dispatch, restored progress, server-chosen first missing actor), `stale_command` no-replay, one-shot advance consumed once; `cross_side_confirm.test.js` playing-round cancellation.

## 5. Bounded implementation and evidence (1h)

- [x] 5.1 Add stories and focused keyboard/pointer/browser coverage within the existing centered card at both acceptance viewports; update client flow docs and browser shard manifest.
  - `stories/Core/AppShell.stories.js` adds `CombatActorSelector` and migrates the polish round's dispatch.
  - Browser suite migrated to the guarded envelope (combat menu/panels/scales/skills/choreography/rejection/pointer) with the bounded actor-card journey `test_actor_selector_chrome_returns_to_root_without_a_command` registered in `.github/browser-shards.json`. Both-viewport card geometry stays covered by the existing registered methods (`test_dock_and_figure_plate_geometry_at_both_desktop_viewports`, `test_combat_renders_at_minimum_viewport`); managed browser execution is CI-owned.
  - `docs/development/frontend-vue-architecture.md` documents the commanded-actor flow; no player command changed, so `docs/game/commands.md`/`command-reference.md` are untouched.

## 6. Integration gate (1h)

- [x] 6.1 Run focused Node/Vitest and one bounded browser method plus tools.contract_gate; update canonical requirement IDs and preserve all active UI geometry contracts.
  - Evidence: `node --test web/static/webclient/js/tests/*.test.js` (547 passed); `pnpm test` (2477 passed, 179 files); `uv run --locked python -m tools.contract_gate` passed; `.github/browser-shards.json` ownership contract (`tests.test_evennia_test_optimization_contract`, 9 tests OK); Storybook `build-storybook` + `showcase-coverage` (74/74) passed.
  - The new browser method is exercised by CI (local managed-browser runs are CI-owned); it reuses the existing canonical requirement ID, so no requirement-ID migration was needed. The card's outer geometry (264px·S) and the active UI contracts are unchanged; the actor line occupies the card's own chrome.
