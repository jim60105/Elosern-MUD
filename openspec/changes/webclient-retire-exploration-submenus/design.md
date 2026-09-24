## Context

See proposal.md (Why). The state after C8b (`webclient-scene-overview-swap`):

- `exploration.root` resolves `overviewMenu`, and `exploration.target` resolves `verbMenuFor`. `exploration.move/look/interact` are still registered in `stores/frame-resolvers.js` and in `EXPLORATION_SUBMENU_PUSHES` (`stores/elosern/frames.js`), but no production path pushes them (C8b task 2.4).
- `overviewMenu` (C8a D1) calls `moveItems` and `lookItems` and strips what the chips do not need: the back rows, the `move-empty` placeholder, and the `（無法通行）` suffix.
- `DockMenu.vue` still carries the `outlet` pane:
  - `outletRows`, `outletSpanCol`, the auto-fit grid style, and the tile template
  - the `aria-activedescendant` clause that skips the outlet `back`
  - the detail suppression for `outlet`
- `dock-panes.js` `classifyPane` still returns `outlet`, and `badgeCount` still serves `interact` / `suggestions`. `DockTabBar` renders only the combat root since C8b, so only `skills` is ever asked for.
- `interaction.js` `focusPress` binds `"1"`–`"4"`. It excludes the outlet `back` through `classifyPane`, and routes to `handleCaptionDialoguePick(slot)` while the dialogue variant presents.
- `DockBreadcrumb.vue` takes `focusedKey` only to draw `dock-crumb__back--focused` when the router focuses the outlet's non-rendered `back`.
- `use-dock.js` `dockItems` normalizes `direction` / `destination` for the outlet.
- The frameworks C8b left for tests: `test_browser_contextual_hud_dock.py` reaches the outlet by a direct `pushFrame({source: "exploration.move"})`, and `test_browser_exploration_tiles.py` pins the outlet grid.

## Goals / Non-Goals

**Goals:**
- Every piece listed above is deleted, and every reachable path is unchanged.
- Digits 1–9 work in every dock frame and for dialogue picks, and the legend says so.

**Non-Goals:**
- `targetMenuFor`, `keywordMenuFor`, `waitItems`, `suggestionsMenu`, `targetById`, `scriptedAffordanceFor`, and `normalizeDirection` stay. They are live.
- `DockTabBar`, `rootItems` in `use-dock.js` (the combat root), and `tabToRootAndConfirm` (top navigation and combat tabs) stay.
- No change to the combat digit semantics beyond the wider range.

## Decisions

### D1. `moveItems` / `lookItems` become chip builders, not deleted
The overview still needs exactly their payload logic: `current_node`, `commandDisplay`, `direction`, `destination`, and the look target ids. They lose:
- the trailing `backItem()` and the `move-empty` placeholder
- `moveItems`' `（無法通行）` label suffix

`overviewMenu` drops its stripping code. `buildMenus` keeps only `wait` and `suggestions`, so `explorationModel()` in the resolver still serves `exploration.wait` and `exploration.target` (through `targetById`). `rootItems`, `interactItems`, `parentKeyFor`, and `openItem` are deleted; `parentKeyFor` has no caller outside its own test.

*Alternative:* inline the builders into `overviewMenu`. Rejected: it is a larger diff, and the Node tests for payload shape would have to move for no gain.

### D2. Unregistered sources resolve to the marker
Deleting the three resolver entries makes any stray `exploration.move/look/interact` descriptor resolve to `UNRESOLVABLE`, which pops it. `frame-resolvers.test.js` replaces their cases with one table-driven "unregistered" case, as `retire-service-keyboard-frames` did for `services.*`.

### D3. Digits 1–9
`focusPress` claims `key.length === 1 && key >= "1" && key <= "9"`, then:
- `slot = Number(key) - 1`
- dialogue picks first, unchanged, but now up to slot 8
- then `menu.items[slot]` with no outlet filter, because every rendered frame now renders its `back` as a row

For the overview, `menu.items` is the reading order (C8a D1), so the slots match what the player sees. Disabled entries take slots, as the 1–4 rule already did, so a digit's target never shifts with enabled state.

The dialogue variant's picks: `webclient-dialogue-session` allows up to 16 scripted keywords, so picks 1–9 become addressable and 10–16 stay pointer-reachable, as 5–16 were before.

*Conflict check:* no other surface binds `5`–`9`. C3 deleted the quick-word letter bindings, and the command field is editable, so the bridge never routes digits typed there.

### D4. Breadcrumb
`DockBreadcrumb` drops `focusedKey` and the focused class. The rule becomes: a `back` item is always a row of its frame and carries the row's focus treatment. `DockMenu` already renders `back` rows for nav, cards, and affordance panes, and `DockVerbPopover` renders them as `DockMenuItem`s.

### D5. Tests
- `test_browser_exploration_tiles.py`:
  - `test_outlet_and_nav_tiles_stay_within_the_pane_at_a_narrow_viewport` becomes an overview chip-wrap test (12 exits in a 1280x720 command region, no horizontal overflow, the last chip reachable by scrolling), annotated to the C8b exploration-dock ID.
  - Its nav-pane half (a keyword frame with a fixed column count) keeps the new fixed-column ID.
  - `test_outlet_last_row_never_leaves_blank_space_at_a_narrower_viewport` is deleted with the rule it pinned.
- `test_browser_contextual_hud_dock.py`: the pane-vocabulary test's direct outlet push becomes overview assertions (glyph + destination, disabled label + marker, reason strip).

## Risks / Trade-offs

- [A stray push site of `exploration.move/look/interact` survives] → Task 2.1 greps before deleting, and D2 makes any survivor pop harmlessly.
- [Digits 5–9 change behaviour in combat frames with more than four rows] → This is intended: one rule for every frame, as the legend states. `digit_row_picks.test.js` covers a combat skill frame.
- [Removing the `（無法通行）` suffix changes the disabled exit text] → The shared `（無法使用）` marker plus the reason strip replace it (C8a D4); C8a's tests already assert the chip text.

## Migration Plan

None. Archive order: **C7 → C8a (`webclient-scene-overview-component`) → C8b (`webclient-scene-overview-swap`) → C8c (this change)**. The legend, pointer current-frame, and direct-children blocks are written on C8b's text. The pane-vocabulary and breadcrumb blocks are written on the main spec; no series change before this one modifies them.
