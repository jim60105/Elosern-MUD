# Design

## Context

See `proposal.md` for motivation. The current client renders the AI 建議 surface from the committed `context_actions.suggestions` envelope in four places that must all go together: the `AppClient` pill and room card, the room-actions composable's card content and Tab chain, the store's room-card slice plus its frame-resolver accessor, and the shared static card module with its Storybook/Vitest/Node/browser coverage. The wire field itself stays in this change (the panel is not re-versioned here); the server writer and the field are removed by the two dependent changes.

## Goals / Non-Goals

**Goals:**

- The client presents no 建議 pill, no suggestions card, no suggestion rows, and no dismissal control in any state, and no client module reads `context_actions.suggestions`.
- Every other exploration surface (compass, readout, presence rail, verb card, place card's 查看房間/休息, wait card, rest entry, sleep handoff) behaves exactly as today.
- The shipped capability text describes only surfaces that exist: the dock/HUD/shell requirements that enumerated the pill or the card are rewritten, and the options-surface capability is retired.
- The browser suite, Storybook manifest, Node gate, and frozen-contract audit lose their suggestions coverage in the same commit.

**Non-Goals:**

- No change to `context_actions` schema/version, the `suggestions` field, `options.dismiss`, the action registry, the presentation validators, or the LLM layer. Change `retire-action-options-service` deletes those.
- No new suggestion source and no replacement card. The surface simply disappears.
- No change to the dialogue choice list, the presence rail, the place card's rest entry, or the combat dock.

## Decisions

**D1 — Delete, do not hide.** Every suggestion-specific module, field, prop, story, and test is deleted rather than left inert behind a false flag. The project is unreleased and has no compatibility obligation; an inert reader of a field that is about to disappear would be exactly the dead weight the cutover rule forbids.

**D2 — Split order: client first, then server, then the wire field.** Applying the client half first leaves the server emitting a `suggestions` envelope that nothing reads, which is a harmless intermediate state. The reverse order would make the client render a field the server no longer sends for the length of a change, and the final change would then have to touch the client twice. The three changes are `retire-action-options-webclient` → `retire-action-options-service` → `retire-context-actions-suggestions`.

**D3 — `ChoiceCard` sheds only its suggestions-only affordances.** `notes`, the per-row `hint` line, and the `icon: "trash"` badge have exactly one producer today (`suggestionsCardContent`). Removing them keeps the shell honest; every surviving consumer (dialogue picks, verb card, presence overflow card, wait card, rest entry, sleep handoff) uses rows with label/badge/kind/enabled/testId only. `block`, `caption`, `trailingIndex`, `viewKey`, focus trapping, digit handling, and the entrance animation are untouched.

**D4 — The wait/rest room card survives; only the `suggestions` kind is deleted.** `ROOM_CARD_KINDS` becomes `{"wait"}`, and `openRoomCard("wait")` keeps its availability gate. `roomCard` stays `{kind: "wait", location}`; the `suggestions`-specific computed properties (`suggestionsCardContent`, `roomCardNotes`, `roomCardShown`, `roomCardCaption`, `roomCardLabel`, `onPill`, `onRoomCardPick`) die. `activeSubDock` stays because the drawer/frame teardown still uses it (`stores/elosern/{hud,frames}.js`); only its "suggestions section" comment changes.

**D5 — Keep the static modules that other surfaces use.** `web/static/webclient/js/elosern/exploration_menu.js` survives as the builder module for the compass, rail, verb card, and look rows; only `suggestionsMenu` and `cardItems` are deleted, and `cardItems` has no other caller. `choicepoint_logic.js` and `stream_end_block.js` are not suggestion renderers any more (the narrative choice-point was retired by `webclient-align-03-narrative-feed`); they are out of scope and stay untouched.

**D6 — Retire `webclient-options-surface`; rewrite the enumerating requirements.** The four requirements of the client render contract are REMOVED. The requirements in other capabilities that name the pill or the card are MODIFIED with their full updated block (body plus every scenario). The schema forbids renaming or dropping a scenario inside a MODIFIED requirement (`openspec validate --strict` reports an omitted/added scenario), so a scenario that named the retiring element keeps its identity and its body states the post-retirement truth (for example "no 建議 pill is rendered"). Whole suggestion-only requirements, where every scenario is about the surface, are REMOVED instead.

**D7 — The panel contract is untouched here.** `context_actions` stays at schema version 8 with the `suggestions` field in this change; `web/static/webclient/js/elosern/protocol/panels/suggestions.js`, its parity test, and every `suggestions: {...}` test fixture stay valid. Only the client *render* path stops reading the field. The field and its version bump are `retire-context-actions-suggestions`'s job.

**D8 — Browser and showcase coverage is deleted, not skipped.** The options-surface browser file, its seed room, its runtime env fixture, and its replay-client seam exist only for this surface. The Storybook stories and the Node evidence tests exist only to prove the deleted module. Deleting them together keeps every gate green without a skip, and `.github/browser-shards.json` loses exactly its ten `OptionsSurfaceBrowserTest` labels.

**D9 — The "single suggestion surface" requirement is retired here, not last.** Its only repository evidence is the Node choice-point test, which this change deletes. Leaving the requirement in the main specs until the wire change would leave it uncovered and fail `spec_traceability` at this landing point, so this change carries a one-requirement `REMOVED` delta for `webclient-context-actions-suggestions`; the remaining four requirements are retired by `retire-context-actions-suggestions`.

## Delete / amend matrix

### Client sources — delete

| File | Why |
|---|---|
| `web/webclient-app/lib/option_cards.js` | ESM wrapper over the deleted card module; only consumer was `view.js`/`frame-resolvers.js`. |
| `web/static/webclient/js/elosern/option_cards.js` | The shared suggestion-card builder/view model (`buildCard`, `buildDismissButton`, `buildOptionsView`, `suggestionsSignature`). |

### Client sources — amend

| File | Change |
|---|---|
| `web/webclient-app/AppClient.vue` | Delete the pill button (`exploration-pill` + `suggestions-pill`, `pillLabel`, `pillCount`, `@click="onPill"`) and the suggestions branch of the room-card template/comment; keep the wait/rest templates. |
| `web/webclient-app/components/ChoiceCard.vue` | Delete the `notes` prop and its `<p class="choice-card__note">` block, the per-row `hint` line, the `icon === "trash"` badge and its CSS, and the suggestions wording in the header comment. |
| `web/webclient-app/components/dock-icons.js` | Delete the `suggestions` glyph entry and the comment naming it. |
| `web/webclient-app/composables/use-room-actions.js` | Delete `suggestionsCardContent`, the pill computed values and handlers, the `pill` Tab-chain slot, the `suggestions` room-card kind and its computed properties; keep the wait layer state machine and the readout feed for the place-card buttons. |
| `web/webclient-app/composables/use-app-client.js` | Delete the `onPillHover` wiring and the comment; the compass keeps its readout hover source. |
| `web/webclient-app/composables/use-exit-compass.js` | Delete the `pill` readout source state (`setPill`, the pill branch of `onPillHover`, and the off-pill fallback) and `use-person-focus.js`'s comment; a room card means the wait card. |
| `web/webclient-app/components/exploration-readout.js` | Delete `pillReadout` and the `pill` parameter/branch of `readoutContent`. |
| `web/webclient-app/stores/frame-resolvers.js` | Delete `SUGGESTIONS_RESOLVABLE` and `explorationSuggestions`, its registry entry, and its export. |
| `web/webclient-app/lib/controls-reference.js` | Delete the `pill` entry; retitle the `room` group `地點`, and rewrite `tab-order`/`room-card-escape` to the shortened chain. |
| `web/webclient-app/stores/elosern/room_actions.js` | `ROOM_CARD_KINDS` → `{"wait"}`; delete `activateSuggestion` and the suggestions branches of `openRoomCard`, `closeOnCommit`, and `roomActionsView`. |
| `web/webclient-app/stores/elosern/view.js` | Delete `suggestions`, `suggestionsView`, and `suggestionsSignature` from the view slice and the `OptionCards` import. |
| `web/webclient-app/stores/elosern/hud.js` | Comment only (the sub-dock note no longer mentions the suggestions section). |
| `web/webclient-app/stores/elosern.js` | Delete the `activateSuggestion` re-export. |
| `web/webclient-app/logic.js` | Delete the `OptionCards` import/export. |
| `web/static/webclient/js/elosern/exploration_menu.js` | Delete `suggestionsMenu`, `cardItems`, their export, and the suggestions rows in the module header. |

### Stories — amend

| File | Change |
|---|---|
| `web/webclient-app/stories/Action/ActionDock.stories.js` | Delete the pill markup in `renderOverview`, the `suggestions` arg on the remaining stories (including `ExplorationDock`, which stays), and the `GeneratingSuggestions`/`DegradedEmptySuggestions`/`UnavailableSuggestions` stories; there is no plain `Suggestions` story. |
| `web/webclient-app/stories/fixtures/action_dock.js` | Delete the four `SUGGESTIONS_*_SAMPLE` constants. |
| `web/webclient-app/stories/Core/AppShell.stories.js` | Delete the `suggestions` fixture from the exploration `context_actions` payload (it stays valid to omit; the panel field is still optional in fixtures only because change three removes it). |
| `web/webclient-app/stories/Core/ChoiceCard.stories.js` | Delete all three suggestion stories (`Suggestions`, `SuggestionsGenerating`, `SuggestionsDegradedEmpty`), the `suggestionsCardArgs` import, and the notes/hint/trash wording from the header. |
| `web/webclient-app/stories/Core/ExplorationScreen.stories.js` | Delete the `suggestions` card case, the `SuggestionsCard` story, and the import. |
| `web/webclient-app/stories/fixtures/scene_overview.js` | Delete `suggestionsCardArgs` and the suggestions sample fixture. |

### Tests — delete

| File | Why |
|---|---|
| `web/static/webclient/js/tests/option_cards.test.js` | Pins the deleted card module. |
| `web/static/webclient/js/tests/options_view.test.js` | Pins the deleted view model and signature. |
| `web/tests/browser/test_browser_options_surface.py` | The whole managed browser file for the deleted surface. |
| `web/tests/browser/seed/options_surface_fixture.py` | The fixture seeds rooms and an NPC/monster only that file uses. |

### Tests — amend

| File | Change |
|---|---|
| `web/webclient-app/tests/app_client_room_actions.test.js` | Delete the `the 建議 pill and the suggestions card` block, the `pill`/`sugCard`/`suggestionsCommit` helpers, and the suggestions fixture; keep the wait/rest/focus/readout tests. |
| `web/webclient-app/tests/app_client_presence_rail.test.js` | Tab-chain test ends at 休息; the inert-panel fallback test targets 休息 instead of the pill. |
| `web/webclient-app/tests/app_client_scene_overview.test.js` | The exploration root's right column holds only `exploration-readout`. |
| `web/webclient-app/tests/app_client_frameless_bag.test.js`, `tests/bridge/bridge.test.js`, `tests/preserved_contract.test.js`, `tests/store/store_dispatch_focus.test.js` | Comments and the root-tab-stop enumeration lose the pill. |
| `web/webclient-app/tests/frame-resolvers.test.js` | Delete every `explorationSuggestions` case and the suggestions fixture fields. |
| `web/webclient-app/tests/store/room_cards.test.js` | Delete the suggestions tests; keep the wait card's open/close/transport/sub-dock cases. |
| `web/webclient-app/tests/store/digit_row_picks.test.js` | Drop the suggestions fixture and the footer-chip comment. |
| `web/webclient-app/tests/components/choice_card.test.js` | Delete the hint/notes/trash test; the remaining row tests cover the shell. |
| `web/webclient-app/tests/components/dock_panes.test.js` | Delete the `options.dismiss` row fixture. |
| `web/webclient-app/tests/components/exploration_readout.test.js` | Delete `pillReadout` and its assertions. |
| `web/webclient-app/tests/components/dock_icons.test.js` | Drop `suggestions` from the expected glyph map and the no-stroke list; the `skills` star glyph keeps the star assertion. |
| `web/webclient-app/tests/action/action_dock.test.js` | Drop the `suggestions` root item and the `dockSource: "suggestions"` crumb fixture. |
| `web/webclient-app/tests/overlays/help_overlay.test.js` | Drop the pill row and the 建議 assertions from the tab-order/escape rows. |
| `web/webclient-app/tests/transport.test.js` | Drop the `suggestions` view key from the empty-view fixture. |
| `web/webclient-app/tests/store/store_slices.test.js` | Delete the "drives the suggestions view model from the committed suggestions" test (`suggestionsView`/`suggestionsSignature`). |
| `tests/test_frontend_toolchain_contract.py` | Remove `option_cards.js` from the preserved-wrapper tuple so the deleted wrapper is not required. |
| `web/static/webclient/js/tests/exploration_menu.test.js` | Drop the `suggestionsMenu` assertions (rows, back cell, title). |
| `web/static/webclient/js/tests/hud_dock_menus.test.js` | Drop the suggestions-row tests and the suggestions title assertion. |
| `web/static/webclient/js/tests/ui_contract.test.js` | Assert the absence of `suggestions-pill`/`suggestions-card` in `AppClient.vue` instead of their presence. |
| `web/webclient/tests/test_node_suite_evidence.py` | Delete `test_option_cards_node_suite_passes`, `test_options_view_node_suite_passes`, and `test_choicepoint_node_suite_passes` (the last pinned the deleted `app_client_room_actions` suggestions coverage) and the room-actions docstring wording. |
| `web/webclient/tests/test_vue_showcase_action_evidence.py` | Drop `action-actiondock--degraded-empty-suggestions`, `--generating-suggestions`, and `--unavailable-suggestions` from the pinned story list. |
| `web/tests/browser/test_browser_exploration_state.py` | Delete `test_suggestions_frame_is_status_driven` (and its shard label); rewrite `test_focus_follows_the_item_key_across_committed_re_resolution` against a surviving row-bearing surface; drop the `SUGGESTIONS_CARD_SELECTOR` import and the suggestion test-id literals. |
| `web/tests/browser/test_browser_contextual_hud_dock.py` | Drop the `SUGGESTIONS_CARD_SELECTOR`/`_suggestions_ready` imports; rewrite `test_breadcrumb_tracks_router_depth` on a surviving frame; drop the `controls["pill"]` assertion. |
| `web/tests/browser/test_browser_exploration_nav.py` | Drop the `PILL_SELECTOR` import and uses; drop the `controls["pill"]` assertion in `test_escape_at_intermediate_depth_keeps_cells_matched_to_the_frame`. |
| `web/tests/browser/test_browser_exploration_frame.py` | Rewrite `test_resolver_table_resolves_purely_against_the_committed_snapshot` without `state.suggestionsCard`. |
| `web/tests/browser/browser_helpers.py` | Delete `SUGGESTIONS_CARD_SELECTOR`, `PILL_SELECTOR`, `open_suggestions_card`, `suggestion_row_key`, the `suggestions` routing in `activate_overview_chip`, and the `pill` field of `exploration_root_controls`; the dock-available probe stops reading the `suggestions` view. |
| `web/tests/browser/_journey_support.py` | Delete `_suggestions_ready`. |
| `web/tests/browser/browser_settings.py` | Delete the `ELOSERN_BROWSER_OPTIONS_SURFACE` gate on the `action_options` profile, the replay-client builder, and the `_build_action_options_client` seam assignment. |
| `web/tests/browser/seed/__init__.py`, `web/tests/browser/seed/runner.py` | Remove the `_options_surface_fixture` import/re-export, the package-docstring mention, and the `_options_surface_fixture(character)` call. |

### Manifests, gates, docs — amend

| File | Change |
|---|---|
| `.github/browser-shards.json` | Remove the ten `OptionsSurfaceBrowserTest` method labels from `files_a`; leave the remaining entries in the shard. |
| `docs/development/webclient-vue-frozen-contract-audit.md` | Remove the `suggestions-pill`, `suggestions-card`, `suggestions-card-row`, and `suggestions-card-dismiss` hook rows and the `choice-card-note` hook (its notes are deleted with the card); drop `OptionCards`/`ChoicePoints` from the module-façade row; replace both `webclient-options-surface:75-76` citations (the `window.Elosern.actions` row and the `data-item-key` row) with a surviving spec. |
| `docs/development/evennia-testing-guide.md` | Delete the options-surface fixture paragraph. |
| `.env.example` | Delete the `ELOSERN_BROWSER_OPTIONS_SURFACE` example line. |
| `web/webclient-app/AGENTS.md` | Update the ChoiceCard and exploration-room-actions descriptions (no notes/hint/trash, no pill or suggestions card). |
| `tools/observability_freeze.json`, `tools/test_data_freeze.json` | No entry changes; verified: neither list names a file this change deletes. |

## Consequence summary

**Dock.** The exploration command panel ships exactly two things: the exit compass on the left and the shared readout on the right. The Tab chain shortens from five stops (compass → rail → 查看房間 → 休息 → pill) to four. The controls reference's `地點與建議` group becomes `地點` and loses its 建議 row. The readout keeps the compass aim, rail entries, and place-card buttons as its content sources; the idle summary and the blocked-move flash are unchanged.

**Card.** The only centred `ChoiceCard` over the stage in exploration is the wait/rest entry's shared shell and the sleep handoff/continuation cards. No card is opened from the command panel any more.

**Panel version.** Unchanged in this change: `context_actions` stays at schema version 8, and the `suggestions` envelope remains a valid, required field on both available forms. The client simply stops reading it. The field's removal and the 8→9 bump belong to `retire-context-actions-suggestions`.

**Surviving shared code.** `web/webclient/presentation/affordances.py` (server) and the static `exploration_menu.js` builder are untouched here except for the client-side `suggestionsMenu` deletion; the canonical affordance vocabulary, `ChoiceCard`, `TimeChoiceCard`, the presence rail, and the compass are all still consumed.

## Risks / Trade-offs

- [A client test fixture still asserts a suggestion view key that the store no longer produces] → the Vitest run in tasks 6 lists every failing file; the fixture cleanup is enumerated per file, not left to discovery.
- [The frozen-contract audit's hook registry and the browser suite disagree after deleting the browser file] → both are edited in the same commit, and task 8 runs `tests.test_webclient_frozen_contract` and `tests.test_evennia_test_optimization_contract`.
- [The server still emits `suggestions` between this change and `retire-context-actions-suggestions`] → accepted intermediate state; no client reader exists, the mirror still validates the field, and the follow-up change deletes it.
- [Scenario titles in the rewritten capabilities still name the pill because the delta schema forbids renames] → each such body states the retirement explicitly, and `retire-context-actions-suggestions`'s sync is the moment those requirement blocks are finalized in the main specs. Recorded here so the wording is not mistaken for a live surface.
