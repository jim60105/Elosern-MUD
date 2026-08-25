## Why

This is change **H3** of the WebClient Contextual HUD Redesign, governed by
`docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` (depends on: **H1**,
`webclient-hud-01-shell-and-scene`, which is landed and archived; it runs parallel to **H2**, roadmap
§6 `H2 ∥ H3`).

H1 built the stage and gave the dock its own anchor: `[data-anchor="dock"]` is `left:0; right:0;
bottom:46px; height:var(--dock-h); z-index:5` (`components/HudFrame.vue:172-178`), and `--dock-h`
(`clamp(150px, 22vh, 184px)`) is live in `tokens.css:109` after being defined and referenced by
nothing for the whole Vue migration. What mounts into that anchor is still the migration's dock:
`ActionDock.vue` is a `flex-direction:column` box that prints one static guidance line
(`方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令`) above a `DockMenu` whose cells are
`repeat(auto-fill, minmax(150px, 1fr))` equal-width text buttons, with the suggestions section
stacked underneath. There are no icons, no count badges, no tabs, and — the load-bearing omission —
**no breadcrumb at all**: at router depth 3 (Interact → a target → its keywords) nothing on screen
names where the player is, and the only way back is Escape or the trailing back cell.

The draft is a different surface. `docs/design/elosern-redesign/index.html:756-880` renders the dock
as an icon tab bar with count badges (`互動 2`, `建議 4`, `技能 87`), a `.crumb` line carrying a back
chevron and the `parent › current` trail, and a *vocabulary* of panes rather than one grid: the exit
outlet (`.outlet` — direction glyph over destination name), navigation rows (`.ngrid .nrow` — icon,
name, sub-line, `›` chevron), suggestion cards (`.sugs .sug`), target-affordance panes (`.aff` with
its `對 X 可作：` head), and — in combat — the participant token frame plus the skill master-detail
(`.skcats` → `.sklist` → `.skdetail` → `.scales` → `.tgt` → `.cast`).

H3 rebuilds the dock as that surface **without touching the navigation model underneath it**. The
rows still come from the preserved KeyboardRouter's current frame (`store.view.combatMenu.items` +
`store.view.dockDepth`), pointer focus still mirrors into `focusItemByKey`, and `#action-dock` stays
the one persistent node it is today. Every visual level in the draft that is not already a router
frame is *made* one, so the tab bar, the breadcrumb and the panes are three renderings of one state
instead of a second navigation model racing Escape.

## What Changes

- **The dock becomes a floating panel.** `ActionDock.vue` fills H1's `dock` anchor with a
  `max-width:1180px` centred panel: the draft's upward gradient
  (`linear-gradient(0deg,#0c0a0e,#141019 70%,var(--panel))`), a `--line` top border and an upward
  shadow, laid out as a fixed-height bar + crumb + one flex-`1` scrolling pane. The `#action-dock`
  id, its `tabindex`, its `data-mode` attribute and its role as the documented focus target are
  byte-identical.
- **The root frame renders as the icon tab bar.** The exploration root (Move / Look / Interact /
  Character / Quests / Inventory / Wait) and the combat root (攻擊 / 技能 / 道具 / 防禦 / 逃跑 /
  投降) are drawn as tabs with an inline decorative SVG glyph and, where a truthful count exists, a
  count badge. The focused/open tab takes the draft's seal-red gradient fill. The tab bar **is** the
  root frame's row container: same `data-item-key`, same `role="option"`, same preserved
  `#combat-row-<i>` ids.
- **A breadcrumb appears at depth ≥ 2.** The preserved `KeyboardRouter` gains one additive read-only
  accessor, `trail()`, returning each stacked frame's `title`; the menu builders in
  `exploration_menu.js` / `combat_menu.js` gain that `title` (for a target frame, the target's own
  `display_name`, which those frames already carry). The store publishes `view.dockTrail`, and the
  crumb renders `parent › current` with a back chevron that calls the same `focusEscape()` path the
  Escape key uses. The crumb is hidden at depth 1.
- **The panes gain the draft's vocabulary,** all rendered by one shared row renderer:
  - **exit outlet** — the direction glyph over the destination name. This fixes an observed defect:
    the shipped move submenu labels rows with the raw exit identifier (`north`), because
    `exploration_menu.js:200` sets `label: row.label` and never reads `row.destination`. H3 renders
    the canonical direction as the glyph and resolves the destination *name* by joining
    `exploration.move[].destination` (a node id) against the committed `local_map.nodes[].label`.
  - **navigation rows** — icon, name, a backed sub-line, and the `›` chevron on rows that open a
    deeper frame.
  - **target-affordance pane** — the `對 <目標> 可作：` head above the affordance rows, with the
    target name taken from the frame's own `target.display_name`.
  - **suggestion cards** — the existing `ChoiceCardRow` / `OptionCard`, re-chromed to the `.sug`
    card and moved into their own pane (see below).
- **`建議` becomes a real root row.** Today the suggestions section is stacked under the menu frame;
  in a 150–184px dock there is no room for both. The exploration root gains an eighth item keyed
  `suggestions` whose frame's rows are the cards, the `✕ 清除建議` row (`options.dismiss`, `{}`) and
  a back row — so the cards become keyboard-reachable router rows for the first time, the tab's
  badge is the true card count, and `generating` / `degraded` / zero-card-degraded keep their exact
  existing copy. `unavailable` renders no tab at all, matching today's "renders nothing".
- **Combat gains the participant token frame.** A new `hud-left` island, combat-only, renders
  `participants[]` split into 我方 / 敵方 with each participant's token, display name, `hp_current /
  hp_maximum`, state, and — uniquely in combat — a real portrait resolved through
  `art.portrait_catalog[portrait_ref]`. While it is mounted it is the sole presenter of the portrait
  catalog, so `ArtPanel`'s standalone catalog strip is absent in combat.
- **Combat skills become a master-detail.** `Skills` opens a category frame (the draft's `.skcat`
  chips, each with its owned-skill count), a category with more than one sub-group opens a group
  frame, and the skill frame lists that group's rows with cost and the disabled reason beside a
  detail pane (`data-testid="combat-detail"`, preserved) that names the focused skill, its
  description, its cost and its target spec. The existing 威力 scale step and target step are
  re-chromed as the draft's `.scales` and `.tok` token row; the 2-step forfeit confirm is re-chromed
  as the warning panel with 取消 / 確認投降. No payload changes: `combat.cast` still carries
  `skill_key` plus `target_ids` / `target_shorthand` and optional `scale`, `combat.forfeit` still
  carries `session_id`.
- **The combat root's grid geometry is corrected.** `combat_menu.js:359` declares `gridCols: 5` for a
  six-item root, so ArrowRight wraps `投降` onto a second geometric row that no longer exists once the
  root is a single-row tab bar. The root's column count becomes its item count (1 in `recovery`).
- **BREAKING (test-facing only):** the dock's internal DOM changes. `#action-dock`,
  `#combat-row-<i>`, `data-item-key`, the `action-*` / `target-*` item keys and
  `data-testid="dock-menu"` (which now always marks whichever container is the active listbox) are
  preserved; `exploration-detail`, `combat-detail`, `suggestions-section`, `action-dock-guidance` /
  `action-dock-description` and the dock's structural selectors are re-mapped in this change.

## Capabilities

### New Capabilities

None. H3 introduces no capability: the dock's behaviour belongs to `webclient-contextual-hud`, the
capability H1 created and archived, and is delivered as `## ADDED Requirements` against it. None of
H1's five landed requirements is modified — H3 satisfies the mode × surface matrix and the anchor
model rather than restating them.

### Modified Capabilities

- `webclient-contextual-hud` (**ADDED**, not modified): the floating dock panel and its icon tab bar
  with truthful count badges; the router-derived breadcrumb; the pane vocabulary (exit outlet, target
  rows, target-affordance pane, suggestion cards) and its truthful-sub-line rule; the combat
  participant token frame; and the combat skill master-detail with its scale, target and forfeit
  steps.
- `webclient-desktop-shell`: the required-surfaces requirement's dock sentence is re-expressed for
  the floating dock — the seal-red frame becomes the tab bar's active-tab fill, the guidance line
  moves into the tab bar's trailing hint slot (naming the same shortcuts), and "submenus render as an
  item grid beside a detail pane" becomes the pane vocabulary plus the crumb. The keyboard-routing
  requirement's exploration-root list gains the eighth `suggestions` key.
- `webclient-pointer-activation`: the frame-rendering requirement is re-expressed so the root frame
  may render as the tab bar while a deeper frame owns the pane, with the ancestor tab as inert
  chrome; the composite-widget requirement is re-expressed so exactly one row container is the
  listbox and the single tab stop at any depth, and so a pointer click on a non-current tab is
  admitted only as router operations (pop to the root frame, focus, confirm).
- `webclient-combat-menu`: the combat dock hierarchy requirement gains the category → group → skill
  master-detail (replacing "Skills SHALL open the complete active-skill list"), the single-row tab
  geometry, the participant frame, and the forfeit confirm's rendered form.
- `webclient-exploration-menu`: the exploration dock requirement's rendering sentence is re-expressed
  for the tab bar + panes, gains the `suggestions` root entry, and gains the move row's canonical
  「direction glyph + destination name」 rendering.
- `webclient-character-creation-ui`: the creation browser-acceptance requirement is re-expressed so
  the single persistent `#action-dock` node is explicitly the floating dock panel, which renders
  neither tab bar nor crumb in creation mode.
- `webclient-options-surface`: **all four** of its requirements move with the pane. The section
  requirement becomes the suggestions *pane* reached from the `建議` tab — same four statuses, same
  copy, same `options.dismiss` envelope, with the dismiss control as a row instead of a corner button
  and a deterministic focus rule replacing "without resetting the keyboard router". The shared-card
  requirement gains the dock's row form (option role, row identity) beside the choice-point's plain
  button, from the same one component. The envelope requirement is re-expressed because a dock-hosted
  card now *does* traverse the router path and is *not* individually tab-focusable — the current text
  states the opposite for both — while every dispatched envelope is unchanged. The zero-card
  empty-state requirement is re-expressed for the pane body.
- `webclient-component-showcase`: **no delta.** H1 already added the frozen-set growth rule
  (`spec.md:170`); H3 extends the manifest under it and ships each new component's story first.

## Impact

- **New:** `web/webclient-app/components/DockTabBar.vue`, `DockBreadcrumb.vue`,
  `SkillDetailPane.vue`, `ParticipantFrame.vue`; the pure modules `components/dock-icons.js` (the
  fixed glyph table keyed by stable server keys) and `components/dock-panes.js` (pane-kind
  classification, badge counts, direction-glyph and destination-name resolution); their Storybook
  stories and Vitest suites; four `component-manifest.json` entries (`Action/DockTabBar`,
  `Action/DockBreadcrumb`, `Action/SkillDetailPane`, `Data/ParticipantFrame`), taking the frozen set
  from H1's 29 to 33 — H2 independently takes it to 32, so the two waves' manifest edits must land
  serially (roadmap §7).
- **Modified:** `components/ActionDock.vue` (box → floating panel + bar + crumb + pane),
  `components/DockMenu.vue` (one grid → pane vocabulary, still one row container),
  `components/DockMenuItem.vue` (one cell → row variants), `components/OptionCard.vue` /
  `ChoiceCardRow.vue` (`.sug` chrome + a row mode so a card can be a listbox option),
  `components/ArtPanel.vue` (yield the catalog to the participant frame in combat), `AppClient.vue`
  (mount the participant frame in the `hud-left` slot, pass the trail and the pane kind),
  `stores/elosern.js` (publish `view.dockTrail`), and the preserved menu logic
  `web/static/webclient/js/elosern/keyboard_router.js` (additive `trail()`),
  `exploration_menu.js` (menu `title`s, the `suggestions` root row and its frame, the move row's
  destination fields), `combat_menu.js` (menu `title`s, category/group frames, root `gridCols`).
- **Re-mapped browser assertions (12 files):** `test_browser_exploration.py` and
  `test_browser_shell.py` and `test_browser_pointer.py` (`exploration-detail`),
  `test_browser_combat.py` (`combat-detail`, `dock-menu`), `test_browser_art.py`
  (`#combat-row-0` — preserved, re-verified against the tab bar at depth 1),
  `test_browser_options_surface.py` and `test_browser_choicepoints.py` (`suggestions-section` →
  the pane; the choice-point's own `option-card` usage is unchanged), `test_browser_services.py`
  (`dock-menu`, `services-confirm`), `test_browser_layout.py` and `browser_helpers.py`
  (`#action-dock` focus forwarding now lands on the active row container),
  `test_browser_creation.py` and `test_browser_input_narrative.py` (`#action-dock` presence and
  focus-return, asserted unchanged). `#action-dock` itself does not move in any of them.
  `test_browser_pointer.py`'s `.quest-board__action` step is **not** H3's: it targets the right-column
  QuestBoard and moves with H4.
- **Preserved / untouched:** the server, all eight presenters, the action allowlist, the OOB
  envelope, `transport.js`, `bridge.js`, the dispatch/echo path, the epoch and revision gates, the
  offline overlay, `#action-dock` / `#combat-row-<i>` / `data-item-key` / the `action-*` and
  `target-*` key contract, the router's key semantics (arrows, Enter, Escape-pops-one, Space,
  `/`), and the dependency-free text fallback.
- **H2 boundary:** H3 does not edit `StatusPanel.vue`, `LocalMap.vue`, `CharacterHead.vue`,
  `VitalsTrack.vue` or `ConditionChips.vue`. The participant frame is a new component slotted into
  the same `hud-left` anchor; the two waves share only `AppClient.vue`'s slot list and
  `component-manifest.json`.
- **Not built (no backing read model, roadmap §2.4):** the draft's `戰鬥外` skill badge
  (`SkillDef.usable_out_of_combat` exists at `world/rules/action.py:273` but is serialized into no
  panel), the look-row stat sub-line 「攻/敏/防·魔階·生命」 (`look.entities[]` carries only
  `identity`, `display_name`, `kind`), and portraits on exploration target rows (`portrait_ref` is
  hard-forced `null` at `web/webclient/presentation/exploration.py:224-225,283-284`). Each is named
  in the extended `tests/overlays/deferred_surfaces_absent.test.js` with the field it waits on.
