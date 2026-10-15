# Tasks

The scope is a pure module plus its tests. Follow the focused Vitest rule of root `AGENTS.md` "Testing".

## 1. Engine (≈3 h)

- [x] 1.1 Create `web/webclient-app/components/combat-formation.js` (design D1, D2, D5): the constants, the zone
  computation, the one-rank and two-rank layout, the plate-slot lines, the marker slots, and the scale policy. Add a
  header comment that states the invariants and points to this change's design.
- [x] 1.2 Add a `tokens.css`-free input adapter `formationInputFromStage(stageRect, styles, vitalsRect, counts)` that the
  next change will call; it converts computed `--ui-scale`, `--actor-h` and the band/top-band edges into the input
  object, and is the only place that reads CSS values.

## 2. Tests (≈2.5 h)

- [x] 2.1 Add `web/webclient-app/tests/core/combat_formation.test.js`:
  - every invariant of design D3 over the full matrix at the four viewports, with the reference vitals dock;
  - the policy (all-full preferred before compact; two ranks only when one does not fit);
  - the shared height of every box;
  - the spec's normative anchors, and a snapshot of the full table for 1451x790 and 1600x900 (design D4) that any
    later change updates deliberately;
  - the `fits: false` fallback for a stage smaller than the reference;
  - a determinism case (same input → same output);
  - a guard that the module imports nothing from Vue or the DOM.

  Run `pnpm test -- web/webclient-app/tests/core/combat_formation.test.js` and verify it passes.

## 3. Gates (≈0.5 h)

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`
  and `openspec validate webclient-combat-formation-engine --strict`. Verify all pass.
