## Context

See proposal.md (Why). The current state was checked in code. C1 to C7 are assumed archived first.

- `web/static/webclient/js/elosern/exploration_menu.js` (UMD, Node-tested) builds the exploration keyboard menus from the validated `exploration` panel:
  - `rootItems` is the tab root. It holds 移動/查看/互動/角色狀態/任務/背包/等待/休息/建議; the store's resolve hook filters out `character`, `quests`, and `inventory`.
  - `moveItems`, `lookItems`, `interactItems`, `waitItems`, `targetMenuFor`, `keywordMenuFor`, and `suggestionsMenu`.
  - `buildMenus` assembles `model.menus`.
  - `targetMenuFor` maps `explore.talk_scripted` (enabled → `openKeywords`), `explore.talk_freeform` (`freeform`), `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.deliver` (server `params`), and `navigate` (`openDrawer: "quest" | "shop"`). It ends with the back row. Other action ids (the possession pair) are not mapped.
- `keyboard_router.js` knows two geometries:
  - `grid` with a fixed `gridCols` (row-major wrap)
  - a list (Up/Down cycle, Left/Right no-ops)

  `projectFocus` keeps a frame's `focusKey` across re-resolution and falls back to the nearest index. `currentMenu()` returns the resolved menu object, so extra fields such as `sections` reach `store.view.combatMenu` untouched.
- `DockMenu.vue` owns `DIRECTION_GLYPHS` / `directionGlyph` and `destinationLabel(item)`, which reads `props.view.localMapModel.nodes`. The outlet tile markup is a `role="option"` button with a glyph, a bold headline, and a hidden reason.
- The `exploration` panel (v2) carries:
  - `move[]`: `exit_ref`, `label`, `destination`, `enabled`, `disabled_reason`
  - `look.room`: `identity`, `display_name`
  - `look.entities[]`: `identity`, `display_name`, `kind`, `portrait_ref`. These are every present character, NPC, or monster.
  - `look.objects[]`
  - `interact[]`: NPC and monster targets only, with `affordances` and scripted `keywords`

  Present characters that are not NPCs or monsters therefore appear only in `look.entities`.
- The manifest and showcase governance (C3) allow the AVG series to add components. Adding one requires the story, the manifest title, and the spec in the same change.

## Goals / Non-Goals

**Goals:**
- Pure, Node-tested `overviewMenu` and `verbMenuFor` whose output is exactly what C8b's resolvers will return.
- A router geometry that makes arrow keys follow the rendered chip rows without any DOM measurement.
- `SceneOverview` and `DockVerbPopover` fully built, storied, and tested. C8b only wires them.

**Non-Goals:**
- Any resolver, store, `AppClient.vue`, `ActionDock.vue`, or CSS-in-`app-shell.css` change (C8b).
- Deleting `moveItems` / `lookItems` / `interactItems` / `rootItems` / `targetMenuFor`, or the outlet pane (C8c). `targetMenuFor` stays and `verbMenuFor` delegates to it, so C8c keeps one mapping.
- Digits and the legend (C8c).

## Decisions

### D1. The overview is one menu with a `sections` index, not nested menus
`overviewMenu` returns a single flat `items` array in reading order plus
`sections: [{key, label, count}]`, where the counts sum to `items.length` and a zero-count section is omitted.

- **Item shapes** reuse the existing builders so payloads stay byte-identical:
  - Exit chips are `moveItems(panel, currentNode)` minus the back row and minus the `move-empty` placeholder (the section is omitted instead). A disabled chip's `label` is reset to the server `label` without the `（無法通行）` suffix, because `DockMenuItem` renders the disabled marker (D4).
  - Object chips are the `object-*` rows of `lookItems`.
  - Entity look chips are `lookItems`' `entity-*` rows filtered to identities absent from `panel.interact`.
  - `look-room` is `lookItems`' room row. It is rendered only when `look.room` exists, which is always true for an available panel.
- **Person chips** (`target-<identity>`) are always enabled with `openTarget: identity`. The popover always has at least 查看, so a target with no mapped affordance is no longer a dead disabled row. Today `interactItems` disables it with 此對象沒有可用的互動。
- **Footer:**
  - `wait` is `{key: "wait", label: "等待／休息", openSubmenu: "wait"}`.
  - `suggestions` is `{key: "suggestions", label, openSubmenu: "suggestions"}`, present exactly when the status is not `unavailable` (today's root rule). Its label is `建議 (N)` with N = `suggestions.cards.length` when the status is `ready` or `degraded` and N > 0. `generating` and zero cards give `建議`.

  The footer always has at least `look-room` and `wait`, so it is never empty.
- `title` is `場景`. It is the breadcrumb's root segment once the overview is the root.

*Why flat:* the router, the digit rule (C8c), `focusItemByKey`, and the pointer path all address rows by index and key. One array keeps those unchanged, and `sections` is only geometry and layout metadata.

*Alternative:* four sub-menus composed in the view. Rejected: the router has one menu per frame, and the design keeps the overview as ONE root frame.

### D2. `verbMenuFor` = `targetMenuFor` plus 查看
`verbMenuFor(model, target)` calls `targetMenuFor`:
- It drops the `target-empty` placeholder when present.
- It inserts `{key: "look-target", label: "查看", actionId: "explore.look", payload: {target_id: target.identity}, commandDisplay: {targetLabel: target.display_name}}` before the back row.
- It returns `{items, focusKey: null, target, title: target.display_name}`.

It carries no `grid` / `gridCols`, so the popover is a vertical list, which the router already supports.

The 交談 seam stays `targetMenuFor`'s `explore.talk_scripted` branch, the one branch C9 changes.

The possession pair stays unmapped, exactly as today. Surfacing it is not part of the design's §7.

### D3. Router geometry `sections`
A menu with `geometry === "sections"` and a `sections` array is treated as a list for projection (`focusRow = index`). In `move()`:
- **Left/Right:** `index ± 1` modulo `items.length`.
- **Up/Down:**
  - Locate `(s, ordinal)` from the cumulative counts, pick `t = s ∓ 1` modulo the section count, and land on `start(t) + min(ordinal, count(t) − 1)`.
  - With one section, Up/Down return false.
  - If the counts disagree with `items.length` (a programmer error), the menu falls back to list behaviour rather than throwing, so a bad model never wedges the keyboard.

*Why ordinal, not visual column:* the router is DOM-independent by contract. Rows wrap by width, so the visual column is unknowable, while the ordinal is deterministic and testable in Node.

*Alternative:* treat the overview as a grid with `gridCols` = the widest row. Rejected: sections have different lengths and wrap. A fixed column count would land on empty cells or on the wrong row.

### D4. `SceneOverview.vue`
- **Props:**
  - `menu` (the resolved overview menu, exactly `view.combatMenu` at the root in C8b)
  - `focusedKey`
  - `localMap` (the `localMapModel`, for destination names)
  - `idPrefix` (default `"exploration-row"`)
  - `active` (default `true`)
- **Emits:** `focus-change(key)`, and `activate({key, item})` for enabled chips only.
- **Markup:**
  - The root is `div.scene-overview` (`data-testid="scene-overview"`).
  - Inside it, one listbox `div.scene-overview__list` with `role="listbox"`, `aria-label="場景"`, and `aria-activedescendant`. While `active` it also carries `tabindex="0"` and `data-testid="dock-menu"`, so it is the surface's single tab stop, as the root tab bar is today. While inactive it carries `tabindex="-1"`.
  - One `div.scene-overview__row[data-section]` (`data-testid="scene-overview-<key>"`) per section. The row has a `<span class="scene-overview__label">` (none for the footer) and a `div.scene-overview__chips` using `flex-wrap: wrap`.
  - The footer row carries a top rule and `·` separators drawn in CSS.
- **Chip:** every chip is a `DockMenuItem` (`itemKey`, `label`, `enabled`, `reason`, `focused`, `rowId = <idPrefix>-<i>`), with the class `scene-chip` for the compact chip styling. The pointer-activation requirement's "one shared renderer" therefore holds without a second row markup.
  - `DockMenuItem` gains an optional `glyph` prop. When it is set, the item renders `<span class="dock-menu-item__glyph" aria-hidden="true">` before the label. Every existing caller passes none and renders unchanged.
  - Exit chips pass `glyph = directionGlyph(direction)`. Their label follows the outlet's headline rule: the destination name when the chip is enabled, the direction is canonical, and the destination is known; otherwise the item's own label.
  - A disabled chip shows `（無法使用）` from `DockMenuItem`.
- **Reason strip:** `p.scene-overview__reason` (`data-testid="exploration-detail"`) renders only while the focused chip is disabled and has a reason. That keeps the pointer-activation rule (a disabled activation surfaces its explanation) without a detail pane.
- **Scrolling:** on `focusedKey` change (`flush: "post"`) the focused chip calls `scrollIntoView({block: "nearest", inline: "nearest"})`. The component itself does not scroll. The dock pane (`.action-dock__pane`) is the single scrolling region (C4a).
- **Inactive:** when `active` is false, the root gets `inert` and `aria-hidden="true"`, and drops the `dock-menu` hook.

### D5. `DockVerbPopover.vue`
- **Props:** `menu` (the resolved verb menu), `focusedKey`, `idPrefix` (default `"exploration-row"`).
- **Emits:** `focus-change`, `activate`, `back`.
- **Markup:**
  - The root is a full-size transparent layer `div.verb-popover-layer` (`position: absolute; inset: 0`) that catches outside presses and emits `back`.
  - Inside it, `section.verb-popover` (`data-testid="verb-popover"`, `role="dialog"`, `aria-label="<name> 的行動"`) is anchored `left: 8px; right: 8px; bottom: 8px; max-height: calc(100% - 16px); overflow-y: auto`.
  - It holds a head `h3.verb-popover__head` with the target name, and a listbox (`data-testid="dock-menu"`) of `DockMenuItem` rows in menu order, the back row last.
  - Pointer presses on the card stop propagation.

*Why bottom-anchored, not chip-anchored:* the command panel is fixed-size and scrolls. Anchoring to the chip would need DOM geometry and scroll tracking, and it would clip near the panel's edges. A bottom sheet inside the panel is always fully visible and deterministic. The overview stays visible above it, inert (D4).

### D6. `dock-exits.js`
It moves `DIRECTION_GLYPHS`, `directionGlyph`, and `destinationLabel` out of `DockMenu.vue` (the null-prototype table kept). `destinationLabel` takes `(item, localMapModel)`. `DockMenu` passes `props.view?.localMapModel`, so the outlet is unchanged. C8c deletes the outlet, and the helper stays for the overview.

### D7. Stories bind the derived shape
`stories/fixtures/scene_overview.js` exports:
- `explorationPanelFixture({exits, targets, entities, objects})`
- `overviewArgs(panel, {currentNode, suggestions, localMap})`, which calls `ExplorationMenu.overviewMenu` through `lib/exploration_menu.js`
- `verbArgs(panel, identity)`, which calls `verbMenuFor`

Stories:
- `SceneOverview`: `FullRoom`, `EmptyRows` (exits and footer only), `DisabledExit` (focused, reason strip shown), and `Overflowing` (12 exits, 10 people, in a 300px-tall box).
- `DockVerbPopover`: `DialogueHost` (交談, 交易, 查看), `HostileTarget` (戰鬥, 查看), and `LookOnly`.

Each popover story is decorated with a positioned 640×300 box showing a `SceneOverview` with `active: false` underneath.

## Risks / Trade-offs

- [Up/Down by ordinal can feel off when a long exit row wraps into two visual lines] → It is deterministic, and Left/Right always reach every chip. Digits (C8c) give direct access to the first nine. The rule is stated in the spec (C8b) so tests pin it.
- [Unmounted components can drift before C8b wires them] → C8b is the next change in archive order, and the story fixtures run the real builders, so a model change breaks the stories' tests.
- [Person chips for targets with no affordance used to be disabled] → The chip now opens a popover with 查看 only. This is intentional (decision accepted by the coordinator) and visible only after C8b.

## Migration Plan

None. Nothing is mounted.

Archive order: **C7 (`webclient-typewriter-reading-prefs`) → C8a (this change) → C8b (`webclient-scene-overview-swap`) → C8c (`webclient-retire-exploration-submenus`)**. This change's manifest requirement is written on C6c's text. No other series change modifies "The action-dock family presents a finite, keyboard-and-pointer-actionable contract".
