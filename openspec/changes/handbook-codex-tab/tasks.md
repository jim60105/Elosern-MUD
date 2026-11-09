# Tasks: handbook-codex-tab

Prerequisites: `handbook-titles-tab` and `lore-codex-schema-v2` are merged. Verify with `git grep -n "export function handbookTabs" web/webclient-app/components/handbook/handbook-tabs.js` and `git grep -n "LORE_CODEX_SCHEMA_VERSION = 2" web/webclient/presentation/lore_codex.py`, each printing one line. Run pnpm commands from the repository root, vitest as `pnpm exec vitest run <path>`, and Python tests with `uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb <label>` (`<file>` contains `MUD_TEST_SETTINGS=1`). Fixtures are synthetic v2 panels. No shipped key or display string may appear.

## 1. Model and tabs

- [x] 1.1 Extend `handbook-tabs.js` per design D1 and update `tests/handbook/handbook_tabs.test.js` (orders `["book","counter","codex","titles"]` and `["codex","titles"]`). Verify with vitest on that file.
- [x] 1.2 Create `components/handbook/lore-codex-model.js` per design D3. Add `tests/handbook/lore_codex_model.test.js` covering: status; rail counts from `discovered`; `defaultCodexCategory`; group order and null-label groups; placeholder items unselectable with an identity-free label and unique ids; entry item labels with stage suffix; `firstEntryKey`; `codexDetail` fields excluding `display_name_zh`, readable labels, `資料` fallback, locked items, monster stamp, track `reached`, and the sighted track's `unlocks` derived from `locked_fields` labels (`null` once defeated); `null` for an unknown key. Verify with vitest.
- [x] 1.3 Add `codexCategory` to `quest-drawer-memory.js` per design D2, with a scope-reset assertion in the existing memory test. Verify with vitest.

## 2. Components

- [x] 2.1 Add the codex emblem paths to `dock-icons.js` (design D4) and create `components/handbook/CodexArt.vue`. Add `tests/handbook/codex_art.test.js`: null `art` renders `handbook__art-emblem`; a descriptor with one image attempt renders the `img`; firing `error` on it with no terminal swaps to the emblem; firing `load` keeps the image. Build synthetic descriptors with the shape used in `web/webclient-app/tests` for `ReferenceArtwork` (find one with `git grep -ln "ReferenceArtwork" web/webclient-app/tests`). Verify with vitest.
- [x] 2.2 Create `components/handbook/CodexTileGrid.vue` per design D4. Add `tests/handbook/codex_tile_grid.test.js`: three distinct `data-stage` marks; the legend only on the monster category with three marks; a placeholder takes focus, has `aria-disabled`, and does not emit `select` on Enter or click; arrow and Home/End roving across groups; group headings only for non-null labels. Verify with vitest.
- [x] 2.3 Extend `components/handbook/CodexDetail.vue` per design D4 without changing its title rendering. Extend `tests/handbook/codex_detail.test.js` with: the stamp `data-stage`; a two-item track with `data-reached` true/false for sighted and true/true for defeated; four locked boxes in order with no field value for a sighted fixture; none for defeated; no footer for a codex detail; the title-detail tests from `handbook-titles-tab` still pass. Verify with vitest.
- [x] 2.4 Create `components/handbook/LoreCodexTab.vue` per design D4. Add `tests/handbook/lore_codex_tab.test.js` covering every scenario of the ADDED tile-wall, stage-mark, locked-field, hero-art and degradation requirements in `specs/webclient-lore-codex-panel/spec.md` that does not need real layout: category selection dispatches nothing; per-category selection memory; the detail renders card fields verbatim; the absent empty state; nothing discovered gives every placeholder plus the empty guidance; vanished-selection fallback. Verify with vitest.

## 3. Dispatcher, shortcut and removals

- [x] 3.1 Edit `QuestDrawer.vue` (design D1, D5), `nav-tools.js`, `stores/elosern/hud.js`, `composables/use-drawers.js` and `AppClient.vue` per design D1. Update `tests/world/quest_drawer.test.js` (four tabs outside combat, two in combat, a remembered `book` in combat resolving to `codex`, the disabled codex tab with reason, a `{slot:"handbook", section:"codex"}` request switching the tab), `tests/store/hud_drawer.test.js` (`openHudDrawer("lore")` rejected, `openHandbook("codex")` accepted in combat), `tests/desktop_navigation.test.js` (圖鑑 emits `handbook` with `"codex"`), and `tests/app_client_drawers.test.js` (`nav-tool-lore` opens the quest drawer on the codex tab). Verify with vitest on those files.
- [x] 3.2 Apply design D7 deletions. Fix every remaining vitest reference (`git grep -n "LoreCodexDrawer\|codex_field_label\|hudDrawer === 'lore'\|openHudDrawer(\"lore\")\|\"lore\"" web/webclient-app` should show only `nav-tools.js`'s key and glyph uses, after fixing `tests/dialogue_store.test.js`, `tests/app_client_frameless_shop.test.js`, `tests/reference_surface_frame.test.js` and every other hit). If any deleted test path appears in `tools/test_data_freeze.json` or `tools/test_data_lint_seed.json`, remove it from both. Verify with `pnpm test` (full vitest run): all green.

## 4. Stories, manifest, docs, contracts

- [ ] 4.1 Add the stories per design D8 and update `component-manifest.json` and the showcase evidence lists per design D7. Verify with `pnpm run build-storybook && pnpm run showcase-coverage` and the focused labels `web.webclient.tests.test_vue_showcase_action_evidence`, `web.webclient.tests.test_vue_showcase_data_evidence`, `web.webclient.tests.test_vue_showcase_overlays_evidence` and `web.webclient.tests.test_vue_showcase_world_evidence`.
- [ ] 4.2 Update `docs/game/commands.md` per design D6, then run the focused label `tests.test_command_docs`. It passes.
- [ ] 4.3 Update the frozen-contract audit and `tests/test_data_independence_js_webclient.py` per design D7. Verify with the focused labels `tests.test_webclient_frozen_contract` and `tests.test_data_independence_js_webclient`, plus `uv run --locked python -m tools.test_data_lint check`.

## 5. Live-client browser acceptance

- [ ] 5.1 Update the browser tests listed in design D7 to the codex tab, keeping their method names and every annotation whose requirement still exists. Run each touched method alone with `uv run --locked python -m web.tests.browser.unittest_driver <module>.<Class>.<method>`, capturing output to a scratch file. All pass.
- [ ] 5.2 Add `web/tests/browser/test_browser_handbook_codex.py` with class `HandbookCodexBrowserTest`, which injects a synthetic v2 panel through the existing `_inject_snapshot` helper (as `test_browser_contextual_hud_drawers.py` does) on the live client. Add these methods:
  - `test_codex_tab_geometry_at_reference_viewports`: for (1451, 790) and (2560, 1440), the rail, wall and detail boxes do not overlap and lie inside the drawer body; the wall has `scrollWidth <= clientWidth`; every visible text node's computed font size is `>=` the computed `--text-xs`; each legend mark's width is `12 * --ui-scale` within 1px.
  - `test_monster_legend_stays_pinned_while_tiles_scroll`: with a synthetic monster category large enough to overflow, the legend box lies inside the wall's visible box at scroll top and at scroll bottom.
  - `test_codex_tool_opens_the_codex_tab_in_combat`: in an injected combat snapshot, `nav-tool-lore` opens the drawer with exactly the codex and titles tabs.
  Register the class's method labels in `.github/browser-shards.json`. Run each method alone as in 5.1. All pass.
- [ ] 5.3 Run `grep -n -E "codex-tile|codex-wall|codex-art|lore-codex-tab|codex-detail|handbook__" web/webclient-app/styles/app-shell.css` and expect no output.

## 6. Evidence bridge and gates

- [ ] 6.1 Extend `web/webclient/tests/test_vue_handbook_evidence.py` (created by `handbook-primitives`) with one method per ADDED codex-tab requirement that runs `tests/handbook/lore_codex_tab.test.js`, `codex_tile_grid.test.js`, `codex_detail.test.js`, `codex_art.test.js` and `lore_codex_model.test.js` and asserts that they pass. Verify with the focused labels `web.webclient.tests.test_vue_handbook_evidence` and `tests.test_evennia_test_optimization_contract`.
- [ ] 6.2 Run `uv run --locked python -m tools.contract_gate --change handbook-codex-tab` (it tolerates the three REMOVED drawer requirements) and `openspec validate handbook-codex-tab --strict`. Both pass.

## Workflow follow-up

- At archive, after the sync, annotate with the IDs from `uv run --locked python -m tools.spec_traceability list`:
  - `test_vue_handbook_evidence` codex methods: the tile-wall, stage-mark, locked-field, hero-art and degradation requirements.
  - `HandbookCodexBrowserTest` methods: the reference-viewport requirement and the stage-mark requirement (pinned legend).
  - Move every annotation that named a REMOVED drawer requirement to the matching new requirement.
- Then run `tools.spec_traceability check` without `--change`.
