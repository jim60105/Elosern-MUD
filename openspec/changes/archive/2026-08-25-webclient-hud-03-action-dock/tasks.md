## 1. Freeze the dock's preserved contract before any DOM moves

- [x] 1.1 Record the identifiers this change must not move: `#action-dock` (with its `tabindex`, `data-mode`, listbox composite role and documented focus-target status), the `#combat-row-<i>` row-id pattern, `data-item-key` with its `action-` / `target-` prefixes, the bare G2 root keys (`move`, `look`, `interact`, `character`, `quests`, `inventory`, `wait`) and the combat root keys (`attack`, `skills`, `items`, `defend`, `flee`, `forfeit`), and `data-testid="dock-menu"` — which from this change forward marks whichever container is the **active** row container
- [x] 1.2 Add a Vitest suite asserting every identifier in 1.1 survives the re-chrome at depth 1 and at depth ≥ 2, so a regression fails at the unit gate rather than in the browser suite
- [x] 1.3 Grep `web/tests/browser/` for `#action-dock`, `#combat-row-`, `exploration-row`, `exploration-detail`, `combat-detail`, `suggestions-section` and `dock-menu`, and record the 12 affected files in the change; they are re-mapped in group 8
- [x] 1.4 Record the hooks this change re-maps to `data-testid` (`exploration-detail`, `combat-detail`, `suggestions-section`, `action-dock-guidance`, `action-dock-description`) for H6's audit re-freeze

## 2. Router trail and menu-model additions (behind the Node gate)

- [x] 2.1 Add the read-only `trail()` accessor to `web/static/webclient/js/elosern/keyboard_router.js`, returning each stacked frame's `menu.title` in push order; change no existing member and no push/pop/escape behaviour
- [x] 2.2 Add a `title` to every menu built by `exploration_menu.js` (移動 / 查看 / 互動 / 等待 / the target's own `display_name` for a target-affordance frame / the keyword frame's target name) and by `combat_menu.js` (攻擊 / 技能 / the category label / the group label / 威力 / 目標 / 投降)
- [x] 2.3 Add the `suggestions` root row to `exploration_menu.js`'s `rootItems` and its frame builder: the cards as rows, the `✕ 清除建議` row (`options.dismiss`, `{}`), a back row; the root row is absent entirely when `suggestions.status` is `unavailable`, and renders one disabled `AI 正在構思建議…` row when `generating`
- [x] 2.4 Give the suggestions frame the deterministic nearest-surviving-focus rule on a suggestions-only panel replacement (a card whose `action_code` + `params` survive keeps focus), so a `generating → ready` flip never resets the router while the frame is open
- [x] 2.5 Add the destination fields to `exploration_menu.js`'s move rows: keep `label` as the submitted-exit display name and carry the canonical direction and `destination` node id alongside it, so the renderer never re-parses the label
- [x] 2.6 Add the category frame and the conditional group frame to `combat_menu.js` (`groups.length === 1` skips the group frame), preserving server order at every level and leaving `openSkill` / `openSkillTargets` / the scale step / every `combat.cast` payload byte-identical
- [x] 2.7 Set the combat root menu's `gridCols` to its item count (`1` in the `recovery` state) so the tab row's focus geometry matches its rendered order
- [x] 2.8 Extend `web/static/webclient/js/tests/*.test.js` with cases for `trail()`, the menu titles, the suggestions frame (all four statuses), the category/group frames including the single-sub-group collapse, and the corrected root geometry; `node --test` stays dependency-free

## 3. Store and shell wiring

- [x] 3.1 Publish `view.dockTrail` from `router.trail()` beside the existing `view.dockDepth`, committed in the same pass so the crumb can never lag the frame
- [x] 3.2 Expose the active frame's pane kind and the root frame's items to `AppClient.vue` so the dock can render the tab bar and the pane from one commit
- [x] 3.3 Vitest: `view.dockTrail.length` equals `view.dockDepth` after every push, pop, replacement and mode change

## 4. The floating dock panel and its chrome

- [x] 4.1 Re-chrome `components/ActionDock.vue` as the floating panel inside H1's `dock` anchor: `max-width:1180px` centred, the draft's upward gradient, a `--line` top border, the upward shadow, and the fixed-bar / crumb / scrolling-pane layout — keeping `<section id="action-dock" tabindex="0" :data-mode>` the same single element
- [x] 4.2 Add `components/dock-icons.js`: the fixed glyph table keyed by stable server keys (root item keys, look-entity `kind`, canonical direction words, `team`), every glyph `aria-hidden` beside a real text label, an unmapped key rendering no icon
- [x] 4.3 Add `components/DockTabBar.vue` rendering the root frame's items as tabs with their glyph, label, count badge and the seal-red gradient fill on the open/focused tab; at depth 1 it carries the listbox role, the single tab stop, `aria-activedescendant` and `data-testid="dock-menu"`
- [x] 4.4 Derive the badges in `components/dock-panes.js` from the committed payload only (`互動` = `exploration.interact.length`, `建議` = `suggestions.cards.length`, `技能` = the flattened skill-descriptor count); render no badge for an unknowable or zero count
- [x] 4.5 Implement the non-current-tab click as router operations (pop to the root frame, `focusItemByKey`, `focusConfirm("pointer")`), bounded by `router.depth()`, with a click on the already-open tab a no-op
- [x] 4.6 Add `components/DockBreadcrumb.vue`: hidden at depth 1, rendering `parent › current` from `view.dockTrail` with a back chevron bound to `focusEscape()`
- [x] 4.7 Move the shortcut legend into the tab bar's trailing hint slot, keeping `data-testid="action-dock-description"` on the element that carries it
- [x] 4.8 Render the panel with no bar and no crumb when `data-mode="creation"`, so exactly one `#action-dock` persists across every mode change
- [x] 4.9 Storybook stories for `DockTabBar` (exploration root with badges, combat root, one tab open at depth ≥ 2, creation's empty bar) and `DockBreadcrumb` (depth 1 hidden, depth 2, depth 3)

## 5. The pane vocabulary

- [x] 5.1 Add the pane-kind classifier to `components/dock-panes.js` — a pure function from the committed frame to `outlet` / `nav` / `affordance` / `cards` / `skills` / `targets` / `scales` / `confirm` / `plain`, with no DOM and no store access
- [x] 5.2 Extend `components/DockMenuItem.vue` with the matching row variants, keeping the focused marker, the `（無法使用）` suffix, the `aria-describedby` reason association and the `data-item-key` identity defined in exactly one place
- [x] 5.3 Keep every disabled row focusable and arrow-reachable in every variant — the draft's dim-only `.sk.disabled` / `.pick.disabled` is deliberately not followed (design D8); assert it per variant in Vitest
- [x] 5.4 Render the exit outlet: the direction glyph from the fixed table (an unmapped label rendering verbatim), the destination name joined from `local_map.nodes[].label`, and no sub-line when the destination is not in the committed lattice
- [x] 5.5 Render navigation rows with their icon, name, backed sub-line (look rows: the entity `kind`; interact rows: the server-authored affordance labels) and the `›` chevron on rows that open a deeper frame — no stat line, no portrait slot
- [x] 5.6 Render the target-affordance pane with the `對 <目標> 可作：` head taken from the frame's own `target.display_name`
- [x] 5.7 Re-chrome `components/OptionCard.vue` / `ChoiceCardRow.vue` to the draft's `.sug` card and add the row mode (`role="option"` + row id) so a card can be the listbox option inside the suggestions pane, leaving the narrative choice-point's plain-button usage unchanged
- [x] 5.8 Rework `components/DockMenu.vue` into the pane host: one row container carrying the listbox role, the single tab stop, `aria-activedescendant` and `data-testid="dock-menu"` at depth ≥ 2, with `exploration-detail` / `combat-detail` preserved as the detail pane's testid
- [x] 5.9 Scroll the focused row into view (`block:"nearest"`) on every frame render and every focus change
- [x] 5.10 Vitest per pane kind: the rows rendered equal the committed frame's items in order; a disabled row keeps focus and its reason; no pane renders a field the payload does not carry

## 6. Combat surfaces

- [x] 6.1 Add `components/ParticipantFrame.vue`: 我方 / 敵方 groups from `participants[]`, each row carrying `token`, `display_name`, `hp_current / hp_maximum` as numerals, and the state as an explicit text marker (`已逃離` / `倒地` / `已敗退`) alongside any colour
- [x] 6.2 Resolve each participant's portrait through `art.portrait_catalog[portrait_ref]`, rendering the catalog's placeholder card for a missing entry and no card for a `null` ref; construct no subject key or URL
- [x] 6.3 Mount `ParticipantFrame` into H1's `hud-left` anchor from `AppClient.vue`, combat-only, and make `components/ArtPanel.vue`'s standalone catalog strip absent while it is mounted
- [x] 6.4 Render the skill master-detail: the category frame as `.skcat` chips with owned counts, the group frame (only when the category carries more than one sub-group), and the skill frame as rows carrying label and cost beside the detail pane
- [x] 6.5 Add `components/SkillDetailPane.vue` for the focused skill's name, description, cost, target spec and disabled reason, rendered into the preserved `data-testid="combat-detail"` pane; render **no** `戰鬥外` badge (design D14 — the flag is serialized by no presenter)
- [x] 6.6 Re-chrome the 威力 step as the draft's `.scales` row (label plus the server-computed `mp_cost`, ascending, `1` preselected) and the target step as the `.tok` token row (party vs foes, the `✓` AREA selection marker preserved)
- [x] 6.7 Re-chrome the forfeit confirmation as the draft's warning panel with 取消 and 確認投降 rows, still requiring an explicit confirm before `combat.forfeit` carries its `session_id`
- [x] 6.8 Storybook stories with deterministic offline args for `ParticipantFrame` (party+foes, a fled/knocked-out/defeated participant, a null portrait ref, an unavailable art panel) and `SkillDetailPane` (enabled, disabled with reason, freeform-capable, each target spec)
- [x] 6.9 Vitest: the participant frame renders every payload participant and invents no field; the skill frames preserve server order; a single-sub-group category skips the group frame; every `combat.cast` payload is byte-identical to the pre-change payload for the same choices

## 7. Manifest and showcase gate

- [x] 7.1 Add `Action/DockTabBar`, `Action/DockBreadcrumb`, `Action/SkillDetailPane` and `Data/ParticipantFrame` to `component-manifest.json` under the frozen-set growth rule H1 already added to `webclient-component-showcase` — the rule is **not** re-added here, and the count is rebased if H2 archives first
- [x] 7.2 Run `npm run build-storybook` and `npm run showcase-coverage`; both must pass with the extended set
- [x] 7.3 Extend `tests/overlays/deferred_surfaces_absent.test.js` to assert the dock renders no `戰鬥外` skill badge, no look-row stat line and no exploration-row portrait, each named with the field it waits on

## 8. Browser acceptance and re-map

- [x] 8.1 Re-map `test_browser_exploration.py`, `test_browser_shell.py` and `test_browser_pointer.py` off the `exploration-detail` structural walk onto the pane's `data-testid` hooks, keeping every emitted-`ui_action` count and payload assertion exactly as it stands
- [x] 8.2 Re-map `test_browser_combat.py` off the flat skill list onto the category → (group) → skill path, and off the old `combat-detail` geometry onto the master-detail pane; the `#combat-row-0` and `dock-menu` selectors stay
- [x] 8.3 Re-map `test_browser_options_surface.py` and `test_browser_choicepoints.py` off `suggestions-section` onto the `建議` tab and its pane, covering all four statuses and the zero-card degraded empty state; the choice-point's own `option-card` assertions are unchanged
- [x] 8.4 Re-verify `test_browser_art.py`'s `#combat-row-0` gate against the tab bar at depth 1 and `browser_helpers.py`'s `#action-dock` focus forwarding against the active row container, editing only what the forwarding target requires
- [x] 8.5 Re-map `test_browser_services.py` (`dock-menu`, `services-confirm`) and `test_browser_layout.py`'s dock component selector onto the floating panel's hooks; confirm `test_browser_creation.py` and `test_browser_input_narrative.py` need no edit beyond the "exactly one `#action-dock`" and focus-return assertions passing unchanged
- [x] 8.6 Add a browser assertion that the crumb is absent at depth 1, present at depth ≥ 2, names the parent and the current frame, and that its back chevron pops exactly one level — matching Escape
- [x] 8.7 Add a browser assertion that a pointer click on a non-current tab at depth ≥ 2 returns to the root frame and opens that tab with exactly one deliberate activation and no stray `ui_action`
- [x] 8.8 Add a browser assertion at **both** 1440x900 and 1280x720 that the dock panel stays inside its anchor, the deepest combat frame's cast/confirm control is reachable without clipping, and the participant frame does not intersect the dock or the narrative caption
- [x] 8.9 Re-run the keyboard-only exploration, service, creation and combat journeys unmodified, and the pointer-parity journeys, as the end-to-end proof that the re-chrome changed no navigation semantics
- [x] 8.10 Re-run the offline-degradation regression: bundle blocked → text playable; `context_actions` unavailable → the dock renders its empty state and blocks no gameplay

## 9. Gates and handoff

- [x] 9.1 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [x] 9.2 `node --test web/static/webclient/js/tests/*.test.js` green (the preserved router and menu models, extended not relaxed)
- [x] 9.3 `uv run --locked python -m tools.spec_traceability check` green; new requirements carry `@covers_requirement` annotations
- [x] 9.4 `openspec validate webclient-hud-03-action-dock --strict` passes
- [x] 9.5 Rebuild `web/static/webclient/app/dist` and verify the running client at both supported viewports
- [x] 9.6 Flip the roadmap's H3 Status cell to `Done`
- [x] 9.7 Record the H4/H5 hand-offs in the change: the `Quests` / `Inventory` / `Character` tabs become drawer openers when the drawers exist, and the freeform-dialogue row targets the persistent command line when it replaces the borrowed drawer
