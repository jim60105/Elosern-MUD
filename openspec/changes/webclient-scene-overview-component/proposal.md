## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §7) found the exploration flow fragmented. After moving, the player must switch to the `互動` tab to learn who is in the room, and exits, people, and objects each hide behind their own tab (`移動 / 查看 / 互動`). The design replaces the tab root with one scrollable scene overview in the fixed command panel:

- an 出口 row of exit chips
- a 人物 row of people chips
- a 物件 row of object chips
- a footer with 查看房間 · 等待／休息 · 建議 (N)

A person chip opens a verb popover inside the panel.

This is the first of three changes. It builds the pieces the swap needs without mounting them:

- the overview and verb-menu builders in the DOM-independent exploration-menu model
- a section-aware arrow geometry in the keyboard router
- the two governed components, with their stories and manifest entries

The component-showcase governance ("a component SHALL NOT be wired into the live application before its story exists") makes build-then-mount the intended order, the same order C6b/C6c used. It also keeps `webclient-scene-overview-swap` (C8b) inside one day.

## What Changes

- `web/static/webclient/js/elosern/exploration_menu.js` gains two builders. Neither is called by any resolver or store yet.
  - `overviewMenu(panel, {currentNode, suggestions})` returns one menu `{items, sections, geometry: "sections", title: "場景"}`. Items are in reading order:
    - **出口:** `exit-*` chips with the existing move-row payload, direction, and destination. Disabled rows are kept with their reason, and their label is the plain exit label: the chip renderer adds the disabled marker, so no `（無法通行）` suffix is baked in.
    - **人物:** `target-*` chips for every `interact` target, always enabled and carrying `openTarget`. They are followed by `entity-*` look chips for `look.entities` that have no `interact` descriptor.
    - **物件:** `object-*` look chips.
    - **Footer:** `look-room`, `wait` (`openSubmenu: "wait"`, label `等待／休息`), and `suggestions` (`openSubmenu: "suggestions"`) whenever the suggestions status is not `unavailable`. Its label is `建議 (N)` when the ready or degraded envelope carries N > 0 cards, otherwise `建議`.
    - `sections` lists `{key, label, count}` for each non-empty row: `exits` 出口, `people` 人物, `objects` 物件, and `footer` with a null label.
  - `verbMenuFor(model, target)` returns the target's affordance rows in payload order, with the same mapping `targetMenuFor` uses today. It appends a `look-target` 查看 row (`explore.look {target_id}`) and ends with the standard back row. A target with no mapped affordance yields 查看 and back only.
- `web/static/webclient/js/elosern/keyboard_router.js` gains the `geometry: "sections"` menu form.
  - The frame's focus index is its reading-order index, as in a list.
  - ArrowLeft/ArrowRight move to the previous/next item in reading order and wrap across the whole menu.
  - ArrowUp/ArrowDown move to the same ordinal in the previous/next section (clamped to that section's last item), wrapping across sections. With a single section they are no-ops.
  - Grid and list menus are unchanged.
- New shared helper `web/webclient-app/components/dock-exits.js`. It exports `directionGlyph(direction)` and `destinationLabel(item, localMap)`, moved verbatim out of `DockMenu.vue`, which now imports them. The move outlet renders byte-identically.
- New governed component `web/webclient-app/components/SceneOverview.vue`.
  - Renders the overview menu as labelled chip rows plus a separated footer. Chips wrap, and empty rows are absent.
  - Every chip is a `DockMenuItem`, the dock's shared row renderer, so the chip keeps these from the one shared definition:
    - the `data-item-key` identity and the row id
    - the focused fill
    - the focusable disabled state with its `（無法使用）` marker and its `aria-describedby` reason
  - `DockMenuItem` gains one optional `glyph` prop, a decorative leading glyph hidden from assistive technology. Exit chips use it for the direction glyph and show the destination name as their label.
  - A one-line reason strip (`data-testid="exploration-detail"`) shows the focused chip's server-authored reason while that chip is disabled.
  - The row container carries `role="listbox"`, `aria-activedescendant`, row ids `<idPrefix>-<i>`, and `data-testid="dock-menu"` while it is `active`. It is `inert` and `aria-hidden` while it is not.
  - The focused chip is scrolled into view with `block: "nearest"`.
  - Emits `focus-change` and `activate`.
- New governed component `web/webclient-app/components/DockVerbPopover.vue`.
  - A card anchored to the bottom edge of its positioned host, with a head naming the target and its own listbox of `DockMenuItem` rows. It carries `data-testid="dock-menu"` and `data-testid="verb-popover"`.
  - A pointer press outside the card but inside the host emits `back`.
- Stories `web/webclient-app/stories/Action/SceneOverview.stories.js` and `DockVerbPopover.stories.js`. Their args are bound through one shared helper, `web/webclient-app/stories/fixtures/scene_overview.js`, that runs the real `overviewMenu` / `verbMenuFor` over a synthesized exploration panel (the showcase derived-shape rule).
- `component-manifest.json` gains `Action/SceneOverview` and `Action/DockVerbPopover`. So do the four showcase-evidence manifest snapshots.
- Nothing is mounted. No store, resolver, OOB schema, presenter, server, or persistence change, and no player-visible change.

Out of scope:
- Mounting the overview as the exploration root, the popover as the `exploration.target` frame, the return-to-overview after movement, the combat-only tab bar, and relocating the shortcut legend: `webclient-scene-overview-swap` (C8b).
- Deleting the move / look / interact frames, the interaction workspace, and the exploration badges; digits 1–9 and the legend wording: `webclient-retire-exploration-submenus` (C8c).
- Swapping the 交談 affordance to `explore.talk_open`: `explore-talk-open-action` (C9).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-component-showcase`:
  - "Every required UI component is a Vue SFC with a documented Storybook story", on C6c's text: the manifest names the scene overview and its verb popover.
  - "The action-dock family presents a finite, keyboard-and-pointer-actionable contract": the family includes the scene overview's chips and the verb popover's rows.

## Impact

- New:
  - `web/webclient-app/components/SceneOverview.vue`, `DockVerbPopover.vue`, `dock-exits.js`
  - `web/webclient-app/stories/Action/SceneOverview.stories.js`, `DockVerbPopover.stories.js`, `stories/fixtures/scene_overview.js`
  - Vitest `web/webclient-app/tests/action/scene_overview.test.js`, `dock_verb_popover.test.js`
- Edited:
  - `web/static/webclient/js/elosern/exploration_menu.js`, `keyboard_router.js`
  - `web/static/webclient/js/tests/exploration_menu.test.js`, `keyboard_router.test.js`
  - `web/webclient-app/components/DockMenu.vue` (helper import only), `DockMenuItem.vue` (optional `glyph` prop)
  - `web/webclient-app/component-manifest.json`
  - `web/webclient/tests/test_vue_showcase_{action,data,world,overlays}_evidence.py`
  - `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js` (its manifest list)
- Spec traceability: no ID changes.
- Dependencies:
  - Archive order: C7 (`webclient-typewriter-reading-prefs`) → C8a (this change) → C8b → C8c.
  - The manifest block is written on C6c's (`webclient-message-window-swap`) text.
