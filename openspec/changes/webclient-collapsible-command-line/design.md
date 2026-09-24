## Context

See proposal.md (Why). The current state was checked in code. C1, C2, C3, C4a, C4b, and C4c are assumed archived first.

- `components/CommandLine.vue` renders `div.cmdline` (`data-testid="command-line"`, 46px):
  - the prompt, then `#inputfield` (a `textarea`) and its send button inside `.inputfieldwrapper`
  - the hint `↑↓ 歷史 · Tab 補全` and the 上一筆 / 下一筆 history buttons
  - `span.cmdutil`: 技能系譜 (`command-line-lineage`, `open-overlay` `lineage`), 圖鑑 (`command-line-lore`, `open-drawer` `lore`), 稱號冊 (`command-line-codex`, `open-overlay` `codex`), 設定 (`command-line-settings`), 說明 (`command-line-help`), and, after C3, 角色肖像圖庫 (`gallery-opener`, behind the `galleryAvailable` prop)

  `submit()` emits `submit` and clears the draft only when `connected && !mutationsLocked && !inFlight`. Escape emits `focus-parent`, and blur emits `focus-lost`. `defineExpose` keeps `focusField` (C3 deleted `insertText`).
- `components/AppShell.vue`:
  - mounts `CommandLine` in HudFrame's `command-line` slot
  - exposes `focusCommandField()` (calls `focusField`), `releaseCommandField(restoreFocus)` (calls `restoreDockFocus`), and `restoreDockFocus()` (`#action-dock`.focus())
  - `onWindowKeydown` only suppresses the default of `/` outside editable controls; `HIDDEN_BY_MODE` drives the pre-flush focus rescue on a mode change
- `/` travels through the bridge (`bridge.js` `onDocumentKeydown`, skipped for editable targets), then `keyboard_router.js` (`SLASH` → `emit("toggle-drawer")`), then `stores/elosern/frames.js` (`ctx.drawerRequest += 1`), then `composables/use-shell-focus.js` (a watch on `store.view.drawerRequest` → `shellRef.focusCommandField()`).
- The free-form borrow uses the same counter:
  - `stores/elosern/interaction.js` `borrowDialogueCommand` (the dialogue variant's free-dialogue row) and `handleExplorationItem`'s `item.freeform` branch set `ctx.freeformTarget` and bump `drawerRequest`
  - `stores/elosern/transport.js` `sendText` dispatches `explore.talk_freeform` for a set target, and bumps `drawerCloseRequest` only when `dispatchAction` returns a request (`sent !== null`)
  - `use-shell-focus.js` maps `drawerCloseRequest` to `releaseCommandField(true)`
- After C4a, `HudFrame.vue`'s `command-line` anchor is `left: var(--left-column); right: 33.3333%; bottom: var(--band-h); height: var(--command-line-h)`, with `--command-line-h: 64px` in `styles/tokens.css`. Other consumers of the token:
  - `--stage-content-bottom` (`calc(var(--band-h) + var(--command-line-h))`)
  - `HudDrawer.vue` (`top: var(--command-line-h)`)
  - `OverlayHost.vue` (inset bottom `calc(var(--command-line-h) + 12px)`)
  - `app-shell.css` `--workspace-bottom`
  - `ToastQueue.vue` (`max-height`)
- `components/DesktopNavigation.vue` (after C4b) renders one `<nav class="desktop-navigation" aria-label="主要導覽">` at `left: var(--left-column)`, 48px tall. It holds the server navigation entries (`navigationItems`, keys in `NAVIGATION_ITEM_KEYS`), 地圖 (not in combat), and 設定 (`$emit('overlay', 'settings')`). Its row buttons are icon plus label (`padding: 0 14px`, 18px icon). The nav stops Enter and Space propagation, so the bridge never claims them. Help (`help`) has no top-bar control today, although the desktop-shell requirement already lists help among the bar's controls.
- `composables/use-overlays.js` `openOverlayByName` captures `document.activeElement` as the opener. `use-drawers.js` `onOpenDrawer` calls `store.openHudDrawer`.
- `#inputfield` is a preserved DOM contract (`AppShell.vue` header comment, `tests/preserved_contract.test.js`). The layout store (`web/static/webclient/js/elosern/layout_store.js`) keeps a `command-drawer` component entry whose `id` is `inputComponent`. It stores dimensions only and has no open/closed state.

## Goals / Non-Goals

**Goals:**
- The command line is collapsed by default and opens on `/`, the ⌨ toggle, or the free-form borrow. It closes on Escape or an accepted send, and focus returns to `#action-dock`. A rejected send leaves it open with its text.
- The expanded row is 44px on the message region's top edge. It covers neither the band nor the message text.
- The five openers stay one pointer action and one Tab stop away with the line collapsed.
- The `#inputfield` contract and the single send path are unchanged.

**Non-Goals:**
- The message window, its paging, and its 日誌 control (C6). The ⌨ toggle only reserves the bottom-right corner that C6 builds around.
- The dialogue stage's choice list and its `⌨ 自由對話` row (C10). This change only routes the existing borrow through the expand path.
- Expand and collapse motion (C11).
- The latent mismatch between `CommandLine`'s accept predicate (`connected && !mutationsLocked && !inFlight`) and `dispatchAction`'s (which also requires `phase === "active"`). It predates this change, and this change does not widen it (see Risks).
- Renaming the store's `drawerRequest` / `drawerCloseRequest` counters. Their meaning (open and close the command line) is accurate again, and only their comments change.

## Decisions

### D1. Collapsed means the anchor is `display:none`, and `CommandLine` stays mounted
`AppShell` holds `const commandLineExpanded = ref(false)` and passes it to `HudFrame` as `commandLineExpanded`. HudFrame renders `:data-expanded="commandLineExpanded ? 'true' : 'false'"` on `[data-anchor="command-line"]`, and its CSS adds `[data-anchor="command-line"][data-expanded="false"] { display: none; }`.

Why the anchor, not the bar inside it: the anchor is the absolutely positioned box. Hiding only `.cmdline` would leave an empty positioned box that still takes part in the browser tests' anchor-intersection checks.

*Alternatives rejected:*
- **Not mounted (`v-if`).** `#inputfield` would leave the DOM, which breaks the preserved contract (`preserved_contract.test.js`) and the layout store's `command-drawer` evidence (`test_browser_layout.py` `COMPONENT_SELECTORS` counts `[data-testid="command-line"]`). Every collapse would also lose the Escape-kept draft, the history-walk backup, and the Tab-completion cycle.
- **Zero height or `visibility`.** A zero-height bar keeps its buttons and field in the tab order and the accessibility tree, which breaks the design's §4 rule that hidden surfaces use `display:none`.

Consequences:
- `focus()` on a `display:none` element is a no-op in browsers. Every expand path must render first and focus second (D2).
- The collapsed field is never `document.activeElement`, so the bridge's `isEditable` test and the router's `/` claim keep working unchanged: a collapsed line never swallows keys.

### D2. One expand path, one collapse path, both in `AppShell`
The expand path:

```
async function focusCommandField() {
  commandLineExpanded.value = true;
  await nextTick();
  commandLine.value?.focusField();
}
```

All three entrance paths already converge here:
- `/` and the borrow through `drawerRequest` → `use-shell-focus.js`
- the ⌨ toggle through a direct call

`focusCommandField` stays the shell's single focus API, and no new store counter is added.

The collapse path is `releaseCommandField(restoreFocus)`: `restoreDockFocus()` first (so the field's `blur` fires `focus-lost` and releases the borrow), then `commandLineExpanded.value = false`. It is reached from:
- Escape (`focus-parent`)
- `CommandLine`'s new `sent` event (D3)
- the store's `drawerCloseRequest` watcher (borrowed success, unchanged in `use-shell-focus.js`)
- the mode watcher when `nextMode === "creation"`, after the existing `HIDDEN_BY_MODE` rescue

Collapsing twice is harmless.

The ⌨ toggle calls `focusCommandField()` when collapsed. When expanded it sets `commandLineExpanded = false` without moving focus: the pointer already moved focus to the toggle, and a keyboard user on the toggle keeps it there.

Blur does not collapse. Clicking the stage, opening a drawer, or opening an overlay leaves the row as it was, so a pointer user can click back into a half-typed command. The design lists only Escape and a successful send as collapse triggers.

### D3. "Successful send" is the field's own accept predicate
`CommandLine.submit()` already decides, in one place, whether the draft is cleared (`connected && !mutationsLocked && !inFlight`). It now emits `sent` at exactly that point, after `submit`. `AppShell` maps `sent` to `releaseCommandField(true)`.

The line therefore collapses exactly when the field clears, and a rejected send stays open with its text and focus. That covers "a mutation lock or an in-flight send keeps the text" for both ordinary text and the borrowed path.

For an accepted borrowed send, both `sent` and `drawerCloseRequest` fire. The second collapse is a no-op.

*Alternative rejected:* using the store's return value. `sendText` returns `true` for every borrowed send, rejected or not, and a Vue emit cannot return a value to its emitter. Moving the decision into the store would change the store contract for no behavioural gain.

### D4. Expanded geometry: 44px, same anchor box
`styles/tokens.css` sets `--command-line-h: 44px`. `CommandLine.vue`'s `.cmdline` uses `height: 100%` instead of `46px`, and `.cmdfield` / `.inputfield` keep 34px, which fits the 44px row with 5px padding.

The C4a anchor rule is unchanged: `left: var(--left-column); right: 33.3333%; bottom: var(--band-h)`. The row therefore overlays the stage strip above the message region and never the band text (design §5.1, §5.5).

Every other consumer follows the token:
- `--stage-content-bottom` still clears the expanded row, so the backdrop captions never sit under it.
- `HudDrawer`'s top inset becomes 44px, 2px closer to the reference's `.draw{top:46px}`.
- `OverlayHost` and `--workspace-bottom` lose 20px of bottom gap.

No consumer is rewritten. `tests/hud_drawer.test.js` asserts the `var(--command-line-h)` expression, not a pixel value, and stays valid.

### D5. The ⌨ toggle is an `AppShell` sibling in the band-message region
`AppShell`'s `#band-message` template renders `NarrativeFeed` and, after it:

```
<button type="button" class="command-line-toggle" data-testid="command-line-toggle"
        aria-label="指令列" title="指令列 (/)" aria-controls="command-line-bar"
        :aria-expanded="commandLineExpanded ? 'true' : 'false'"
        @click="onToggleCommandLine" @keydown.enter.stop @keydown.space.stop>⌨</button>
```

`CommandLine`'s root gets `id="command-line-bar"`.

`app-shell.css` places the toggle at `position: absolute; right: 22px; bottom: 18px; width: 30px; height: 30px; z-index: 1` inside `[data-anchor="band-message"]`, which C4a made `position: relative`. `[data-anchor="band-message"] .narrative-scroll` gets `padding-bottom: 36px`, so the latest line scrolls clear of the toggle and the text is never covered.

The `.stop` modifiers copy `DesktopNavigation`'s guard: without them, the document-level bridge would also route a Space on the toggle into the dock router.

Why `AppShell` and not `NarrativeFeed`: C6 replaces `NarrativeFeed` with `MessageWindow` in the same slot. The toggle is shell chrome tied to the shell's `commandLineExpanded` state, so it must survive that swap. C6 adds its 日誌 control beside it (design §5.1 `[日誌] [⌨]`).

The toggle lives in the message region, so the creation-mode `display:none` on `band-message` (C4a) hides it with no extra rule.

### D6. The utility cluster moves to the top bar as an icon tool group
`DesktopNavigation.vue` appends, after 設定:

```
<div class="desktop-navigation__tools" role="group" aria-label="工具" data-testid="nav-tools">
  <button … aria-label="技能系譜" title="技能系譜" data-testid="nav-tool-lineage" @click="$emit('overlay','lineage')">
  <button … aria-label="圖鑑"     title="圖鑑"     data-testid="nav-tool-lore"    @click="$emit('drawer','lore')">
  <button … aria-label="稱號冊"   title="稱號冊"   data-testid="nav-tool-codex"   @click="$emit('overlay','codex')">
  <button v-if="galleryAvailable" … aria-label="角色肖像圖庫" title="角色肖像圖庫" data-testid="gallery-opener" @click="$emit('overlay','gallery')">
  <button … aria-label="說明"     title="說明"     data-testid="nav-tool-help"    @click="$emit('overlay','help')">
</div>
```

- The icon SVGs move verbatim from `CommandLine.vue`. The gallery button gets a portrait-frame glyph, because it had text only.
- The buttons are 38px wide and the bar's full 48px tall, with an 18px icon. A 1px `--line` divider sits before the group.
- The existing 設定 button gains `data-testid="nav-settings"`.
- `DesktopNavigation` gains the `galleryAvailable` prop and a `drawer` emit. `AppClient.vue` binds `:gallery-available="panelAvailable('gallery')"` and `@drawer="onOpenDrawer"`, and deletes C3's `galleryAvailable` bindings on `AppShell` / `CommandLine`.
- `onOpenOverlay` already captures the opener, so focus return is unchanged.

Why the top bar, and the 48px budget:
- The design's top bar (§5.1, §5.4) is the one strip visible in every playing mode that never covers the stage. The ⌨ corner of the message window is reserved for reading controls (C6's 日誌). Five more icons there would crowd a surface whose inner width is paging input.
- A compact icon strip left on the stage (for example, beside the ⌨) would put permanent chrome back over the art, which the design removes ("reference data is one click away … never permanently on screen").
- A single "more" menu button would cost two pointer actions.

At 1280x720 (`--left-column` 216px):
- The nav starts at 216px. Worst case: three navigation entries plus 地圖 and 設定 as icon-and-label buttons of at most about 101px each (14 + 18 + 7 + four 12px glyphs + 14), which ends near 721px. The divider and five 38px tools add 199px, ending near 920px.
- The top-right cluster (`.topbar-right`: `right: 18px; max-width: calc(var(--right-column) + 50px)` = 294px) begins no further left than 968px.
- The worst-case margin is therefore about 48px. In combat, 地圖 is absent and the margin grows.

C4b's switcher gain (location and time left the top-meta) is what makes this room. Task 5.4 measures it with a maximum-length name.

Why icon-only: the cluster was already icon-only with `aria-label`s. Labels on five more buttons (at least 77px each) would not fit at 1280. `title` restores the visible label on hover, and the accessible name is unchanged.

Why the command line's 設定 is deleted, not moved: the bar already has 設定. Two openers for one overlay in one bar would be noise.

*Alternative rejected:* the 角色 drawer as the home for lineage and codex. C3 D5 rejected the same idea for the gallery: `openOverlay` closes the drawer first, which detaches the opener and breaks focus return.

### D7. Mode interplay
- **Combat and dialogue.** The expanded or collapsed state survives the mode change. The player may be typing when combat starts, and dialogue shows the same line (design §4 "same").
- **Creation.** The line collapses, and focus is rescued first by the existing `HIDDEN_BY_MODE` rule, which already names `[data-anchor='command-line']`. Returning from creation starts collapsed.
- **Overlays and drawers.** Opening one does not collapse the line. Focus-trap restore returns focus to the opener, which is the nav tool button, not the field.

### D8. Help text and comments
In `lib/controls-reference.js`:
- `/` becomes "Open the command line" / "Expands the collapsed line and focuses its field; no literal slash is inserted."
- Enter's detail adds "a successful send collapses the line and returns to the dock".
- Esc's precedence detail reads "open overlay → open drawer → focused command field (collapses the line) → dock menu level".

The "permanently present" comments are rewritten in `AppShell.vue`, `CommandLine.vue`, `use-shell-focus.js`, `frames.js` (`toggle-drawer`), `interaction.js` (`borrowDialogueCommand`), `transport.js` (the `drawerCloseRequest` comment), and `HudDrawer.vue` / `HudDrawer.stories.js` (44px).

### D9. Spec strategy, traceability, and archive order
Each MODIFIED block is written on the latest series text:

| Requirement | Written on top of |
|---|---|
| contextual-hud "Surface visibility is gated by the committed game mode" | C4c `webclient-avg-stage-hud-anchors` |
| contextual-hud "The map, settings, and help surfaces are reachable from the live client" | C3 `webclient-retire-redundant-hud` (which carries C2's map clause) |
| desktop-shell "Required desktop surfaces remain visible and usable" | C4b `webclient-avg-place-card-top-bar` |
| input-narrative "A deliberate mutation echo appears exactly once at dispatch" | C3 (its ADDED text) |
| desktop-shell "Keyboard routing is menu-first and submission-safe", pointer-activation "Keyboard input is dispatched through the WebClient plugin contract", browser-verification "Browser acceptance covers foundation recovery and layout behavior" | main spec (no series change touches them) |

Three requirements change subject, so each is REMOVED and ADDED:

| Old ID | New ID |
|---|---|
| `webclient-contextual-hud::the-command-line-is-a-permanently-present-bar-in-the-stage-s-command-line-anchor` (last modified by C4a) | `…::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge` |
| `webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control` (last modified by C3; its first scenario "…with no opening action" cannot survive a MODIFIED) | `…::the-collapsible-command-line-preserves-ordinary-text-control` |
| `webclient-lore-codex-panel::the-codex-opens-from-the-command-line-utility-strip-not-from-the-quest-drawer` | `…::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer` |

The gallery-control clause of the removed contextual-hud requirement moves into the new desktop-shell requirement "The top navigation bar carries the tool group", whose ID is new.

Annotations to re-anchor (from `grep -rn` of the old IDs):
- the command drawer: `web/tests/browser/test_browser_input_narrative.py` (3), `test_browser_shell_command_line.py` (5), `test_browser_exploration_dialogue.py` (1), `web/webclient/tests/test_node_suite_evidence.py` (2)
- the permanent bar: `test_browser_input_narrative.py` (1)
- the codex: `test_browser_contextual_hud_drawers.py` (4)

All other requirement IDs are unchanged.

`openspec validate` reports that archive would refuse the input-narrative MODIFIED block: its requirement exists only after C3 is archived. That is expected, and it is why this change must be archived after C3.

**Archive order: C1 → C2 → C3 → C4a → C4b → C4c → C5 (this change).** If any of those blocks changes before archive, this change's block for that requirement must be re-synced, keeping only this change's edits.

## Risks / Trade-offs

- [About 66 browser-test uses of `#inputfield` assume a visible field] `page.fill` and `click` wait for visibility, so they would time out against a collapsed line. → Task 5.1 adds `open_command_line(page)` to `browser_helpers.py`: press `/` with focus on the dock, then wait for `#inputfield` to be focused. Every hit from `grep -rn "inputfield\|command-line-input-field" web/tests/browser` is classified: it either opens first, asserts the collapsed state, or is presence-only (`count()`), which keeps working. `REQUIRED_SURFACES` swaps `[data-testid="command-line"]` for `[data-testid="command-line-toggle"]`.
- [Consecutive-command journeys now need `/` before each command] This is the design's intent (§5.5: a send returns to the command panel). → The shell journey scenarios are restated. A player typing many commands in a row pays one key per command. The design accepts this.
- [Borrowed send rejected by `phase !== "active"` while `CommandLine` clears] This mismatch predates this change: today the speech is cleared and lost in that window. Now the line also collapses, so the loss is the same and no worse. → Non-goal. It is recorded here so C10, which reworks the borrow, can close it by passing the store's full lock predicate.
- [Top-bar width at 1280 with a long name] → D6 budget with about 48px margin. Task 5.4 asserts it with a maximum-length name. If it fails, `.desktop-navigation button` drops to `padding: 0 10px` under the existing `(max-width: 1350px)` block before any tool is removed.
- [Screen-reader users lose the always-present field] → The ⌨ toggle is a named disclosure (`aria-expanded`, `aria-controls`), and `/` is announced in the help overlay. Focus lands in the field on every entrance path.
- [`browser-verification` "The minimap stays inside its island" still names a legend, which C1 removed] This change restates that requirement for the command-line clause only, and it copies that scenario unchanged. → Out of scope here (C1's area). Flagged in the series report.

## Migration Plan

None. The client is unreleased, and the expanded state is never persisted.
