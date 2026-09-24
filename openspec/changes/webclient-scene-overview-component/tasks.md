## 1. Preconditions

- [ ] 1.1 Confirm that C7 (`webclient-typewriter-reading-prefs`) and everything before it is archived. `grep -n "Core/MessageWindow" web/webclient-app/component-manifest.json` matches, and `openspec list` shows no earlier AVG series change pending. Stop and report otherwise.

## 2. Model and router (Node gate)

- [ ] 2.1 `web/static/webclient/js/elosern/exploration_menu.js`: add `overviewMenu(panel, options)` per design D1 and export it.
  - Reuse `moveItems`, `lookItems`, and the `normalizeDirection` table.
  - Omit empty sections.
  - Footer labels are `查看房間`, `等待／休息`, and `建議` / `建議 (N)`.
  - `geometry: "sections"`, `title: "場景"`.
  - Extend the header comment.
- [ ] 2.2 In the same file, add `verbMenuFor(model, target)` per design D2 (delegates to `targetMenuFor`, drops `target-empty`, inserts `look-target` before the back row) and export it. `targetMenuFor` is unchanged.
- [ ] 2.3 `web/static/webclient/js/tests/exploration_menu.test.js`: add cases built only from synthesized fixtures (the file is in `tests/test_data_independence_js_webclient.py`'s `MIGRATED_FILES`):
  - reading order and `sections` counts
  - empty people/objects sections omitted
  - a disabled exit kept with its reason
  - entity look chips only for non-interact identities
  - person chips enabled with `openTarget` even with zero affordances
  - the footer's suggestions entry absent at `unavailable`, `建議` at `generating`, `建議 (3)` at ready with three cards
  - move payloads carrying `current_node`
  - `verbMenuFor` keeping payload order, appending 查看 then back, and yielding 查看 + back for an unmapped target
- [ ] 2.4 `web/static/webclient/js/elosern/keyboard_router.js`: implement the `sections` geometry per design D3 in `move()` and `projectFocus` (list projection). Update the file header comment. `web/static/webclient/js/tests/keyboard_router.test.js`: add cases for:
  - Left/Right wrapping across sections
  - Up/Down landing on the same ordinal, clamped to a shorter section, and wrapping
  - a single-section menu making Up/Down no-ops
  - a count mismatch falling back to list behaviour
  - `focusItemByKey` and re-resolution keeping the key

  Run `node --test web/static/webclient/js/tests/*.test.js` and `uv run --locked python -m tools.test_data_lint check`. Both are green.

## 3. Components

- [ ] 3.1 Create `web/webclient-app/components/dock-exits.js` with `directionGlyph` and `destinationLabel(item, localMapModel)` moved from `components/DockMenu.vue` (design D6). Make `DockMenu.vue` import them, passing `props.view?.localMapModel`. `pnpm exec vitest run web/webclient-app/tests/action/dock_menu_outlet.test.js` stays green unchanged.
- [ ] 3.2 `web/webclient-app/components/DockMenuItem.vue`: add the optional `glyph` prop (design D4), rendered as an `aria-hidden` leading span. `pnpm exec vitest run web/webclient-app/tests/action/dock_menu_item.test.js` stays green, and one new case covers the glyph.
- [ ] 3.3 Create `web/webclient-app/components/SceneOverview.vue` per design D4, with:
  - props `menu`, `focusedKey`, `localMap`, `idPrefix`, `active`
  - emits `focus-change`, `activate`
  - the section rows, chip markup, reason strip, `scrollIntoView` on focus change, and the inert inactive state

  Styles are scoped and use existing tokens only (`--gold-400`, `--gold-glow`, `--ink-*`, `--paper-*`). The header comment cites design §7 and this change.
- [ ] 3.4 Create `web/webclient-app/components/DockVerbPopover.vue` per design D5, with:
  - props `menu`, `focusedKey`, `idPrefix`
  - emits `focus-change`, `activate`, `back`
  - the outside-press layer, the bottom-anchored card, the head, and `DockMenuItem` rows

## 4. Stories, manifest, tests

- [ ] 4.1 Create `web/webclient-app/stories/fixtures/scene_overview.js` with `explorationPanelFixture`, `overviewArgs`, and `verbArgs` (design D7), importing `../../lib/exploration_menu.js` only.
- [ ] 4.2 Create `web/webclient-app/stories/Action/SceneOverview.stories.js` (`FullRoom`, `EmptyRows`, `DisabledExit`, `Overflowing`) and `DockVerbPopover.stories.js` (`DialogueHost`, `HostileTarget`, `LookOnly`, each over an inactive overview in a positioned 640×300 box). Args come only from the helper.
- [ ] 4.3 `web/webclient-app/component-manifest.json`: add `"Action/SceneOverview"` and `"Action/DockVerbPopover"` after `"Action/DockBreadcrumb"`. Add both titles to the manifest snapshots in:
  - `web/webclient/tests/test_vue_showcase_action_evidence.py`
  - `test_vue_showcase_data_evidence.py`
  - `test_vue_showcase_world_evidence.py`
  - `test_vue_showcase_overlays_evidence.py`
  - `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`

  Fix any comment that states a manifest count. `pnpm run showcase-coverage` is green.
- [ ] 4.4 Create `web/webclient-app/tests/action/scene_overview.test.js`. Mount `SceneOverview` with menus from `overviewMenu` and cover:
  - the section order, with an absent section leaving no row or label
  - row ids `exploration-row-<i>` in reading order and `data-item-key`
  - the exit glyph plus destination name, and the disabled exit rendering its own exit label with `（無法使用）` and no `（無法通行）`
  - a disabled chip click emitting `focus-change` only, with the reason strip showing the reason
  - an enabled click emitting `focus-change` then `activate`
  - `aria-activedescendant` following `focusedKey`
  - `scrollIntoView` called on focus change (stubbed)
  - `active: false` removing the `dock-menu` hook and setting `inert` / `aria-hidden`
- [ ] 4.5 Create `web/webclient-app/tests/action/dock_verb_popover.test.js`. Cover:
  - the head naming the target
  - rows in `verbMenuFor` order, ending 查看 then 返回上一層
  - an enabled row emitting `activate` with its key
  - a disabled row emitting only `focus-change`
  - an outside press on the layer emitting `back` once
  - a press on the card emitting nothing

  Run `pnpm test` green.

## 5. Specs

- [ ] 5.1 Sync this change's two showcase deltas into `openspec/specs/webclient-component-showcase/spec.md`. Run `uv run --locked python -m tools.spec_traceability check`, which is green (no ID changes). `test_vue_showcase_action_evidence.py` keeps its `the-action-dock-family-presents-a-finite-keyboard-and-pointer-actionable-contract` annotation.

## 6. Validation

- [ ] 6.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, and `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_node_suite_evidence`. All green.
- [ ] 6.2 Open `Action/SceneOverview` → `Overflowing` and `Action/DockVerbPopover` → `DialogueHost` in the built Storybook (`.storybook-out`) with `agent-browser`. Check that the chips wrap inside the box with no horizontal scrollbar and that the popover sits inside the box above its bottom edge. Close the browser afterwards.
- [ ] 6.3 Run `openspec validate webclient-scene-overview-component --strict` and `git diff --check`. Both clean.
