# Tasks

Prerequisites: `webclient-combat-panel-v6` and `webclient-combat-formation` are archived.

Rules:

- Follow root `AGENTS.md` "Testing": focused commands only (`pnpm exec vitest run <file> …`, never a bare
  `pnpm test`), browser output captured to a scratch file.
- **Styling pitfall** (`web/webclient-app/AGENTS.md`): grep `styles/app-shell.css` for `.elosern-root` rules on
  `condition`, `chip`, `figure-plate` and `vitals` classes, and keep the plate's glyph styling in the components.

## 1. Glyphs, alarm and tooltip (≈2.5 h)

- [ ] 1.1 `components/ConditionChips.vue`: add the `cap`, `tabbable`, `variant`, `fold` and `closeSignal` props and
  the measured tooltip placement (design D2, D3); `lib/condition_label.js`: a missing `provenance` is no source. Keep
  every existing vitals dock behaviour (its tests guard it).
- [ ] 1.2 `components/FigurePlate.vue` / `figure-plate.js`: the glyph row and its box budget per form, the severity order, the
  low-HP alarm on the glyph line (design D5), the fold, and the conditions and 危險 in the accessible name.
  `AppClient.vue`: pass the participant `conditions`, the `plateTooltipClose` counter (design D3) and each plate's
  stage x.
- [ ] 1.3 Tests (run with `pnpm exec vitest run` on exactly these files):
  - `tests/core/figure_plate.test.js`: glyph counts per form, `+N` and its tooltip list, the severity order,
    the fold, the 危險 tag at exactly 25% and its absence at 26% (both forms), the accessible name with conditions,
    and the close signal;
  - `tests/data/condition_chips.test.js`: the default cap unchanged, `tabbable=false` puts no icon in the tab order,
    the plate variant's hooks and `+N` tooltip, and the tooltip's viewport clamp and flip;
  - the existing vitals guards `tests/data/vitals.test.js`, `tests/data/vitals_track.test.js` and
    `tests/data/vitals_visibility.test.js`.

## 2. Keyboard group (≈1.5 h)

- [ ] 2.1 Create `components/plate-group.js` and wire the group on `components/HudFrame.vue`'s plates anchor, moved
  after the band in DOM order (design D4).
- [ ] 2.2 Add `tests/core/plate_group.test.js`: one tab stop; Left/Right order equals the stage order (left to
  right); Up/Down glyph moves; focus memory; Escape focuses `#action-dock` once no tooltip is open; handled keys do not
  reach a spy on `store.focusPress`. Update `tests/hud_frame.test.js` for the group and the anchor order. Run both
  files and verify they pass.

## 3. Browser verification (≈1.5 h)

Build once: `pnpm run build`.

- [ ] 3.1 Add `test_figure_plates_show_conditions_and_alarm` to `web/tests/browser/test_browser_combat_stage.py`
  `CombatStageBrowserTest`. With a poisoned foe and a companion at 20% HP at 1451x790:
  - the glyphs show inside their plates and no tooltip is open at rest; hovering opens the tooltip, which closes on
    Escape and when a round starts playing;
  - the companion's plate carries 危險 and its current value the critical hue;
  - Tab from `#action-dock` reaches the plates group once, ArrowRight moves to the next plate, and Escape returns to
    `#action-dock`.

  Update the existing plates-layer focus assertions in `test_browser_combat_stage.py` and
  `test_browser_contextual_hud_combat.py` (the layer is now one tab stop). Register the new method in
  `.github/browser-shards.json` beside the other `CombatStageBrowserTest` methods, run it and the touched methods
  through `web.tests.browser.unittest_driver`, and verify they pass.

## 4. Storybook (≈1 h)

- [ ] 4.1 `Core/FigurePlate`: the `FullHp`, `Damaged`, `LowHpAlarm`, `WithConditions`, `ConditionOverflow`,
  `LongName`, `Compact`, `CompactWithConditions`, `CompactLowHpFold` and `PlaybackDrain` stories (an animated
  `displayHp` sequence). `Core/AppShell`: `CombatConditionsSoloFifteenFoes` and `CombatConditionsFullParty`. Review
  them with `agent-browser` at 1451x790 and 1600x900 (glyphs, tooltips, danger tags, plates). Run
  `pnpm run build-storybook` then `pnpm run showcase-coverage` and verify both succeed.

## 5. Gates (≈0.5 h)

- [ ] 5.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`,
  the Evennia focused labels `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract`,
  and `openspec validate webclient-combat-figure-plates --strict`. Verify all pass.
