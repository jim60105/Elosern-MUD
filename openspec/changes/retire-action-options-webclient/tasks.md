# Tasks

## 1. Delete the client suggestion modules

- [x] 1.1 Delete `web/webclient-app/lib/option_cards.js` and `web/static/webclient/js/elosern/option_cards.js`.
- [x] 1.2 Delete `web/static/webclient/js/tests/option_cards.test.js` and `web/static/webclient/js/tests/options_view.test.js`.
- [x] 1.3 Remove `OptionCards` from `web/webclient-app/logic.js` and from the suggestions view slice in `web/webclient-app/stores/elosern/view.js` (delete `suggestions`, `suggestionsView`, `suggestionsSignature`).
- [x] 1.4 Delete `option_cards.js` from the preserved-wrapper tuple in `tests/test_frontend_toolchain_contract.py`.

## 2. Remove the pill and the suggestions room card

- [x] 2.1 `web/webclient-app/AppClient.vue`: delete the `exploration-pill` / `suggestions-pill` button, `pillLabel`, `pillCount`, `onPill`, and the suggestions wording in the room-card template comment.
- [x] 2.2 `web/webclient-app/composables/use-room-actions.js`: delete `suggestionsCardContent`, every pill computed/handler, the `pill` slot in `TAB_CHAIN_ORDER`, and the `suggestions` kind of `roomCard`; keep the two-layer wait/rest entry, `tilesShown`, `waitFormOpen`, `sleepFormOpen`, and the readout feed for the place-card buttons. The exploration Tab chain becomes compass → rail → 查看房間 → 休息.
- [x] 2.3 `web/webclient-app/stores/elosern/room_actions.js`: `ROOM_CARD_KINDS` becomes `{"wait"}`; delete `activateSuggestion`, the suggestions branch of `openRoomCard`, the suggestions close rule in `closeOnCommit`, and the `suggestionsCard` view key.
- [x] 2.4 `web/webclient-app/stores/elosern.js`: delete the `activateSuggestion` re-export. `web/webclient-app/stores/elosern/hud.js`: update the sub-dock comment only.
- [x] 2.5 `web/webclient-app/stores/frame-resolvers.js`: delete `SUGGESTIONS_RESOLVABLE`, `explorationSuggestions`, its registry entry, and its export.
- [x] 2.6 `web/static/webclient/js/elosern/exploration_menu.js`: delete `suggestionsMenu`, `cardItems`, and their export.

## 3. Shed the suggestions-only ChoiceCard affordances

- [x] 3.1 `web/webclient-app/components/ChoiceCard.vue`: delete the `notes` prop, the `choice-card__note` markup and CSS, the per-row `hint` line (`choice-card__hint`) and its CSS, and the `icon === "trash"` badge and CSS; update the header comment to the surviving consumers.
- [x] 3.2 Confirm no surviving producer passes `notes`, a row `hint`, or `icon: "trash"` (`grep` the composables and components); the verb card, dialogue picks, overflow card, wait card, rest entry, and sleep handoff render label/badge/kind/enabled only.
- [x] 3.3 `web/webclient-app/components/dock-icons.js`: delete the `suggestions` glyph and its comment.

## 4. Rewrite the controls reference and the readout sources

- [x] 4.1 `web/webclient-app/lib/controls-reference.js`: delete the `pill` entry, retitle the `room` group to `地點`, and rewrite `tab-order` and `room-card-escape` to the four-stop chain and 休息/雙層卡片的 return-focus wording.
- [x] 4.2 `web/webclient-app/components/exploration-readout.js`: delete `pillReadout` and the `pill` parameter/branch of `readoutContent`; the compass aim, rail entry, and place-card buttons keep their priority, and the blocked-move flash and idle summary are unchanged.
- [x] 4.3 `web/webclient-app/composables/use-exit-compass.js`: delete the pill readout state (`setPill`, the pill branch of `onPillHover`, the off-pill fallback). `web/webclient-app/composables/use-app-client.js`: delete the `onPillHover` wiring. `web/webclient-app/composables/use-person-focus.js`: comment only.

## 5. Stories and fixtures

- [x] 5.1 `web/webclient-app/stories/Action/ActionDock.stories.js`: delete the pill markup in `renderOverview`, the `suggestions` arg on the remaining stories (keep `ExplorationDock`), and the `GeneratingSuggestions`/`DegradedEmptySuggestions`/`UnavailableSuggestions` stories. `web/webclient-app/stories/fixtures/action_dock.js`: delete the four `SUGGESTIONS_*_SAMPLE` constants.
- [x] 5.2 `web/webclient-app/stories/Core/AppShell.stories.js`: delete the `suggestions` fixture from the exploration `context_actions` payload.
- [x] 5.3 `web/webclient-app/stories/Core/ChoiceCard.stories.js`: delete all three suggestion stories (`Suggestions`, `SuggestionsGenerating`, `SuggestionsDegradedEmpty`), the `suggestionsCardArgs` import, and the notes/hint/trash wording.
- [x] 5.4 `web/webclient-app/stories/Core/ExplorationScreen.stories.js` and `stories/fixtures/scene_overview.js`: delete the suggestions card case, its story, `suggestionsCardArgs`, and the sample fixture.

## 6. Vitest and Node coverage

- [x] 6.1 `web/webclient-app/tests/app_client_room_actions.test.js`: delete the pill/card describe block and its helpers; keep the wait/rest/focus/readout tests.
- [x] 6.2 `web/webclient-app/tests/app_client_presence_rail.test.js`: end the Tab-chain test at 休息 and retarget the inert-panel fallback assertion.
- [x] 6.3 `web/webclient-app/tests/app_client_scene_overview.test.js`: the exploration root's right column holds only `exploration-readout`.
- [x] 6.4 `web/webclient-app/tests/frame-resolvers.test.js`: delete every `explorationSuggestions` case and the suggestions fixture fields.
- [x] 6.5 `web/webclient-app/tests/store/room_cards.test.js`, `tests/store/digit_row_picks.test.js`: delete the suggestions tests/fixtures; keep the wait card's cases.
- [x] 6.6 `web/webclient-app/tests/components/choice_card.test.js`: delete the hint/notes/trash test.
- [x] 6.7 `web/webclient-app/tests/components/dock_panes.test.js`, `tests/components/exploration_readout.test.js`, `tests/components/dock_icons.test.js`, `tests/action/action_dock.test.js`, `tests/overlays/help_overlay.test.js`, `tests/transport.test.js`: drop the suggestion fixtures/assertions named in design.md.
- [x] 6.8 `web/webclient-app/tests/store/store_slices.test.js`: delete the suggestions view-model test. `web/webclient-app/tests/app_client_frameless_bag.test.js`, `tests/bridge/bridge.test.js`, `tests/preserved_contract.test.js`, `tests/store/store_dispatch_focus.test.js`: update comments and the root tab-stop enumeration.
- [x] 6.9 `web/static/webclient/js/tests/exploration_menu.test.js`, `hud_dock_menus.test.js`, `ui_contract.test.js`: drop the `suggestionsMenu`/suggestion-row assertions; `ui_contract.test.js` asserts the pill/card test ids are absent from `AppClient.vue`.

## 7. Browser suite and its fixture

- [x] 7.1 Delete `web/tests/browser/test_browser_options_surface.py` and `web/tests/browser/seed/options_surface_fixture.py`; remove its import/re-export from `web/tests/browser/seed/__init__.py` (including the package-docstring mention) and its call site in `web/tests/browser/seed/runner.py` (the `_options_surface_fixture(character)` line).
- [x] 7.2 `web/tests/browser/browser_settings.py`: remove the `ELOSERN_BROWSER_OPTIONS_SURFACE` profile gate, the replay-client builder, and the `_build_action_options_client` seam assignment.
- [x] 7.3 `web/tests/browser/browser_helpers.py`: remove `SUGGESTIONS_CARD_SELECTOR`, `PILL_SELECTOR`, `open_suggestions_card`, `suggestion_row_key`, the `suggestions` routing, and the `pill` field of `exploration_root_controls`; the dock-available probe stops reading a `suggestions` view key. `_journey_support.py`: remove `_suggestions_ready`.
- [x] 7.4 `web/tests/browser/test_browser_exploration_state.py`: delete `test_suggestions_frame_is_status_driven` and rewrite `test_focus_follows_the_item_key_across_committed_re_resolution` against a surviving row-bearing surface; drop the `SUGGESTIONS_CARD_SELECTOR` import and suggestion test-id literals. `test_browser_contextual_hud_dock.py`: drop the deleted imports, rewrite `test_breadcrumb_tracks_router_depth` on a surviving frame, and drop the `controls["pill"]` assertion. `test_browser_exploration_nav.py`: drop `PILL_SELECTOR` and the `controls["pill"]` assertion. `test_browser_exploration_frame.py`: rewrite `test_resolver_table_resolves_purely_against_the_committed_snapshot` without `state.suggestionsCard`.
- [x] 7.5 `.github/browser-shards.json`: also remove `web.tests.browser.test_browser_exploration_state.ExplorationBrowserTest.test_suggestions_frame_is_status_driven`.
- [x] 7.6 `.github/browser-shards.json`: remove the ten `OptionsSurfaceBrowserTest` method labels from `files_a`.
- [x] 7.7 `.env.example`: remove the `ELOSERN_BROWSER_OPTIONS_SURFACE` example line.

## 8. Evidence, frozen contract, and docs

- [x] 8.1 `web/webclient/tests/test_node_suite_evidence.py`: delete `test_option_cards_node_suite_passes`, `test_options_view_node_suite_passes`, and `test_choicepoint_node_suite_passes` and their annotations. The choicepoint test is the sole evidence for `webclient-context-actions-suggestions::the-suggestions-card-is-the-single-suggestion-surface`, whose one-requirement REMOVED delta ships in this change (design D9).
- [x] 8.2 `web/webclient/tests/test_vue_showcase_action_evidence.py`: drop the three suggestions story IDs from the pinned list.
- [x] 8.3 `docs/development/webclient-vue-frozen-contract-audit.md`: remove the four suggestion hook rows and the `choice-card-note` hook, drop `OptionCards`/`ChoicePoints` from the module-façade row, and replace both `webclient-options-surface:75-76` citations (the `window.Elosern.actions` façade row and the `data-item-key` hook row) with a surviving spec citation such as `webclient-action-dispatch` / `webclient-pointer-activation`.
- [x] 8.4 `docs/development/evennia-testing-guide.md`: delete the options-surface fixture paragraph. `web/webclient-app/AGENTS.md`: update the ChoiceCard and room-action descriptions.
- [x] 8.5 `tools/observability_freeze.json` and `tools/test_data_freeze.json`: confirm neither names a deleted file (expected: no edit). Do not add entries.

## 9. Verification

- [x] 9.1 `openspec validate retire-action-options-webclient --strict` passes.
- [x] 9.2 `pnpm exec vitest run web/webclient-app/tests/` passes (the full Vitest suite is the smallest gate that covers the shared view store and the AppClient composition).
- [x] 9.3 `node --test web/static/webclient/js/tests/*.test.js` passes.
- [x] 9.4 `pnpm run build-storybook` and `pnpm run showcase-coverage` pass with the four `Action/ActionDock` suggestion stories gone and every remaining manifest component still covered.
- [x] 9.5 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract` passes (create `.env.test` containing `MUD_TEST_SETTINGS=1` if absent).
- [x] 9.6 `uv run --locked python -m tools.spec_traceability check` passes; no annotation references a removed requirement.
- [x] 9.7 Browser smoke: run one surviving journey that opens the rest entry and one that walks the shortened Tab chain, for example `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration.ExplorationJourneyBrowserTest` (pick the exact class from the file), and confirm the pill is absent.
- [x] 9.8 `uv run --locked python -m tools.contract_gate --change retire-action-options-webclient` passes.
