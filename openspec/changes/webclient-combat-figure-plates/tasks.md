# Tasks

Prerequisites: `webclient-combat-panel-v6` and `webclient-combat-formation` are archived.

Rules:

- Follow root `AGENTS.md` "Testing": focused commands only, browser output captured to a scratch file.
- **Styling pitfall** (`web/webclient-app/AGENTS.md`): grep `styles/app-shell.css` for `.elosern-root` rules on
  `condition-chip`, `figure-plate` and `vitals` classes, and keep the plate's glyph styling in the component.

## 1. Glyphs, alarm and tooltip (≈2.5 h)

- [ ] 1.1 `components/ConditionChips.vue`: add the `cap` and `tabbable` props (design D2). Keep every existing vitals
  dock behaviour (its tests guard it).
- [ ] 1.2 `components/FigurePlate.vue`: the glyph row per form, the severity order for compact plates, the low-HP alarm
  (design D5), and the conditions in the accessible name. `AppClient.vue`: pass the participant `conditions` and the
  `plateTooltipClose` counter (design D3).
- [ ] 1.3 Tests:
  - `tests/core/figure_plate.test.js`: glyph counts per form, `+N`, the compact severity order, the 危險 tag at
    exactly 25% and its absence at 26%, and the accessible name with conditions;
  - `tests/core/condition_chips.test.js` (or the existing ConditionChips test file): the default cap unchanged, and
    `tabbable=false` puts no glyph in the tab order.

  Run `pnpm test` on those files plus `web/webclient-app/tests/core/vitals*.test.js` (the existing vitals guards) and
  verify they pass.

## 2. Keyboard group (≈1.5 h)

- [ ] 2.1 Create `components/plate-group.js` and wire the group in `components/HudFrame.vue`'s plates layer
  (design D4).
- [ ] 2.2 Add `tests/core/plate_group.test.js`: one tab stop; Left/Right order equals the formation's stage order;
  Up/Down glyph moves; Escape focuses `#action-dock`; handled keys do not reach a spy on `store.focusPress`. Run it and
  verify it passes.

## 3. Browser verification (≈1.5 h)

Build once: `pnpm run build`.

- [ ] 3.1 Add `test_figure_plates_show_conditions_and_alarm` to `web/tests/browser/test_browser_combat_stage.py`
  `CombatStageBrowserTest`. With a poisoned foe and a companion at 20% HP at 1451x790:
  - the glyphs show, and hovering opens the tooltip, which closes on Escape and when a round starts playing;
  - the companion's readout carries 危險;
  - Tab from `#action-dock` reaches the plates group once, ArrowRight moves to the next plate, and Escape returns to
    `#action-dock`.

  Register it in `.github/browser-shards.json` beside the other `CombatStageBrowserTest` methods, run it through
  `web.tests.browser.unittest_driver`, and verify it passes.

## 4. Storybook (≈1 h)

- [ ] 4.1 `Core/FigurePlate`: the `FullHp`, `Damaged`, `LowHpAlarm`, `WithConditions`, `ConditionOverflow`,
  `LongName`, `Compact`, `CompactWithConditions` and `PlaybackDrain` stories (an animated `displayHp` sequence).
  `Core/AppShell`: `CombatConditionsSoloFifteenFoes` and `CombatConditionsFullParty`. Run `pnpm run build-storybook`
  then `pnpm run showcase-coverage` and verify both succeed.

## 5. Gates (≈0.5 h)

- [ ] 5.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`,
  the Evennia focused labels `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract`,
  and `openspec validate webclient-combat-figure-plates --strict`. Verify all pass.
