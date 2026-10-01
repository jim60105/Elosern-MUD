## Context

See proposal.md for motivation. The exploration panel delivers each target's affordances; `web/static/webclient/js/elosern/exploration_menu.js::verbMenuFor` builds the person-chip verb popover (`DockVerbPopover.vue`) and maps `navigate` affordances to client-local drawers through a surface→drawer map. `use-drawers.js` and the store own a single open-drawer name with focus-trapped drawer chrome (`HudDrawer.vue`, `DrawerHeader.vue`, `lib/focus-trap.js`); `use-overlays.js` registers open surfaces for stage recession; `use-resync.js` handles reconnect; `command_echo.js` maps action ids to narrative echoes. Browser seeds live in `web/tests/browser/seed/*_fixture.py`. `.elosern-root` rules in `styles/app-shell.css` override component styles in the live client only.

## Goals / Non-Goals

**Goals:** the complete editor journey on existing primitives; correctness under late results, conflicts, departures, reconnects, and session changes; accessible keyboard operation; real-browser evidence.

**Non-Goals:** server changes (actions change); fixed-dialogue editing; name/title/stat editing; gamepad additions; a global NPC catalogue.

## Decisions

### D1. The editor is a drawer bound by value, not by selection

Opening stores `{npcId, epoch, openerKey}` in the editor composable; the drawer name `npc_persona` joins the store's closed drawer-name set and the open-surface registry. All later logic reads the bound `npcId`, never the current selection. Alternative rejected: a full-screen overlay (the design asks to reuse the drawer width and keep the interaction context visible).

### D2. Explicit state machine with request correlation

States: `loading`, `ready_clean`, `ready_dirty`, `saving`, `conflict`, `unavailable`, `rejected` (field/other error, still editable). Each dispatch records its `request_id`; a result is applied only if its `request_id` is the editor's latest outstanding request and the editor is still open for the same `npcId` and epoch. A confirmed save replaces `baseline` and `version` and returns to `ready_clean`; a field rejection sets `rejected` with the field focused; a conflict sets `conflict` with actions 重新載入 (fresh read, replaces baseline/version, keeps draft until the player chooses to discard local edits) and 放棄修改. Transport loss leaves `saving` pending without a claim; on resync the composable dispatches a fresh read, keeps the draft, and enters `conflict` if the returned version differs from the draft's base version, else returns to the prior ready state.

### D3. Departure and session rules come from committed presentation

Departure: when a committed exploration snapshot no longer lists the bound `npcId` in `interact` (or the panel becomes unavailable because the mode left exploration/dialogue), the editor enters `unavailable`, keeps the draft, and disables save; it returns to ready if the NPC reappears. Logout, puppet change, or epoch replacement closes the editor and drops all editor state (no persistence anywhere). Snapshot refreshes never touch the draft.

### D4. Budgets and validation reuse the static mirror

`web/webclient-app/lib/npc_persona_card.js` re-exports the static `npc_persona_card.js` mirror (the lib-wrapper pattern used for the other shared modules); per-control remaining counts and total remaining come from `cardBudget`, and save is disabled while `normalizeCard` rejects the draft. Text is rendered as plain text (no `v-html`).

### D5. Accessibility and focus

The drawer root is `role="dialog"` `aria-modal="true"` with `aria-labelledby` on the heading; notices are static text; errors and save results announce through an `aria-live="polite"` region; the discard confirmation is a small in-drawer alertdialog. Focus is trapped with `lib/focus-trap.js`; on close focus returns to the opener row if it still exists, else to the interaction surface root. The keyboard router ignores keys whose target is an editable control (verify the existing guard covers `textarea`; extend it if not).

### D6. No echo, no storage

`command_echo.js` registers `npc.persona.read`/`npc.persona.update` as silent (no narrative echo). The composable never writes `localStorage`/`sessionStorage`; a Vitest asserts storage is untouched across a full journey.

### D7. Evidence

Vitest: state machine, correlation, conflict, departure, dirty-close, storage. Storybook: `Overlays/NpcPersonaEditor` stories for loading, clean, dirty with budget overflow, saving, field rejection, conflict, unavailable, narrow viewport. Browser (two modules so each file stays under the five-minute CI bound): `test_browser_npc_persona_editor.py` (open/save/reopen persistence on an NPC seeded with an initialized card, keyboard-only round trip, Escape/backdrop dirty-close confirmation, field error retention, typing does not move) and `test_browser_npc_persona_editor_edges.py` (late-read correlation, target departure, puppet change clears, two-page cross-tab conflict and reload). Each method is registered in `.github/browser-shards.json`; local runs use one method per command through `web.tests.browser.unittest_driver`.

## Risks / Trade-offs

- [`.elosern-root` overrides hide live regressions in Storybook] → grep `app-shell.css` for every reused class and verify geometry in the live-client browser test, not only Storybook.
- [Two-page browser tests are slow] → keep the cross-tab case to one method with bounded deterministic waits.
- [Disabled entries before the cutover confuse players] → the server reason text explains it; user docs mention it.
