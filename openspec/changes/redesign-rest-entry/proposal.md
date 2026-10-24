# Proposal: redesign-rest-entry

## Why

The place card's 等待 button opens a `ChoiceCard` with three flat rows (等待直到黎明, 睡眠至完全恢復, 等待 N 小時) that hide four actions on two axes, mode (stay awake or sleep) by end condition (an until-state or a duration). The card is named after one mode, row 2 is labelled as if it slept when it only opens a form, and neither form has a visible way out: Escape is the only exit and it returns to the list instead of closing. The approved design (`docs/superpowers/specs/2026-10-24-rest-entry-redesign-design.md`, §2–§8) restructures the surface into two explicit layers.

## What Changes

- Relabel the place card button 等待 → 休息 (icon, `data-testid="place-card-wait"`, and class unchanged); update its readout to `休息` over `保持清醒等待，或入睡恢復精力` and the help overlay text.
- Layer 1: a new `TimeChoiceCard` with two tiles, `1 等待` and `2 睡眠`, each with a hint and a client-known context line (`現在 HH:MM`; `精力 N%（stage）` from the controlled body's fatigue row), a corner `✕`, digit/arrow/Home/End keys, a focus trap, and a locked state with the one reason `上一個行動尚未完成，請稍候。`.
- Layer 2: one shared shell (caption 等待 or 睡眠, paired corner buttons `‹ 返回上一層` and `✕ 關閉`) around a new `WaitForm` (等待直到黎明, or a duration and 等待此時長) or the existing `SleepForm`. `‹`/Escape step back to the tile the player came from; `✕` closes everything and returns focus to the place card button.
- `SleepForm` drops its inner 睡眠模式 caption; both forms centre the duration input text.
- The four dispatches keep the exact existing `explore.wait` payloads; the server contract is unchanged.
- **BREAKING (client internals, pre-release)**: retire `ExplorationMenu.waitItems()`, `frameResolver.explorationWait()`, `store.view.waitRows`, `store.activateWaitRow`, `waitCardRows`, and the `ChoiceCard` wait story args; the test ids `wait-card-row` and `rest-card` leave the exploration room card. New test ids: `wait-card-tile`, `wait-card-close`, `wait-form-card`, `rest-step-back`, `rest-step-close`, `wait-form`, `wait-form-dawn`.
- New Storybook stories `Core/TimeChoiceCard` (default, locked, no fatigue row, narrow) and `Action/WaitForm`, registered in `component-manifest.json`. `RestForm.vue` and its `Action/RestForm` story stay.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-room-actions`: the place card button becomes 休息; the wait card becomes a two-layer rest entry (tiles, then a shared-shell form); readout, controls reference, Tab-order text, and the retired-surface list change.
- `webclient-exploration-menu`: "The waiting surface offers exactly three operations" describes the tiles and layer-2 forms instead of three rows plus a back row.
- `webclient-frame-resolution`: the wait card no longer reads builder rows through an accessor; the back-row example moves to the suggestions card.
- `webclient-contextual-hud`: the place card's room-action scenarios name the 休息 button.
- `webclient-desktop-shell`: the exploration-root keyboard scenario names the 休息 button.
- `webclient-component-showcase`: the required story states replace the choice card's wait and locked-wait states with the time choice card and wait form stories.

`dream-sleep-surface` does not name the wait card or its rows, so it gets no delta. `webclient-pointer-activation` describes "the wait card's rest-duration form" as a modal form outside the row model; that still holds for the layer-2 forms, so it gets no delta.

## Impact

- Client only: `web/webclient-app/` (`AppClient.vue`, `composables/use-room-actions.js`, `stores/elosern/room_actions.js`, `stores/elosern.js`, `stores/frame-resolvers.js`, `components/PlaceCard.vue`, `components/SleepForm.vue`, new `components/TimeChoiceCard.vue` and `components/WaitForm.vue`, `components/exploration-readout.js`, `lib/controls-reference.js`, stories, `component-manifest.json`) and `web/static/webclient/js/elosern/exploration_menu.js`.
- Tests: Vitest (`tests/waiting_surface.test.js`, `tests/app_client_room_actions.test.js`, store and resolver tests, new component tests), the Node gate (`exploration_menu.test.js`), the Storybook manifest evidence tests, and browser tests and helpers that open the wait card or the rest form.
- Docs: `docs/development/webclient-vue-frozen-contract-audit.md` §2.3, and the two player-doc sentences that describe the web client's 等待 card (`docs/game/commands.md` and the `wait` entry of `docs/game/command-reference.md`).
- No server, payload, or `explore.wait` validator change.

## Batch:

depends-on: none

- Independent of `rename-reserve-to-energy`. The new tile text already reads 精力.
- Code-conflict note: both changes edit `docs/game/commands.md` and `docs/game/command-reference.md`, on different lines (this change: the web-client 等待 card sentences in the 等待 paragraph and the `wait` entry; the other: the 精神儲備 occurrences). No other file is shared. Whichever lands second rebases with a textual merge only.
