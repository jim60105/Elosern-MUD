## 1. Preconditions

- [x] 1.1 Confirm C4b (`webclient-avg-place-card-top-bar`) is archived, or will be before this change (archive order C1 → C2 → C3 → C4a → C4b → C4c).
  - If any requirement text this change builds on changed after it was written, re-sync this change's block to it and keep only this change's edits (design D5). Those texts are C4b's stage and visibility blocks, C4a's reference-surface block, C3's island-stack and party blocks, C1's minimap-convention block, and C2's `webclient-local-map` minimap block.
  - Checked at apply time: the `webclient-local-map` block was re-synced onto the current main text (which had gained the 0.75 scale floor and the floating view controls). Only its two `hud-right` words change.
- [x] 1.2 List every consumer to update (stop and report any hit outside the files named in sections 2–5):
  - `grep -rn "hud-left\|hud-right\|panel-left\|panel-right\|#objectives\|name=\"objectives\"" web/webclient-app --include='*.vue' --include='*.js' --include='*.css'` (excluding `dist/`)
  - `grep -rn "objective-tracker__count\|objective-tracker__deadline\|objective-tracker__row\|party-strip__empty-slot\|party-strip__name\|party-strip__state\|emptyCount" web --include='*.vue' --include='*.js' --include='*.py'` (excluding `dist/`)

## 2. Anchors

- [x] 2.1 `components/HudFrame.vue`:
  - rename the anchors to `vitals` (`data-testid="anchor-vitals"`, slot `vitals`) and `map` (`data-testid="anchor-map"`, slot `map`), keeping their CSS values
  - delete the `objectives` slot and the `.obj` part of the menu-open selector
  - hide `[data-anchor="map"]` in creation
  - add the exploration-only `.obj` rule of design D2
  - rewrite the header comment
- [x] 2.2 `components/AppShell.vue`:
  - forward `vitals` / `map` slots (rename `panel-left` / `panel-right`) and drop `objectives`
  - set `HIDDEN_BY_MODE.creation` per design D1
- [x] 2.3 `AppClient.vue`:
  - rename `#panel-left` to `#vitals` and `#panel-right` to `#map`
  - move `<ObjectiveTracker v-if="showObjectiveTracker" :rows="store.objectivesRows" />` from the deleted `#objectives` template into `#map`, directly after `LocalMap`
  - order `#map` as `LocalMap`, `ObjectiveTracker`, `ParticipantFrame`, `TitleBallotMenu`
  - rewrite the slot comments (the H2/H3/H4 comments naming the right anchor)
- [x] 2.4 `styles/app-shell.css`:
  - rename every `[data-anchor="hud-left"]` / `[data-anchor="hud-right"]` selector to `vitals` / `map`
  - drop `.obj` from the menu-open filter rule
  - at `max-width: 1350px`, set `--right-column: 246px` so the `map` anchor is exactly the minimap card's 218px (design D1)

  Comment-only updates in `components/ParticipantFrame.vue` and `StatusPanel.vue` (`LocalMap.vue` names no anchor).

  `grep -rn "hud-left\|hud-right" web/webclient-app --include='*.vue' --include='*.js' --include='*.css'` (excluding `dist/`) returns nothing.

## 3. Objective line and compact party

- [x] 3.1 `components/ObjectiveTracker.vue`: rewrite the template and scoped CSS per design D2:
  - one 32px row; `目標` label; the first row's box, text (ellipsis, `title`), and `.pr` slot
  - `objective-tracker__more` `+N`
  - no absolute positioning
  - delete the header count and deadline markup
  - rewrite the header comment

  `stories/Overlays/ObjectiveTracker.stories.js`: keep the existing story IDs, and add a `LongLine` story. The existing `ActiveObjectives` story already commits three rows, so it shows `+2`.
- [x] 3.2 `components/PartyStrip.vue`: compact cells per design D3:
  - `title` equal to the `aria-label`
  - the token as an avatar badge
  - the HP hairline under the avatar
  - delete the name, the state row, `emptyCount`, and the invite cells, and rewrite the header comment

  `stories/Overlays/PartyStrip.stories.js`: keep the story IDs and update the descriptions (no invite padding).

- [x] 3.3 `stories/Core/AppShell.stories.js`: add a `PopulatedHud` player story (a vital below its maximum, a harmful condition, a two-slot party, three tracked objectives) and a `CombatHud` player story (combat mode with participants). They are the visual-review targets for the `vitals` and `map` anchors. `stories/Core/HudFrame.stories.js`: sample blocks for the `vitals` and `map` slots. `stories/World/MapLattice.stories.js`: comment names the `map` anchor. No component is added, so the manifest is unchanged.

  Run `pnpm run build-storybook`; green.

- [x] 3.4 Short-viewport compaction (design D6), under `@media (max-height: 820px)`:
  - `styles/tokens.css`: add `--stage-inset-y: 16px`, and use it in place of the vertical `16px` / `44px` / `32px` literals of the `place`, `vitals`, and `map` offsets in `HudFrame.vue` and `app-shell.css`
  - `styles/app-shell.css`: `--place-h: 56px; --stage-inset-y: 10px;` and a `vitals` anchor gap of 8px
  - compact rules in `VitalsTrack.vue` (one-row gauges), `ConditionChips.vue` (26px chips, tighter disclosure), and `PartyStrip.vue`
  - at 1280x720, the populated stack with eight disclosed conditions and a party of four fits the `vitals` anchor

## 4. Vitest

- [x] 4.1 `tests/overlays/objective_tracker.test.js`:
  - "renders the tracker header with the row count" becomes "renders the 目標 label and a +N count for further rows" (0 rows beyond the first: no `objective-tracker__more`; 3 rows: `+2`)
  - "renders rows in payload order" becomes "renders only the first row"; the second row's testids are absent
  - keep the checkmark case and the `.pr` slot matrix case against the first row
  - "renders a deadline line…" becomes "renders no deadline line on the stage"
  - keep the empty and display-only cases
  - add: a long `objective_line` sets `title` to the full text

  `tests/overlays/objective_tracker_integration.test.js`: mount through `AppClient`/`AppShell` and assert the tracker is inside `[data-anchor="map"]`, directly after `[data-testid="local-map"]`.

  `tests/hud_frame.test.js`: the stage CSS hides `[data-anchor="map"] .obj` outside exploration, and creation hides `[data-anchor="map"]`.
- [x] 4.2 `tests/data/party_strip.test.js`:
  - "mirrors the committed party slots with count N / 4 and invite padding" becomes "…with count N / 4 and no invite padding"; also assert each cell's `title` and `aria-label` state name, numerals, and bond, and no `party-strip__name` exists
  - "renders zero dashed invite cells and 4 / 4 for a full party" becomes "renders four compact cells and 4 / 4 for a full party"
  - the token case asserts the badge inside `party-strip__avatar`
  - keep the empty-party case from C3

  `tests/app.test.js` and `tests/data/status_panel.test.js`: anchor names `anchor-vitals` / `anchor-map`.

  `tests/app_client_drawers.test.js`: rename the `panel-left` wording in the party quickbar test's title and comment to the `vitals` anchor.

  `tests/world/local_map.test.js`: rename any surviving `data-anchor="hud-right"` fixture attribute to `map`.

  Run `pnpm exec vitest run web/webclient-app/tests/overlays web/webclient-app/tests/data web/webclient-app/tests/world web/webclient-app/tests/hud_frame.test.js web/webclient-app/tests/app.test.js web/webclient-app/tests/store`; green.

## 5. Browser tests

- [x] 5.1 `grep -rn "anchor-hud-\|hud-left\|hud-right" web/tests/browser`. Re-point every hit to `anchor-vitals` / `anchor-map` / `data-anchor="vitals"` / `data-anchor="map"`, including:
  - the anchor-id lists in `test_browser_contextual_hud_anchors.py`, `test_browser_layout.py`, `test_browser_contextual_hud_drawers.py`, and `test_browser_shell_surfaces.py`
  - the `hudLeft` / `hudRight` targets in `test_browser_contextual_hud_stage.py::test_command_line_never_overlaps_dock_caption_or_hud`
  - the clamp anchor in `test_browser_combat_menu.py::test_dock_and_participant_frame_geometry_at_both_desktop_viewports`. Today it clamps to `[data-anchor="hud-left"]` while the frame lives in `hud-right`, so the clamp returns null and the intersect checks pass vacuously. It now clamps to `[data-anchor="map"]`, asserts the clamped box is non-null, asserts the frame is a descendant of `map` and not of `[data-anchor="actor-right"]`, and adds a non-intersection check against `[data-anchor="command-line"]`
  - the stale description string in `test_browser_art.py` ("the participant frame (hud-left island)")
  - the anchor scroll checks in `test_browser_local_map_lattice.py` and any left in `test_browser_local_map_geometry.py`
- [x] 5.2 `test_browser_shell_surfaces.py::test_populated_island_stack_fits_its_anchor_at_both_viewports`: measure the `vitals` stack (compact party) against `anchor-vitals` and the `map` stack against `anchor-map`, at both viewports. If C4a / C4b applied the Risks fallback (8px gap, compact cells) and the stack now fits without it, remove the fallback.

  Add `test_objective_line_shows_only_in_exploration` to `test_browser_contextual_hud_stage.py`, annotated `webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode` and `webclient-contextual-hud::the-objective-tracker-island-presents-the-committed-objectives-only`:
  - inject a two-row `objectives` panel
  - in exploration, `objective-tracker` is visible inside `anchor-map` below `local-map`, reads `+1`, and is one line tall (≤ 34px)
  - after injecting combat mode it is not visible; in dialogue it is not visible; back in exploration it is visible

  Run each touched method on its own (AGENTS.md: focused single-method runs only, never two browser runs at once; the full browser suite is CI-only), each green:
  - `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.<module>.<Class>.<method>` for:
    - `test_browser_contextual_hud_anchors`: `test_caption_wider_and_no_anchor_overlap`, and the anchor-id-list method
    - `test_browser_layout`: `test_no_stage_anchor_overlaps_at_supported_viewports`, `test_mode_gating_hides_and_restores_surfaces`
    - `test_browser_contextual_hud_drawers`: the anchor-id-list method
    - `test_browser_shell_surfaces`: `test_stage_anchors_do_not_intersect_at_both_viewports`, `test_populated_island_stack_fits_its_anchor_at_both_viewports`
    - `test_browser_contextual_hud_stage`: `test_command_line_never_overlaps_dock_caption_or_hud`, `test_objective_line_shows_only_in_exploration`, `test_stage_box_is_at_least_65_percent_at_the_reference_viewport`
    - `test_browser_combat_menu`: `test_dock_and_participant_frame_geometry_at_both_desktop_viewports`
    - `test_browser_local_map_lattice`: the method holding the `map` anchor scroll check
- [x] 5.3 `.github/browser-shards.json`: add `test_objective_line_shows_only_in_exploration` to the shard holding `test_browser_contextual_hud_stage`.

## 6. Specs and traceability

- [x] 6.1 Sync this change's deltas (`openspec archive` at the end, or `openspec-sync-specs` first). No requirement ID changes.

  `grep -rn "hud-left\|hud-right" openspec/specs` returns nothing.

  Run `uv run --locked python -m tools.spec_traceability check`; green.

## 7. Validation

- [x] 7.1 Run every gate from the repository root, all green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `pnpm run build-storybook`
  - `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_overlays_evidence`
- [x] 7.2 Run `agent-browser` against the running client at 1920x1080:
  - In exploration, the top-right shows the minimap, then one objective line.
  - With a party, compact avatars sit under the vitals, and hovering one shows the name, HP, and bond.
  - In combat the objective line and minimap disappear and the participant frame takes the top-right.
  - In dialogue the objective line is hidden.

  Close the browser when done.
- [x] 7.3 Run `openspec validate webclient-avg-stage-hud-anchors --strict` and `git diff --check`; both clean.
