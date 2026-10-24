# Design: redesign-rest-entry

The authority for every visual and interaction decision is `docs/superpowers/specs/2026-10-24-rest-entry-redesign-design.md` (§2–§8). The geometry, colors, and feel come from the prototype in `docs/design/time-choice-redesign/` (`TimeChoicePrototype.vue`, `WaitFormPrototype.vue`); where the prototype and the design doc disagree on behavior, the design doc wins. This file records how the change maps onto the current code and the few choices the design doc leaves to implementation.

## Context

Current code path (observed):

- `components/PlaceCard.vue` renders the 等待 button (`data-testid="place-card-wait"`, class `place-card__action--wait`) and emits `hover` with `PLACE_WAIT_READOUT` from `components/exploration-readout.js`.
- `composables/use-room-actions.js` owns the view-local `waitStep` (`null | "sleep" | "rest"`), builds the wait rows with `waitCardRows(store.view.waitRows, locked)`, and routes row picks: `wait-sleep` opens `SleepForm`, `wait-rest` opens `RestForm`, and `wait-dawn` calls `store.activateWaitRow(key)`.
- `stores/elosern/room_actions.js` gates `openRoomCard("wait")` on `ctx.frameResolver.explorationWait()` being non-null, implements `activateWaitRow`, and publishes `waitRows` in `roomActionsView()`. `stores/elosern.js` re-exports `activateWaitRow`.
- `stores/frame-resolvers.js` `explorationWait()` returns `ExplorationMenu.waitItems()` without its back row, or null when `requireExplorationPanel()` fails (no `exploration` panel, or `available === false`).
- `web/static/webclient/js/elosern/exploration_menu.js` `waitItems()` builds the three rows plus a back row; `stores/elosern/interaction.js` ignores items flagged `openRestForm`.
- `AppClient.vue` renders the wait card through `ChoiceCard` (kept mounted under `v-show` so its active row survives) and two `section.choice-card.rest-card` blocks for the sleep and rest forms.
- The status panel payload (`web/webclient/presentation/status.py`) carries `fatigue[]` rows `{identity, name, reserve_percent, stage, label, severity, restriction}`: the status source's own row, plus the controlled body's distinct row under possession. `panels.status.actor.identity` is the controlled body's identity.
- `store.view.statusSlice.timeLabel` is `"<season> <day> 日 ‧ HH:MM"` (`stores/elosern/shared.js` `formatTimeLabel`), or null.

## Goals / Non-Goals

**Goals:**

- Implement §2–§8 of the design doc exactly, client side only.
- Remove the wait-row builder path end to end, including its tests and story fixtures, without leaving a compatibility shim (pre-release project).

**Non-Goals:**

- No change to the server, the `explore.wait` validator, or any payload. `midnight`, `noon`, and `dusk` stay out of the client.
- No change to the sleep handoff, dream question, or continuation surfaces.
- `RestForm.vue` and its `Action/RestForm` story stay (design doc §4). The `openRestForm` guard in `stores/elosern/interaction.js` stays as is; after this change no builder produces that flag, and removing it is not part of this change.
- The player-facing term 精神儲備 elsewhere (status panel, travel refusal, handoff label, docs) belongs to `rename-reserve-to-energy`.

## Decisions

**D1. Keep the room card kind `"wait"` and widen `waitStep` to `null | "wait" | "sleep"`.** The store slice, `openRoomCard("wait")`, `closeRoomCard`, `settleRoomCard` (move and mode close), the opener-focus watcher, and the Tab chain stay unchanged (design doc §6). `waitStep === null` shows the tiles; `"wait"` and `"sleep"` show that layer-2 shell. A new view-local ref `lastTile` (`"wait" | "sleep"`, default `"wait"`) remembers which tile opened the current step. Alternative considered: a second room card kind per layer; rejected because it would duplicate the move/mode close and the focus return.

**D2. Express the availability gate directly.** `openRoomCard("wait")` replaces `ctx.frameResolver.explorationWait()` with a direct read of the committed state: `const panel = rs.panels && rs.panels.exploration; if (!panel || panel.available === false) return false;`. That is the same check `requireExplorationPanel()` makes. `explorationWait` is then deleted from `frame-resolvers.js` and from its returned object. Alternative: export `requireExplorationPanel`; rejected because the registry's public surface should only shrink here.

**D3. Dispatch through `dispatchIntent`, like the existing sleep handlers.** `onWaitDawn()` sends `dispatchIntent("explore.wait", { daypart: "dawn" })` and `onWaitSubmit(seconds)` sends `dispatchIntent("explore.wait", { seconds })`. Each returns early while `skipDisabled` is true and calls `store.closeRoomCard()` only when `dispatchIntent` returns non-null. The sleep handlers `onSleepRecover` and `onSleepSubmit` stay. The dawn wait previously went through `activateExplorationRow` with the builder row (which also passed `commandDisplay`, absent on that row), so the request bytes are unchanged.

**D4. `TimeChoiceCard.vue` is presentational and self-contained.** Props: `timeLabel` (string or null), `fatigue` (`{reserve_percent, label}` or null), `locked` (boolean), `entrance` (boolean, default true), `autofocus` (boolean, default true), `initialTile` (`"wait" | "sleep"`, default `"wait"`). Emits: `pick("wait" | "sleep")` and `close`. It exposes `focusTile(key)` via `defineExpose`. It reuses the global `choice-card` frame classes (`choice-card`, `choice-card__corners`, `choice-card__caption`) that `ChoiceCard.vue` ships and copies the close button markup and SVG from `QuestionCard.vue` (`question-card__close`). It handles its own keys on the root `keydown` and calls `event.stopPropagation()` for every key it consumes, as `ChoiceCard` does, so the store's digit routing never sees `1`/`2`. The Tab trap uses `focusableElements()` from `components/focus-trap.js` over the card root. The narrow layout uses a container query (`container-type: inline-size` on the card's host) at `calc(320px * var(--ui-scale))`; if `calc` with a custom property is not accepted in the container query, the card measures its own width with a `ResizeObserver` and toggles a `time-choice--stacked` class instead.

**D5. The context lines are computed in the composable and passed as props.** `useRoomActions` adds `waitTileTime = computed(() => store.view.statusSlice.timeLabel ? store.view.statusSlice.timeLabel.split("‧").pop().trim() : null)` and `sleepTileFatigue`: the row of `store.view.panels.status.fatigue` whose `identity` equals `String(store.view.panels.status.actor.identity)`, or null when the panel is absent, unavailable, has no `fatigue` array, or has no matching row. The tile renders `現在 ${time}` and `精力 ${reserve_percent}%（${label}）` (numerals in the mono face, the stage label in the sans face, `white-space: nowrap`).

**D6. One layer-2 shell in `AppClient.vue`.** A single `<section class="choice-card rest-step" role="dialog" aria-modal="true" :aria-labelledby="restStepCaptionId" :data-testid="waitStep === 'wait' ? 'wait-form-card' : 'sleep-card'">` renders `choice-card__corners`, a visible caption `<div :id="restStepCaptionId" class="choice-card__caption">{{ waitStep === 'wait' ? '等待' : '睡眠' }}</div>`, then `<WaitForm>` or `<SleepForm>`, then the two corner buttons (`rest-step-back`, `rest-step-close`). The shell's `keydown` handler traps Tab across `focusableElements(shell)` and maps Escape on a corner button to `onStepBack()`. The forms already stop propagation and emit `close` on Escape; `close` maps to `onStepBack()`. The class `.rest-card` and the `rest-card` test id are removed; the flat-form rule moves to `.rest-step .exploration-sleep-form, .rest-step .exploration-wait-form { background: transparent; border: 0; }`.

**D7. Focus moves.** `onTilePick(key)`: no-op while `skipDisabled`; otherwise `lastTile.value = key; waitStep.value = key;` (the form autofocuses its input on mount). `onStepBack()`: `waitStep.value = null; await nextTick(); roomCardRef.value?.focusTile(lastTile.value)`. `onStepClose()` and the tile card's `close`: `store.closeRoomCard()`; the existing watcher returns focus to `place-card-wait`. The watcher's `waitStep.value = null` reset on kind change also resets `lastTile` to `"wait"`.

**D8. `WaitForm.vue` copies `SleepForm.vue`.** Same props (`max` 43200, `autofocus`, `disabled`), same validation and error text, same `onKeyDown` (stop propagation; Escape emits `close`). Emits `dawn`, `submit(seconds)`, `close`, `error`. Root `<form class="exploration-wait-form" data-testid="wait-form">`; first button `data-testid="wait-form-dawn"` with text 等待直到黎明; input `aria-label="等待時長（小時）"`; submit text 等待此時長. Both forms set `text-align: center` on their `input`.

**D9. Story fixtures.** `stories/fixtures/scene_overview.js` drops `waitCardArgs` and adds `timeChoiceArgs({ locked = false, fatigue = true, narrow = false } = {})` returning the `TimeChoiceCard` props with fixed values (time label `春季 3 日 ‧ 22:40`, fatigue `{reserve_percent: 62, label: "輕度疲勞"}`). `Core/ChoiceCard` loses its `Wait` and `WaitLocked` stories; `Core/ExplorationScreen`'s `WaitCard` story renders `TimeChoiceCard` from `timeChoiceArgs()`.

**D10. Requirement identifiers.** Two requirements are replaced rather than modified (`webclient-room-actions` "等待 opens the wait card through ChoiceCard" and `webclient-exploration-menu` "The waiting surface offers exactly three operations"), and one is renamed (`webclient-room-actions` "The place card carries 查看房間 and 等待 in exploration only"), because OpenSpec refuses a MODIFIED block that drops scenarios. Until archive syncs the specs, the old identifiers stay canonical, so existing `covers_requirement` annotations keep naming them and new tests annotate the nearest current requirement. The archive step re-mounts them to the identifiers `uv run --locked python -m tools.spec_traceability list` prints after sync (see tasks.md, Workflow follow-up).

**D11. Player docs.** The two sentences in `docs/game/commands.md` and the `wait` entry of `docs/game/command-reference.md` that describe the web client's 等待 card are rewritten for the 休息 entry. This is the same relabel applied to player documentation, which `AGENTS.md` treats as part of the command surface.

## Risks / Trade-offs

- [Many browser tests and helpers open the wait card by row key] → `browser_helpers.activate_wait_row` keeps its key vocabulary (`wait-dawn`, `wait-sleep`, `wait-rest`) and maps each key onto the new path (tile, then form), so its callers need no change; the callers that wait for `exploration-rest-form` switch to `wait-form`.
- [Manifest exact-set evidence tests fail when stories are added] → the tasks list each evidence test that pins the manifest and the `Action/*` family set.
- [The frozen-contract audit rejects unregistered test ids] → the tasks register every new test id in the audit's §2.3 REMAP-TO-TESTID rows and run `tests.test_webclient_frozen_contract`.
- [Focus return after step-back races the DOM] → step-back awaits `nextTick()` before `focusTile`, the same pattern `returnToWaitCard` uses today.

## Migration Plan

None. Client-only, pre-release; no persisted state changes.
