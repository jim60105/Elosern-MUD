# Rest Entry Redesign Design

**Date:** 2026-10-24
**Status:** Design approved in brainstorming; interaction prototype in `docs/design/time-choice-redesign/`. Split into two OpenSpec changes (§9); implementation not started.
**Scope:** Restructure the surface the place card's 等待 button opens into two explicit layers: first choose 等待 or 睡眠, then set how long. Rename the button to 休息, give every layer a visible way out, and shorten the player-facing term 精神儲備 to 精力.

The place card's 等待 button opens a `ChoiceCard` captioned 等待 with three rows: 1 等待直到黎明, 2 睡眠至完全恢復, 3 等待 N 小時, then `✕ 返回`. Row 2 does not sleep; it opens the 睡眠模式 form (`SleepForm`: 睡眠至完全恢復 or a duration). Row 3 opens `RestForm` (a duration). Under that list sit four actions on two axes, mode (stay awake or sleep) by end condition (an until-state or a duration), and the list shows none of that structure. It mixes the two modes, names the whole card after one of them, and labels a row 睡眠至完全恢復 when the row only opens a form. Neither form has a visible close control: Escape is the only way back, and it returns to the list instead of closing.

**Visual reference:** the interaction prototype is committed at [`docs/design/time-choice-redesign/`](../../design/time-choice-redesign/):

- `TimeChoicePrototype.vue`: the whole flow over a stage backdrop, using the real `PlaceCard`, the real `SleepForm`, and the `ChoiceCard` frame.
- `WaitFormPrototype.vue`: the new wait form.
- `TimeChoicePrototype.stories.js`.

Storybook loads it under `Design/TimeChoiceRedesign` with the stories `Choice`, `WaitForm`, `Sleep Form`, `Locked`, `NoFatigueData`, `Narrow`, `Closed`, and `FullReserve`. Run `npm run serve-storybook` and open `?path=/story/design-timechoiceredesign--choice`.

The prototype is the source of truth for geometry, colors, and feel. It is reference only: it reads no payload, sits outside the component-coverage manifest, and is not imported by the app. It relabels the real `PlaceCard` button through the DOM and hides `SleepForm`'s inner caption with CSS; the implementation changes those components instead (§5). Where this document and the prototype disagree on behavior, this document wins.

## 1. Authority and Constraints

- The server contract does not change. Every action is the existing bounded `explore.wait` intent with one of the four payloads it already accepts: `{daypart: "dawn"}`, `{seconds}`, `{sleep: true}`, `{sleep: true, sleep_mode: "duration", seconds}`.
- The server-owned sleep handoff, dream question, and continuation surfaces that follow an accepted sleep are unchanged.
- The wait side offers only 等待直到黎明 as its until-state. The server also accepts `midnight`, `noon`, and `dusk`; they stay out of scope.
- The lock rule is unchanged: while a mutation is in flight or awaiting its declared revision, or the session is not live (`skipDisabled`), no option acts, and the one reason is `上一個行動尚未完成，請稍候。`.

## 2. Player Decisions and Flow

The player answers two questions in order: whether to stay awake or sleep, then until when or for how long.

```
place card 休息
  └─ Layer 1 「度過時間」: [1 等待] [2 睡眠]                 ✕
       ├─ 等待 → Layer 2 「等待」  ‹                          ✕
       │     等待直到黎明              → explore.wait {daypart: "dawn"}
       │     或指定時長（小時）＋等待此時長 → explore.wait {seconds}
       └─ 睡眠 → Layer 2 「睡眠」  ‹                          ✕
             睡眠至完全恢復            → explore.wait {sleep: true}
             或指定時長（小時）＋以此時長入睡
                                    → explore.wait {sleep: true, sleep_mode: "duration", seconds}
```

| Control | Effect | Focus afterwards |
|---|---|---|
| Place card 休息 | Opens layer 1 | The 等待 tile |
| Tile, `1` / `2` | Opens that tile's layer 2 | The form's duration input (autofocus) |
| Layer 1 `✕`, layer 1 Escape | Closes everything | The place card 休息 button |
| Layer 2 `‹`, layer 2 Escape | Returns to layer 1 | The tile the player came from |
| Layer 2 `✕` | Closes everything | The place card 休息 button |
| A dispatched action | Closes everything (as today) | The existing opener return; sleep then hands over to the server sleep surfaces |

## 3. Layer 1: Choice Tiles (`TimeChoiceCard.vue`, new)

Two large tiles side by side inside the `choice-card` frame (corners, crest, caption). It is not a row list, and it holds no inputs.

**Content**

| Element | 等待 tile | 睡眠 tile |
|---|---|---|
| Badge (top left) | `1` | `2` |
| Icon (24-unit line SVG, stroke 1.6) | open eye | crescent moon with a star |
| Label | 等待 | 睡眠 |
| Hint | 保持清醒，讓時間流逝 | 入睡，恢復精力 |
| Context line | `現在 HH:MM`, the clock part of `store.view.statusSlice.timeLabel` | `精力 N%（stage label）` from the controlled body's `panels.status.fatigue[]` row (`reserve_percent`, `label`) |

- The visible caption is 度過時間 (`aria-hidden`); the dialog's accessible name is 等待或睡眠 from a visually hidden heading.
- A context line is omitted when its source is absent (no time label, or no fatigue row for the controlled body). The tile keeps its other content.
- The context line never wraps: `white-space: nowrap`, with the numerals in the mono face and the stage label in the sans face. The default card width is `min(100%, calc(460px * var(--ui-scale)))`. The widest current line, `精力 100%（精神充沛）`, fits on one line. All stage labels are four characters (精神充沛, 輕度疲勞, 中度疲勞, 重度疲勞, 強制睡眠) except 沉睡.
- Hierarchy: icon and label (`--text-xl`, `--paper-50`), hint (`--paper-300`), context (`--gold-400`, under a faint gold rule).
- Below `calc(320px * var(--ui-scale))` of anchor width the tiles stack. Each becomes a horizontal tile: icon on the left, text in the middle, badge on the right. They are still tiles, not rows.
- A corner `✕` at the top right uses `QuestionCard`'s close button styling and SVG, with `aria-label` 關閉並回到探索 and `title` 關閉.
- Data comes from what the client already has; the card shows nothing the client cannot read. Hours until dawn and whether the place is safe are known only to the server and are not shown.

**States**

- Rest: a faint gold gradient fill with a `rgba(185,154,96,.35)` border.
- Hover and focus: a `--gold-500` border and a stronger fill; focus adds a 2px `--gold-400` ring, and the badge turns into the solid gold fill the active `ChoiceCard` badge uses.
- Locked: both tiles get `aria-disabled="true"`, stay focusable, and draw a dashed border, a dashed badge, and the icon and label in `--paper-400`. A `role="status"` line under the tiles reads `上一個行動尚未完成，請稍候。`, and both tiles reference it through `aria-describedby`. Digits and Enter do nothing.

**Semantics and keys**

- Outer `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing at the hidden heading. Each tile is a real `<button>` with `aria-describedby` pointing at its hint and context.
- `1` / `2` pick a tile; `←` `→` (and `↑` `↓`) move focus between the tiles and wrap; `Home` / `End` jump to the first or last tile; `Enter` / `Space` activate natively; Escape closes everything; Tab is trapped in the card (`✕` and the two tiles).
- The component is presentational: it emits `pick("wait" | "sleep")` and `close`. It adds no action id.
- Its entrance follows `ChoiceCard`'s `entrance` prop and the motion-level setting.

## 4. Layer 2: Shared Shell, Wait Form, Sleep Form

**Shared shell.** The two `section.choice-card.rest-card` blocks in `AppClient.vue` become one shell with:

- `choice-card__corners`;
- a visible caption naming the mode, 等待 or 睡眠, carrying an id for `aria-labelledby` (no longer `aria-hidden`);
- the form;
- after the form in DOM order, so Tab walks the form first, two absolutely placed corner buttons that pair visually: `‹` at the top left (`aria-label` and `title` 返回上一層) and `✕` at the top right (`aria-label` 關閉並回到探索, `title` 關閉), both in the `QuestionCard` close-button style.

The shell is `role="dialog"` and `aria-modal="true"` and traps Tab across the form controls and the two corner buttons. Escape inside the form steps back, because the forms already claim Escape and emit `close`; Escape on a corner button also steps back.

**Wait form (`WaitForm.vue`, new).** It mirrors `SleepForm` element for element:

1. A button 等待直到黎明, which emits `dawn`.
2. A label 或指定時長（小時） over a number input (`aria-label` 等待時長（小時）, default `1`, min one second, max `max / 3600`, `step="any"`).
3. A hint 最長 12 小時，可輸入小數。
4. An error line on an invalid entry: `請輸入有效時長，最短 1 秒、最長 12 小時。`.
5. A submit button 等待此時長, which emits `submit(seconds)`.

It takes `max` (default 43200), `autofocus`, and `disabled`, and it validates exactly as `SleepForm` does.

**Sleep form (`SleepForm.vue`, changed).** Drop the inner `<p class="exploration-sleep-caption">睡眠模式</p>`, because the shell caption names the form, and drop both duplicate `.exploration-sleep-caption` rules. Everything else is unchanged.

**Both forms.** The duration input text is centred (`text-align: center`). Inside the shell, a form sits flat: transparent background and no border, as `.rest-card .exploration-rest-form` does today.

`RestForm.vue` stays; `stores/elosern/interaction.js` still uses it. Only the exploration room card stops using it.

## 5. Other Surface Text

| Where | Today | New |
|---|---|---|
| `PlaceCard.vue` button label | 等待 | 休息 |
| `PLACE_WAIT_READOUT` (`components/exploration-readout.js`) | `{lead: "等待", text: "讓時間流逝、休息或睡眠"}` | `{lead: "休息", text: "保持清醒等待，或入睡恢復精力"}` |
| `lib/controls-reference.js` (help overlay, place card entry) | 打開等待卡片：等待直到黎明、睡眠至完全恢復、等待 N 小時。… | 打開休息卡片：先選「等待」或「睡眠」，再選等待直到黎明、睡眠至完全恢復，或指定時長。… Keep the existing sentences about the sleep handoff, and state the ‹ and ✕ behavior. |

The place card button keeps its hourglass icon, its `data-testid="place-card-wait"`, and its class `place-card__action--wait`.

## 6. Wiring (`composables/use-room-actions.js`, store)

- The room card kind stays `"wait"`, so the store slice, `openRoomCard("wait")`, `closeRoomCard`, the opener-focus return, and the Tab chain stay as they are.
- The view-local `waitStep` becomes `null | "wait" | "sleep"`: `null` shows the tiles, and the others show that layer 2 form. The remembered tile for the return is the step just left.
- Handlers: `onTilePick(key)` sets the step; `onStepBack()` clears the step and focuses the remembered tile; `onStepClose()` calls `store.closeRoomCard()`. `onWaitDawn()` dispatches `explore.wait {daypart: "dawn"}` and `onWaitSubmit(seconds)` dispatches `explore.wait {seconds}`, both through `dispatchIntent` like the existing sleep handlers. The sleep handlers stay.
- Retire the builder path the list used: `ExplorationMenu.waitItems()`, `frameResolver.explorationWait()`, `store.view.waitRows`, `store.activateWaitRow`, and `waitCardRows`. Their only consumers are this card and the `scene_overview` story fixture. `openRoomCard("wait")` keeps its availability gate as the same exploration-panel check `explorationWait` makes today (null when the panel is unavailable), expressed directly.
- The tile context reads `store.view.statusSlice.timeLabel` and the status panel's fatigue row for the controlled body. They are passed to `TimeChoiceCard` as props and are never fetched by it.

## 7. Test Ids

| Element | Test id |
|---|---|
| Layer 1 card | `wait-card` (keeps `data-card-kind="wait"`) |
| Tile | `wait-card-tile` with `data-tile="wait"` or `"sleep"` |
| Layer 1 `✕` | `wait-card-close` |
| Layer 2 shell | `wait-form-card` or `sleep-card` |
| Layer 2 corners | `rest-step-back`, `rest-step-close` |
| Wait form | `wait-form`, with `wait-form-dawn` on its first button |
| Sleep form | unchanged (`sleep-form`, `sleep-form-recovery`) |

`wait-card-row` and `rest-card` retire from the exploration room card. `docs/development/webclient-vue-frozen-contract-audit.md` §2.3 is updated to match.

## 8. Testing

- Unit (`tests/waiting_surface.test.js`, `tests/app_client_room_actions.test.js`, and new component tests):
  - The tiles render with the hints, and each context line appears only when its source exists.
  - `1` / `2`, the arrows, `Home` / `End`, and Enter pick or move as specified, and Tab stays trapped.
  - Locked tiles are `aria-disabled`, carry the reason, and ignore digits and Enter.
  - Each of the four actions dispatches exactly its payload and closes the card.
  - Escape and `‹` step back to the tile the player came from; `✕` in either layer closes and returns focus to `place-card-wait`.
  - `WaitForm` validates like `SleepForm`.
  - `SleepForm` no longer renders 睡眠模式.
- Storybook: a `Core/TimeChoiceCard` story set (default, locked, no fatigue row, narrow) and an `Action/WaitForm` story, both registered in `component-manifest.json`.
- Browser (`web/tests/browser/test_browser_exploration_actions.py` and the helpers that use `wait-card` / `rest-card`): the place card → tile → form → dispatch path for one wait action and one sleep action; `✕` closes from each layer.

## 9. OpenSpec Split

1. **`redesign-rest-entry`** (`webclient-room-actions`, and `dream-sleep-surface` where it names the wait card): §2–§8. Client only.
2. **`rename-reserve-to-energy`**: replace the player-facing term 精神儲備 with 精力 everywhere a player reads it. That covers the status panel row (`StatusPanel.vue`), the travel depletion message (`world/rules/travel_cost.py`), the handoff candidate suffix (`world/rules/possession.py`), and the player docs (`docs/game/commands.md`, `docs/game/command-reference.md`), together with the tests that assert those strings. Code comments, rulebook comments, and internal identifiers may keep the old term. Stage labels such as 精神充沛 are unchanged. The change is independent of change 1; change 1's tile reads 精力 either way, because it is new text.
