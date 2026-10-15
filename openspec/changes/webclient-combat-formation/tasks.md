# Tasks

Prerequisite: `webclient-combat-formation-engine` is archived.

Rules:

- Follow root `AGENTS.md` "Testing": focused commands only, browser output captured to a scratch file, no loops over
  browser files.
- Before changing an assertion, note in the commit body what it guarded, and replace it with an assertion that
  detects the same defect.
- **Styling pitfall** (`web/webclient-app/AGENTS.md`): grep `styles/app-shell.css` for `.elosern-root` rules on
  `foe-lineup`, `companion-lineup`, `participant-frame` and the `map` anchor, and remove or update them; verify
  geometry with the live-client browser test, not only Storybook.

## 1. Formation on stage (≈2.5 h)

- [x] 1.1 `AppClient.vue`: compute `formation` (design D1) with a ResizeObserver on the stage and the vitals dock, and
  pass it to both line-ups. `components/HudFrame.vue`: in combat, set the portrait anchors to `inset: 0`, add the
  `plates` layer/slot, and hide the `map` anchor (design D2).
- [x] 1.2 `components/CompanionLineup.vue` and `components/FoeLineup.vue`: the `formation` prop, stage-coordinate slots
  and the shared slot transition with its reduced/off/hydration rules (design D3). `components/foe-lineup.js`: set the
  cap to 15 (named `FOE_STAGE_MAX`) and retire `FOE_SCALES`/`FOE_EXPOSED`/`FOE_LIFT` and the floor name/gauge markup.
- [x] 1.3 Vitest:
  - `tests/core/companion_lineup.test.js`: formation slots used only when `formation` is set, and exploration
    geometry unchanged;
  - `tests/core/foe_lineup.test.js`: 15 foes rendered, presenter order, no floor plate;
  - `tests/hud_frame.test.js`: the anchors' `inset: 0` in combat, the `map` anchor hidden in combat, the plates layer;
  - `tests/mode_transitions.test.js`: one shared slot transition rule, and none at reduced/off.

  Run
  `pnpm exec vitest run web/webclient-app/tests/core/companion_lineup.test.js web/webclient-app/tests/core/foe_lineup.test.js web/webclient-app/tests/hud_frame.test.js web/webclient-app/tests/mode_transitions.test.js web/webclient-app/tests/core/combat_formation.test.js`
  and verify it passes.

## 2. Glance plates and roster removal (≈2.5 h)

- [x] 2.1 Create `components/FigurePlate.vue` (design D4: the 52/36px·S line layouts, the repeated-name token) and
  change the beat step distance to `12px·S` (the `--motion-beat-lunge` token in `styles/tokens.css` that `components/StageActor.vue`'s lunge keyframes read; design D4b) and render one per non-controlled figure in the plates
  layer from `formation` slots, `displayHp`/committed HP, and the participant names.
- [x] 2.2 Delete `components/ParticipantFrame.vue`, `stories/Data/ParticipantFrame.stories.js`,
  `tests/core/participant_frame.test.js` and `tests/combat/participant_frame.test.js`. Update
  `tests/overlays/deferred_surfaces_absent.test.js` and `component-manifest.json` (remove `Data/ParticipantFrame`,
  add `Core/FigurePlate`), following the test-id table (design D5).
- [x] 2.3 Add `tests/core/figure_plate.test.js`: the full and compact forms, the readout text, the stroke fraction, the
  trailing segment, the accessible name with side and token, and the `displayHp` override. Run
  `pnpm exec vitest run web/webclient-app/tests/core/figure_plate.test.js web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`
  and verify it passes. Run `node --test web/static/webclient/js/tests/ui_contract.test.js` and verify it passes.

## 3. Live-client browser verification (≈2 h)

Build once: `pnpm run build`.

- [x] 3.1 Add `test_combat_formation_shares_one_scale_and_keeps_the_centre_clear` to
  `web/tests/browser/test_browser_combat_stage.py` `CombatStageBrowserTest`. At 1451x790 and 1600x900, for parties
  of 1, 3 and 5 figures against 1, 4, 8 and 16 − party foes (fixtures must stay within the 16-participant bound):
  - every figure box on both sides has equal height (±1px), including at three sampled frames while entering combat
    at `full`;
  - no box or plate is inside `centre ± 148px·S`;
  - plates are pairwise disjoint and clear of the vitals dock and the top band;
  - the place card and the `map` anchor are not rendered;
  - leaving combat restores the exploration boxes (±1px);
  - during a played round, no figure box enters the card's columns (`centre ± 132px·S`) at the lunge's farthest
    frame;
  - three same-named foes show their tokens on their plates.

  Register it in `.github/browser-shards.json` beside `CombatStageBrowserTest.test_foes_stand_opposite_the_player`.
  Rewrite that existing method's three-foe depth assertions as formation assertions; it guarded the foe placement
  defects. Run both methods with `web.tests.browser.unittest_driver` and verify they pass.
- [x] 3.2 Extend `web/tests/browser/test_browser_proportional_ui_scale.py`
  `ProportionalUiScaleBrowserTest.test_resize_keeps_pointer_targets_live` with a resize while combat is shown: after
  the resize, the formation matches the new stage and the root-row click still activates once. Run it and verify it
  passes.
- [x] 3.3 Migrate the browser methods that read `participant-frame`, `participant_frame` or `foe-gauge`. Find them with
  `grep -rn "participant-frame\|participant_frame\|foe-gauge\|foe-lineup__name" web/tests/browser`. Run each affected
  method by its full label, one file per command (for example
  `web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_dock_and_participant_frame_geometry_at_both_desktop_viewports`
  and the `test_browser_art.py` combat portrait methods), and verify they pass.

## 4. Storybook and documentation (≈1 h)

- [x] 4.1 Add the stories of design D6. Run `pnpm run build-storybook` then `pnpm run showcase-coverage` and verify both
  succeed with the updated manifest. Screenshot `core-appshell--combat-solo-fifteen-foes` and
  `--combat-full-party-eleven-foes` at 1451x790 and 1600x900 and confirm one scale and a clear centre.
- [x] 4.2 Amend `web/webclient-app/AGENTS.md`'s layout bullets: in combat both sides stand in one shared-scale
  formation around a clear centre, each figure carries a plate, and the place card and the roster are not shown.

## 5. Gates (≈0.5 h)

- [x] 5.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`,
  the Evennia focused labels `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract`
  (env file with `MUD_TEST_SETTINGS=1`), and `openspec validate webclient-combat-formation --strict`. Verify all pass.

## 6. Heads never covered (user decision at apply time, design D7)

- [ ] 6.1 `components/combat-formation.js`: the head proxy, the head fit conditions, the two-rank front plates on
  the floor line, the optional command-line input (HudFrame probe + `use-combat-formation.js`); re-derive the
  invariants and re-pin the table and the anchors in `tests/core/combat_formation.test.js`. Run
  `pnpm exec vitest run web/webclient-app/tests/core/combat_formation.test.js` and verify it passes.
- [ ] 6.2 Amend the contextual-hud delta (the engine requirement, the plates requirement, "Combat identity and status
  remain legible") and add the `avatar-artwork-presentation` delta (no participant avatars). Run
  `openspec validate webclient-combat-formation --strict`.
- [ ] 6.3 Extend `test_combat_formation_shares_one_scale_and_keeps_the_centre_clear`: no plate covers any head (front
  or back rank), no front figure covers a back head, heads of one rank stay apart, the plates layer paints above the
  figures. Run the class with `web.tests.browser.unittest_driver` and verify it passes. Re-screenshot the two-rank
  stories at 1451x790 and 1600x900.

Archive-time only (not an apply task):

- After the delta sync, retarget the `covers_requirement` IDs that still name the two removed requirements ("Foes stand
  opposite the player during combat" and "The combat participant frame presents the session's participants and their
  portraits") to "Combat figures stand in a shared-scale formation" and "Combat figures carry glance plates": find them
  with `grep -rn "foes-stand-opposite-the-player-during-combat\|the-combat-participant-frame-presents" web tests`, then
  run `uv run --locked python -m tools.spec_traceability check`. The new IDs do not exist in `openspec/specs/` before
  the sync, so the apply could not name them.
