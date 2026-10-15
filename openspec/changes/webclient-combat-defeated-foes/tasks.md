# Tasks

Prerequisites: `webclient-combat-formation` and `webclient-combat-figure-plates` are archived.

Rules:

- Follow root `AGENTS.md` "Testing": focused commands only, browser output captured to a scratch file.
- **Styling pitfall** (`web/webclient-app/AGENTS.md`): grep `styles/app-shell.css` for `.elosern-root .stage-actor`
  rules.

## 1. Treatments (≈2.5 h)

- [ ] 1.1 `components/StageActor.vue`: the `fallen` prop, the `.stage-actor__fall` wrapper, the two treatments, the
  seal SVG and the transitions with reduced/off/hydration (design D1–D4). Add the pose tokens to `styles/tokens.css`.
- [ ] 1.2 `components/foe-lineup.js` and `components/FoeLineup.vue`: drawn set = non-fled foes (design D5) and pass
  `fallen`. `components/CompanionLineup.vue`: `fallen="down"` for knocked-out companions. `components/FigurePlate.vue`:
  the fallen readout and accessible name. `lib/beat_queue.js`: a defeat beat marks the foe fallen instead of removing
  it.
- [ ] 1.3 Tests:
  - `tests/components/stage_actor*.test.js` (or `tests/app_client_stage_actor.test.js`): `data-fallen`, the seal
    present only when defeated, `aria-hidden` on the seal, no transition at off, and the transformed box inside
    the untransformed slot;
  - `tests/core/foe_lineup.test.js`: knocked-out and defeated foes stay and fled ones leave;
  - `tests/core/figure_plate.test.js`: 已擊破/倒地;
  - `tests/beat_queue.test.js` and `tests/beat_choreography.test.js`: the defeat beat keeps the foe.

  Run those files with `pnpm test -- …` and verify they pass.

## 2. Browser verification (≈1.5 h)

Build once: `pnpm run build`.

- [ ] 2.1 Add `test_fallen_figures_keep_their_slot_and_read_as_fallen` to `web/tests/browser/test_browser_combat_stage.py`
  `CombatStageBrowserTest`. With three foes, one defeated by a playing round at `full`, and a knocked-out companion:
  - the defeated foe keeps its box (±1px, before transform), carries `data-fallen="defeated"`, the seal and 已擊破;
  - the companion carries `data-fallen="down"` and 倒地;
  - the formation scale is unchanged;
  - at `reduced` the computed transition on the fall wrapper has no transform duration.

  Register it in `.github/browser-shards.json`. Update `CombatBeatsBrowserTest` methods that asserted the defeated foe
  leaves (find them with `grep -n "defeat" web/tests/browser/test_browser_combat_beats.py`); each now asserts the
  defeated look. Run the new method and each updated method by full label, and verify they pass.

## 3. Storybook (≈1 h)

- [ ] 3.1 `Core/StageActor`: `DefeatedPortrait`, `DefeatedPlaceholder`, `DefeatedFailedArt`, `DownedAlly`,
  `FallenVsDim` (a dialogue listener, a defeated foe and a downed ally side by side) and
  `DefeatedReducedMotion`. `Core/AppShell`: `CombatSomeFoesDefeated` (six foes, two defeated, one downed companion).
  Run `pnpm run build-storybook` then `pnpm run showcase-coverage` and verify both succeed.

## 4. Gates (≈0.5 h)

- [ ] 4.1 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`,
  the Evennia focused labels `tests.test_evennia_test_optimization_contract` and `tests.test_webclient_frozen_contract`,
  and `openspec validate webclient-combat-defeated-foes --strict`. Verify all pass.
