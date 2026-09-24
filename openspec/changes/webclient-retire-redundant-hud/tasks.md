## 1. Preconditions

- [ ] 1.1 Confirm the consumers this change relies on (stop and report if any grep disagrees):
  - `grep -rn "CharacterHead\|ArtPanel\|QuickWordChips\|quick_chips" web/webclient-app --include='*.js' --include='*.vue'` (excluding `dist/` and `node_modules/`) lists only `AppClient.vue`, `StatusPanel.vue`, `CommandLine.vue`, `AppShell.vue`, the three components themselves, their stories, and the tests named in sections 2–5.
  - `grep -rn "insertText" web/webclient-app --include='*.js' --include='*.vue'` shows only the chip paths in `CommandLine.vue` and `AppShell.vue`.
  - `grep -rn "openHudDrawer('party')\|openHudDrawer(\"party\")" web/webclient-app --include='*.vue' --include='*.js'` shows only the `PartyStrip` binding in `AppClient.vue`.
  - `grep -n '"severity"' web/webclient/presentation/status.py` shows the `severity` key on every `status.conditions` entry, and `grep -n "_SEVERITIES" world/rules/status_display.py` lists `beneficial`, `informational`, `warning`, `harmful`, `critical`.
- [ ] 1.2 Confirm C1 (`webclient-minimap-and-log-quick-fixes`) and C2 (`webclient-full-map-fit-view`) are archived, or will be archived before this change (archive order C1 → C2 → C3). If C2's MODIFIED text of "The map, settings, and help surfaces are reachable from the live client" changed after this change was written, re-sync this change's block to it, keeping only the help-paragraph edit.

## 2. Head card and art strip

- [ ] 2.1 Delete these files:
  - `web/webclient-app/components/CharacterHead.vue`
  - `stories/Data/CharacterHead.stories.js`
  - `tests/data/character_head.test.js`

  Also remove `web/webclient-app/tests/data/character_head.test.js` from `tools/test_data_freeze.json` (both occurrences) and from `tools/test_data_lint_seed.json`.

  `components/StatusPanel.vue`:
  - drop the `CharacterHead` import and element, and the `character` prop
  - add a `visible` boolean prop, bound with `v-show` on the `status-panel` root (design D1)
  - rewrite the header comment

  `components/character-identity.js`: rewrite the header comment only, so it no longer describes a head card; its exports stay.

  Delete the three `.elosern-root .character-head…` rules in `styles/app-shell.css`.
- [ ] 2.2 Delete these files:
  - `web/webclient-app/components/ArtPanel.vue`
  - `stories/World/ArtPanel.stories.js`
  - `tests/world/art_panel.test.js`

  Also:
  - delete the `ArtPanel.vue` row in `tests/z_index_scale.test.js`
  - delete the `.elosern-root .art-panel` rule in `styles/app-shell.css`
  - in `AppClient.vue`, delete the `ArtPanel` import, its element, and its H3 comment

  `grep -rn "art-panel\b\|art-panel__\|ArtPanel.vue" web/webclient-app --include='*.js' --include='*.vue' --include='*.css'` (excluding `dist/`) returns nothing. The `artPanel` prop names on other components are unrelated and stay.
- [ ] 2.3 `web/webclient-app/component-manifest.json`: remove `Core/QuickWordChips`, `Data/CharacterHead`, and `World/ArtPanel` (keep `"frozen": true`).

  Update the manifest snapshots that list them:
  - `tests/overlays/deferred_surfaces_absent.test.js`
  - `web/webclient/tests/test_vue_showcase_action_evidence.py`
  - `test_vue_showcase_data_evidence.py`
  - `test_vue_showcase_world_evidence.py`: the title lists, the `world-artpanel--*` story IDs, and the `"ArtPanel"` component-name list near line 301
  - `test_vue_showcase_overlays_evidence.py`

  Fix the comments that enumerate those keys.

## 3. Quick-word chips and letter bindings

- [ ] 3.1 Delete these files:
  - `web/webclient-app/components/QuickWordChips.vue`
  - `lib/quick_chips.js`
  - `stories/Core/QuickWordChips.stories.js`
  - `tests/quick_word_chips.test.js`
- [ ] 3.2 `components/CommandLine.vue` (design D6):
  - delete the `QuickWordChips` import and mount, `onChipInsert`, `insertText`, the `chipLetters` import and its use in the candidate list, and the `mode` prop
  - make `defineExpose` expose `focusField` only
  - delete any chip-cluster CSS and comments
  - rewrite the header comment's element order

  `components/AppShell.vue`:
  - delete the `boundLetters` import and the bound-letter tail of `onWindowKeydown` (keep the modifier guard and the `/` `preventDefault`)
  - drop `:mode` on `<CommandLine>`
  - rewrite the shell header comment's quickbar paragraph

  `stories/Core/CommandLine.stories.js`:
  - drop the `mode` args
  - delete the `Combat` story (it only showed the combat chip set)
  - rewrite the header comment

  `grep -rn "quick_chips\|QuickWordChips\|boundLetters\|chipLetters\|insertText\|qwc" web/webclient-app --include='*.js' --include='*.vue' --include='*.css'` (excluding `dist/`) returns nothing.
- [ ] 3.3 `lib/controls-reference.js`:
  - delete the `Quick-word chips` and `l g s t w / s c` entries
  - reword the `Tab` detail to "complete against history and the room's exits and targets"

  `components/HelpOverlay.vue`: drop "the quick-word chips" from the header comment.
- [ ] 3.4 `web/webclient-app/tests/command_line.test.js`:
  - delete "the quick-word chips prepare without submitting" and "chip sets follow the mode"
  - rewrite "Tab is stable across candidate kinds" so the unique completion comes from a history or panel candidate instead of the chip letter `s`
  - stop passing `mode` to `mountLine` (keep the host's `data-elosern-mode` attribute only if another case still reads it)
  - add one case: in exploration mode, a keydown of `g` on a non-editable target leaves `#inputfield` empty and does not move focus. Mount `AppShell` for this case, or put it in the existing AppShell test file if `grep -rln "AppShell.vue" web/webclient-app/tests` finds one.

  Run `pnpm exec vitest run web/webclient-app/tests/command_line.test.js web/webclient-app/tests/overlays/help_overlay.test.js` (repository root); green.
- [ ] 3.5 `commands/tests/test_localized/test_surface_and_quickbar.py`:
  - delete the `QuickbarLetterPinningTests` class and its imports that become unused
  - reword the module docstring to name only `LocalizedCommandSurfaceTests`

  Run `uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_localized`; green.

## 4. Vitals visibility

- [ ] 4.1 `components/vitals.js`: add `isVitalsVisible({ mode, resources, conditions, lowHp })` per design D2 (numeric-only comparison, missing gauges ignored).

  `stores/elosern/view.js`: add `visible` to both branches of the `vitals` slice. The unavailable branch is `visible: false`; the available branch passes the committed mode, `statusPanel.resources`, `statusPanel.conditions`, and the derived `lowHp`.

  Add `web/webclient-app/tests/data/vitals_visibility.test.js` covering:
  - full vitals with no condition in exploration, dialogue, and combat (false, false, true)
  - `mp` below max (true)
  - one `harmful` condition at full vitals (true)
  - one `warning` condition at full vitals (true)
  - one `critical` condition at full vitals (true)
  - only `beneficial` conditions (e.g. a `defense_instinct_defense_bonus` row) at full vitals in exploration (false)
  - only `informational` conditions, or a condition with a missing `severity`, at full vitals in exploration (false)
  - `lowHp` (true)
  - a missing gauge and a string `current` (neither counts)
  - the store slice through a fixture snapshot (`tests/store/protocol_fixtures.js` `statusPanel()`)
- [ ] 4.2 `AppClient.vue`:
  - mount `StatusPanel` on `panelAvailable('status')` alone
  - drop its `:character` binding
  - bind `:visible="store.view.vitals.visible"`
  - pass `:vitals-visible="store.view.vitals.visible"` to `AppShell`

  `AppShell.vue`: add the `vitalsVisible` prop and the pre-flush watcher from design D3 (true → false edge, `document.activeElement.closest('[data-testid="status-panel"]')`, then `restoreDockFocus()`).

  `tests/data/status_panel.test.js`:
  - replace the head-card cases with: two sibling islands (vitals, conditions) in order; `visible: false` gives a root with `display: none` that is still in the DOM; the trailing-bar memory survives a hidden-then-shown revision (mount hidden at full hp, commit a lower hp with the same epoch, assert the ghost width is the previous ratio)
  - keep the gauge-hook and combat-header cases

  Add a `status_panel.test.js` case: with `visible: true` and one `beneficial` plus one `harmful` condition, both chips render.

  Add an AppShell/AppClient case: focus a `harmful` condition chip, then commit full vitals with only a `beneficial` condition in exploration; the island hides and focus lands on `#action-dock`.

  `stories/Data/StatusPanel.stories.js`: drop `character` args and add `visible: true` (plus one `HiddenAtFullHealth` story). Keep the existing story IDs `full-payload`, `combat-rounds`, and `minimal`. If the `data-statuspanel--*` story-ID list in `web/webclient/tests/test_vue_showcase_data_evidence.py` is exhaustive, add `data-statuspanel--hidden-at-full-health` to it.

  Run `pnpm exec vitest run web/webclient-app/tests/data web/webclient-app/tests/store`; green.
- [ ] 4.3 `web/webclient/tests/test_node_suite_evidence.py`: add `test_vitals_visibility_node_suite_passes`, running `web/webclient-app/tests/data/vitals_visibility.test.js` and `tests/data/status_panel.test.js` in the same shape as `test_party_strip_node_suite_passes`, annotated `webclient-contextual-hud::the-vitals-island-is-shown-only-in-combat-or-while-a-vital-or-a-condition-needs-attention` (confirm the ID with `uv run --locked python -m tools.spec_traceability list` after 7.1).

## 5. Party strip, party opener, gallery opener

- [ ] 5.1 `components/PartyStrip.vue`:
  - render the root only when `safeSlots.length > 0`
  - rewrite the header comment (drop "Empty party renders one row of 4 dashed invite cells")

  `tests/data/party_strip.test.js`: replace "renders four dashed invite cells and 0 / 4 for an empty party" with "renders nothing for an empty party" (`w.find('[data-testid="party-strip"]').exists()` is false). Replace the empty-slot click step in the activation test with a one-companion mount.

  `stories/Overlays/PartyStrip.stories.js`: keep `EmptyParty` (story ID unchanged) and document that it renders nothing.

  `tests/app_client_drawers.test.js`: add an available, empty `party` panel case asserting no `party-strip`.
- [ ] 5.2 `components/CharacterStatusDrawer.vue`:
  - add a `partyAvailable` prop and an `open-party` emit
  - add a `同伴 · 隊伍` button (`data-testid="character-status-drawer__open-party"`) beside `character-status-drawer__open-skill`, rendered only when `partyAvailable`

  `AppClient.vue`: bind `:party-available="store.partyAvailable"` and `@open-party="() => store.openHudDrawer('party')"`.

  `tests/data/character_status_drawer.test.js`: the button is absent without `partyAvailable`, and emits `open-party` without dispatching when present.

  `tests/app_client_drawers.test.js`: with an empty party, open the status drawer, activate the button, and see `store.view.hudDrawer === "party"` and a mounted `party-drawer`.

  `stories/Data/CharacterStatusDrawer.stories.js`: pass `partyAvailable: true` in the full-payload story.
- [ ] 5.3 Gallery opener (design D5):
  - `components/CommandLine.vue`: add a `galleryAvailable` prop and, inside `span.cmdutil`, a `button.cmdutil__btn` with `aria-label="角色肖像圖庫"`, `data-testid="gallery-opener"`, and `@click="onOpenOverlay('gallery')"`, rendered only when `galleryAvailable`
  - `AppShell.vue`: add and forward the `galleryAvailable` prop
  - `AppClient.vue`: bind `:gallery-available="panelAvailable('gallery')"`, and delete the left-column button and the `.gallery-opener` CSS block

  `tests/app_client_gallery.test.js` keeps its selector and must stay green unchanged. Add one assertion that the opener is inside `[data-testid="command-line"]`.

  `stories/Core/CommandLine.stories.js`: add `galleryAvailable: true` to `Exploration`.

  Run `pnpm exec vitest run web/webclient-app/tests/app_client_gallery.test.js web/webclient-app/tests/app_client_drawers.test.js web/webclient-app/tests/data`; green.

## 6. Browser tests

- [ ] 6.1 `web/tests/browser/test_browser_shell_surfaces.py`:
  - delete `test_character_head_card_renders_only_backed_identity`
  - in `test_unavailable_placeholders_and_numeric_status`, delete the `.art-panel` block and assert that no `[data-testid="art-panel"]` exists
  - in `test_populated_island_stack_fits_its_anchor_at_both_viewports`, lower the injected `hp.current` below maximum so the island is visible before measuring, and delete the `ArtPanel present` assertion and its comments
  - add `test_vitals_island_hides_at_full_health_outside_combat`, annotated with the new vitals ID: inject full vitals with no conditions and assert `status-panel` is attached but not visible; inject full vitals with only a `beneficial` condition and assert it is still not visible; inject full vitals with one `harmful` condition and assert it is visible with that chip; inject `mp` below max with no condition and assert it is visible

  `.github/browser-shards.json`: replace the deleted test label with the new one.
- [ ] 6.2 `web/tests/browser/test_browser_input_narrative.py`: delete `test_quick_word_chip_prepares_a_command_without_sending` and `test_bound_letter_outside_the_field_inserts_like_a_chip`, and drop both labels from `.github/browser-shards.json`.

  Re-anchor every `webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch` annotation to `…::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch`: `test_browser_input_narrative.py` (3) and `test_browser_inventory_actions.py` (1).

  `web/tests/browser/test_vue_foundation.py`: remove `"quick-word-chips"` from `CORE_SURFACE_TESTIDS`.
- [ ] 6.3 Art browser tests:
  - `test_browser_art.py`: delete `test_exploration_portrait_tiles_match_the_catalog` and the now-unused `ART_PANEL_DOM` / `_art_panel_available`, and drop its shard label if listed. The combat portrait tests keep covering "Contextual portrait focus is client-local and verified".
  - `test_browser_reconnect.py::test_offline_overlay_outranks_open_full_views_and_full_log`: delete the `portrait-full-view` subtest entry.
  - `web/tests/browser/seed/art_fixture.py`: reword the two ArtPanel comments.
  - `test_browser_contextual_hud_combat.py`: keep the `art-panel` count-0 assertion (it still pins "no separate portrait strip").
- [ ] 6.4 Classify every browser selector on `status-panel` and fix the ones that need the island visible:
  - `grep -rn 'status-panel"' web/tests/browser/*.py`
  - `test_browser_local_map_interaction.py::test_minimap_visible_and_keyboard_usable_at_both_viewports`: inject a below-max `status` before `is_visible()`, or drop `status-panel` from that visibility list.
  - `test_browser_layout.py` readiness waits only need the node in the DOM, and `v-show` keeps it there, so leave them unchanged.
  - gauge-text reads are unaffected.

  Run these on a local server and get them green:
  - `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_shell_surfaces web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_local_map_interaction web.tests.browser.test_browser_layout web.tests.browser.test_vue_foundation`
  - the edited cases of `test_browser_art` and `test_browser_reconnect`

## 7. Specs and traceability

- [ ] 7.1 Sync this change's deltas into the main specs (`openspec archive` at the end of the work, or `openspec-sync-specs` first to obtain the new IDs). Then run `uv run --locked python -m tools.spec_traceability list | grep -E "vitals-island|a-deliberate-mutation-echo"` and use those exact IDs in 4.3, 6.1, and 6.2.
- [ ] 7.2 `grep -rn "the-character-head-card-renders-only-backed-identity\|quick-word-chips-prepare-a-command\|bound-quickbar-letters-are-pinned\|every-deliberate-mutation-echo" web tests commands tools --include='*.py' --include='*.js'` returns nothing. Then run `uv run --locked python -m tools.spec_traceability check`; green.

## 8. Validation

- [ ] 8.1 Run every gate from the repository root, all green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `pnpm run build-storybook`
  - `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_node_suite_evidence commands.tests.test_localized`
- [ ] 8.2 Run `agent-browser` against the running client at 1920×1080:
  - At full health in exploration, the left column shows no vitals, no party strip, no head card, and no 美術展示 strip, and the command line shows no chips.
  - After taking damage (or entering combat), the vitals appear.
  - The 角色肖像圖庫 control in the command line opens the gallery.
  - Pressing `g` with the dock focused inserts nothing.

  Close the browser when done.
- [ ] 8.3 Run `openspec validate webclient-retire-redundant-hud --strict` and `git diff --check`; both clean.
