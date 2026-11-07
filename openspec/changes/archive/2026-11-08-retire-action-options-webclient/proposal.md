# Proposal

## Why

The AI 建議 surface — the pill at the top right of the exploration command panel and the centred suggestion card it opens — is an advisory layer on top of the deterministic exploration dock. It is the only consumer of the AI action-options pipeline (prompt, 12-stage ladder, trigger service, session options state) and it duplicates affordances the dock already renders from server-authored data. The project is retiring the whole action-options feature; this change removes its client-visible half, so the wire field can then be deleted without a second client churn.

## What Changes

- **BREAKING**: delete the 建議 pill from the exploration command panel and the centred suggestions card it opened, including the `suggestions-pill`, `suggestions-card`, `suggestions-card-row`, and `suggestions-card-dismiss` hooks and the 清除建議 row.
- **BREAKING**: delete the client suggestion machinery: `lib/option_cards.js` and the preserved `web/static/webclient/js/elosern/option_cards.js`, the `explorationSuggestions` resolver, the `suggestionsMenu`/`cardItems` exploration-menu builders, the store's `suggestionsCard` slice and `activateSuggestion`, and the room-card `suggestions` kind (the wait/rest room card survives).
- **BREAKING**: remove the `notes`, row-`hint`, and `icon: "trash"` affordances of `ChoiceCard`, whose only producer was the suggestions card; the card shell keeps every other consumer (dialogue picks, verb card, presence overflow, wait card, rest entry, sleep handoff).
- Shorten the exploration Tab chain to compass → rail → 查看房間 → 休息, drop the 建議 row from the controls reference and the help overlay, and drop the pill from the shared readout's hover sources and the dock icon vocabulary.
- Delete the options-surface Storybook stories/samples and the Vitest/Node/browser tests that pin the pill or the card; delete `web/tests/browser/test_browser_options_surface.py` and its fixture (`ELOSERN_BROWSER_OPTIONS_SURFACE`, the seed room, the replay client seam), and drop its `.github/browser-shards.json` method labels in the same change.
- Retire the `webclient-options-surface` capability and rewrite the layout/dock requirements that named the pill so the shipped contract describes only surfaces that exist.

Non-goals: the `context_actions.suggestions` field, the `options.dismiss` action, the generative layer, the trigger service, the prompt/profile/slot, and the schema version. Those land in the two dependent changes below; until then the server still emits `suggestions`, and this change leaves the field validated and simply unread by the client.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-options-surface`: REMOVED — the whole capability (four requirements).
- `webclient-context-actions-suggestions`: one requirement REMOVED — "The suggestions card is the single suggestion surface", whose only evidence is the Node choice-point test this change deletes; the four wire-contract requirements remain until `retire-context-actions-suggestions`.
- `webclient-room-actions`: the exploration root, the readout priority, the controls reference, and the retired-surface verification lose the pill; "The 建議 pill opens the suggestions card" is REMOVED.
- `webclient-frame-resolution`: the exploration table and the dynamic-row requirements lose the suggestions accessor; "Suggestions frames are status-driven" is REMOVED.
- `webclient-pointer-activation`: the inert-popover, exploration-root, and listbox scenarios lose the pill.
- `webclient-desktop-shell`: the required-surfaces, keyboard-routing, and pane-host requirements lose the pill and the suggestions card.
- `webclient-contextual-hud`: nine layout/legend/breadcrumb/pane/settings requirements lose the pill or the suggestions card; no other HUD behaviour changes.
- `webclient-component-showcase`: the required-story and action-dock-family requirements lose the suggestions stories and the card shape.

`webclient-context-actions`, `webclient-combat-menu`, and `action-options-*` are deliberately untouched here.

## Impact

- Client sources: `web/webclient-app/AppClient.vue`, `components/ChoiceCard.vue`, `components/dock-icons.js`, `composables/use-room-actions.js`, `composables/use-app-client.js`, `lib/{frame-resolvers,controls-reference,option_cards}.js`, `lib/elosern/{room_actions,view}.js`, `lib/elosern/hud.js`, `stores/elosern.js`, `web/static/webclient/js/elosern/{option_cards,exploration_menu}.js`.
- Stories: `stories/Action/ActionDock.stories.js`, `stories/Core/{AppShell,ChoiceCard,ExplorationScreen}.stories.js`, `stories/fixtures/scene_overview.js`.
- Tests: `web/webclient-app/tests/**` (Vitest), `web/static/webclient/js/tests/{option_cards,options_view}.test.js` deleted and `{exploration_menu,hud_dock_menus,ui_contract}.test.js` amended, `web/webclient/tests/test_node_suite_evidence.py`, `web/webclient/tests/test_vue_showcase_*_evidence.py`, `web/tests/browser/test_browser_options_surface.py` deleted, `web/tests/browser/{browser_helpers,_journey_support,browser_settings}.py` and `{test_browser_exploration_state,test_browser_contextual_hud_dock,test_browser_exploration_nav,test_browser_exploration_frame}.py` amended, `web/tests/browser/seed/options_surface_fixture.py` deleted with its `seed/__init__.py`/`seed/runner.py` wiring, `tests/test_frontend_toolchain_contract.py` amended.
- Manifests and gates: `.github/browser-shards.json` (10 method labels), `.github/evennia-shards.json` (no module added or removed), `tools/test_data_freeze.json` (no entry: no tagged data-contract test dies here), `tools/observability_freeze.json` (no entry).
- Docs: `docs/development/webclient-vue-frozen-contract-audit.md` (hook and façade rows), `docs/development/evennia-testing-guide.md` (options-surface fixture paragraph), `.env.example` (`ELOSERN_BROWSER_OPTIONS_SURFACE`), `web/webclient-app/AGENTS.md` (ChoiceCard props and the room-action card description).
- Player commands: unaffected. `docs/game/commands.md` and `docs/game/command-reference.md` document no 建議 command, and `options.dismiss` was never a typed command.
- Spec traceability: `uv run --locked python -m tools.spec_traceability check` must pass after apply; the retired `webclient-options-surface` IDs and the annotations pinned in `web/webclient/tests/` die with the code (the tool indexes main specs only, so no annotation debt is created).
- Human review: none required; every acceptance step below is mechanical (deleted hooks, rewritten specs, green focused gates).

## Batch:

Part of the AI action-suggestions retirement batch.

depends-on: none

Code-conflict notes: apply first. It removes the only client readers of `context_actions.suggestions`, so `retire-action-options-service` can delete the writer, and `retire-context-actions-suggestions` can delete the field, without a window in which the client renders a field the server no longer sends. `retire-action-options-service` then removes the backend that fed the field this change stops reading; apply them in order. The later changes own the Python shard and freeze edits, so this change does not touch `.github/evennia-shards.json`.
