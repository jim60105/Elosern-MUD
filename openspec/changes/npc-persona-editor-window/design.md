## Context

See proposal.md for motivation. The exploration panel delivers each target's affordances; `web/static/webclient/js/elosern/exploration_menu.js::verbMenuFor` builds the person-chip verb popover (`DockVerbPopover.vue`) and maps `navigate` affordances to client-local drawers through a surface→drawer map. `use-drawers.js` and the store own a single open-drawer name with focus-trapped drawer chrome (`HudDrawer.vue`, `DrawerHeader.vue`, `lib/focus-trap.js`); `use-overlays.js` registers open surfaces for stage recession; `use-resync.js` handles reconnect; `command_echo.js` maps action ids to narrative echoes. Browser seeds live in `web/tests/browser/seed/*_fixture.py`. `.elosern-root` rules in `styles/app-shell.css` override component styles in the live client only.

## Goals / Non-Goals

**Goals:** the complete editor journey on existing primitives; correctness under late results, conflicts, departures, reconnects, and session changes; accessible keyboard operation; real-browser evidence.

**Non-Goals:** fixed-dialogue editing (scripted tables stay read-only author data); name/title/stat editing; gamepad additions; a global NPC catalogue. The one server surface here is the bounded `offline_greeting` extension of the archived editor transport (design §13a amendment).

## Decisions

### D1. The editor is a drawer bound by value, not by selection

Opening stores `{npcId, epoch, openerKey}` in the editor composable; the drawer name `npc_persona` joins the store's closed drawer-name set and the open-surface registry. All later logic reads the bound `npcId`, never the current selection. Alternative rejected: a full-screen overlay (the design asks to reuse the drawer width and keep the interaction context visible).

### D2. Explicit state machine with request correlation

States: `loading`, `ready_clean`, `ready_dirty`, `saving`, `conflict`, `unavailable`, `rejected` (field/other error, still editable). Each dispatch records its `request_id`; a result is applied only if its `request_id` is the editor's latest outstanding request and the editor is still open for the same `npcId` and epoch. A confirmed save replaces `baseline` and `version` and returns to `ready_clean`; a field rejection sets `rejected` with the field focused; a conflict sets `conflict` with actions 重新載入 (fresh read, replaces baseline/version, keeps draft until the player chooses to discard local edits) and 放棄修改. Transport loss leaves `saving` pending without a claim; on resync the composable dispatches a fresh read, keeps the draft, and enters `conflict` if the returned version differs from the draft's base version, else returns to the prior ready state.

### D3. Departure and session rules come from committed presentation

Reconnect: every transport generation retires the epoch, so a reconnect always arrives on a new epoch. The editor survives a transport loss (the store's drawer teardown exempts `npc_persona`; the composable owns its lifecycle), and when the next epoch is established for the same character (the roster's current identity, when committed, equals the one bound at open) it rebinds to that epoch and re-reads; a reconnect onto a different character closes it. Request ids restart per generation, so correlation always compares the request id AND the epoch it was dispatched on.

Departure: when a committed exploration snapshot no longer lists the bound `npcId` in `interact` (or the panel becomes unavailable because the mode left exploration/dialogue), the editor enters `unavailable`, keeps the draft, and disables save; it returns to ready if the NPC reappears. Logout (the puppet detaching), puppet change, or an epoch replacement inside the same transport generation closes the editor and drops all editor state (no persistence anywhere). Snapshot refreshes never touch the draft.

### D4. Budgets and validation reuse the static mirror

`web/webclient-app/lib/npc_persona_card.js` re-exports the static `npc_persona_card.js` mirror (the lib-wrapper pattern used for the other shared modules); per-control remaining counts and total remaining come from `cardBudget`, and save is disabled while `normalizeCard` rejects the draft. Text is rendered as plain text (no `v-html`).

### D5. Accessibility and focus

The drawer root is `role="dialog"` `aria-modal="true"` with `aria-labelledby` on the heading; notices are static text; errors and save results announce through an `aria-live="polite"` region; the discard confirmation is a small in-drawer alertdialog. Focus is trapped with `lib/focus-trap.js`; on close focus returns to the opener row if it still exists, else to the interaction surface root. The keyboard router ignores keys whose target is an editable control (verify the existing guard covers `textarea`; extend it if not).

### D5a. The offline-greeting control (override model)

Every NPC shows one optional single-paragraph control after the seven card controls, labeled 離線問候語, seeded from the read snapshot's `offline_greeting` (verbatim, `""` when unset). It carries its own 300-code-point budget from the mirror (it does NOT count toward the card's 2,000 total — it is not a card leaf). A preview line below it shows `default_greeting` as the currently-effective authored default (the dialogue-table line, else the profile line, as resolved by `world.rules.dialogue` below the instance field; 無 when empty) so the author can restore it by clearing the field. The helper states the semantics: the line is spoken as the NPC's first line only when the generative layer is offline or the player talks without a keyword; LLM dialogue always follows the card; keyword answers are unaffected. Save submits `{persona, offline_greeting}` as one payload; the server's `greeting_invalid` rejections behave like any field rejection (draft kept, field focused, announced). A greeting-only change is a dirty draft and advances `persona_version` exactly like a card edit, so conflict/reload/stale-exchange semantics are identical.

### D6. No echo, no storage

`command_echo.js` registers `npc.persona.read`/`npc.persona.update` as silent (no narrative echo), and the store's generic non-success narrative error line skips these two actions because the editor announces its own rejection in its live region. The composable never writes `localStorage`/`sessionStorage`; a Vitest asserts storage is untouched across a full journey.

### D6a. Drawer-frame extensions are additive

`HudDrawer` gains three optional props used only by the editor: `closeGuard` (a function consulted before Escape/close/scrim close; returning `false` keeps the drawer and its focus trap), `titleId` (forwarded to `DrawerHeader` and used as the dialog's `aria-labelledby`), and `bodyFlush` (drops the body padding/scroll so the editor owns a fixed notice column and its own scrolling form column). It also exposes `forceClose()` for the confirmed discard. Every existing drawer keeps its exact behavior with the props absent.

### D6b. Mirror label parity

The JS twin's `renderCardBlock`/`cardBudget` currently render different identity/life-story/social labels than `world.lore.npc_card` (so the browser total under-counts by two code points when 人脈 is empty). The editor shows these totals, so the twin is corrected to the server's exact labels and the card fixture gains `expected_total` parity cases evaluated on both sides.

### D7. Evidence

Vitest: state machine, correlation, conflict, departure, dirty-close, storage. Storybook: `Overlays/NpcPersonaEditor` stories for loading, clean, dirty with budget overflow, saving, field rejection, conflict, unavailable, narrow viewport. Browser: `test_browser_npc_persona_editor.py` (open/save/reopen persistence on an NPC seeded with an initialized card including the offline greeting and the narrative line that follows it, keyboard-only round trip, Escape/backdrop dirty-close confirmation, field error retention, typing does not move, and a single-page conflict: a bridge-dispatched update advances the version under the open editor, the editor's save shows the conflict with the draft intact, and reload/discard recover). Every new `data-testid` a browser method targets is registered in the frozen-contract audit §2.3. The slower multi-page and multi-entity edge journeys (late-read correlation, target departure, puppet change, cross-tab conflict) are `npc-persona-editor-browser-edges`; this change proves those behaviors with Vitest. Each method is registered in `.github/browser-shards.json`; local runs use one method per command through `web.tests.browser.unittest_driver`.

## Risks / Trade-offs

- [`.elosern-root` overrides hide live regressions in Storybook] → grep `app-shell.css` for every reused class and verify geometry in the live-client browser test, not only Storybook.
- [Two-page browser tests are slow] → moved to `npc-persona-editor-browser-edges`.
- [Disabled entries before the cutover confuse players] → the server reason text explains it; user docs mention it.
