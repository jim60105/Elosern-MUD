# Tasks: wire-equipment-combat-modifiers

Depends on `add-equipment-effect-rulebook` (rulebook + roster must be
synced/merged first; the parent design §6 gauge-sync amendment ships in this
change's commit).

## 1. Bundle accessor and merge

- [ ] 1.1 Implement `equipment_adjustments(entity)` in
      `world/rules/equipment_effects.py`: function-local import of
      `normalized_equipment` (module-level deps stay lore/rulebook-only),
      per-worn combat-field fold (flat/percent kinds), malformed storage →
      empty bundle, no writes; frozen-bundle return.
- [ ] 1.2 Merge the equipment bundle after rule-table matching in
      `evaluate_combat_modifiers()` and
      `evaluate_combat_modifiers_no_create()` (both via `_merge_adjustments`).
- [ ] 1.3 Add `combat_modifiers.adjusted_agility(entity, modifiers=None)`
      with the ≥ 0 floor; route `combat._to_hit`, `overwhelm` estimation,
      `sexual_resist` scoring, and `disengage`'s flee contest through it;
      leave `combat.roll_initiative` raw (documented exception).

## 2. Gauge ceiling sync and heal scaling

- [ ] 2.1 Implement the recompute-from-scratch gauge-limit sync in
      `world/rules/equipment.py` (`mod = Σ worn gauge_caps` per gauge, base
      untouched, absent gauge traits skipped, function-local import of the
      rulebook accessor; settle `current` down to any lowered ceiling) and
      call it inside `toggle_equipment`'s transaction; snapshot/restore
      trait storage alongside the equipment attribute snapshot.
- [ ] 2.2 Apply the normative heal formula in `combat._heal_magnitude()`
      (`max(floor(base_amount × (1 + pct/100)), heal.floor)` over the
      unchanged unamplified base); leave item-use heal amounts unscaled.
- [ ] 2.3 Regression-verify gauge maxima reporting (`(base + mod)` in the
      strict status read model and panel surfaces) renders effective
      maxima after sync — presentation code is expected to need no changes;
      change it only if a test proves otherwise.

## 3. Tests

- [ ] 3.1 Unit: bundle stacking (multi-item additive), malformed → empty,
      accessor purity (no state writes), no parallel equipment formula
      (structural test per the equipment-effects delta scenario).
- [ ] 3.2 Behavior (fixed RNG): to-hit/damage with worn gear through live
      resolution; preview/resolve cost agreement with `mp_cost`/`sp_cost`
      gear; resist-score pickup; overwhelm-estimator agreement with live
      math; agility floor equality (to-hit and flee-contest scenarios);
      `heal_gain` floored scaling (base 3 × +20% → 3) and unscaled potion
      heal; golden fixed-seed tests stay green.
- [ ] 3.3 Behavior (EvenniaTest): equip/unequip gauge sync — raised headroom
      with heal past the old max, unequip settling excess current to the
      lowered ceiling (status read model renders, no error), repeated-toggle
      no-accumulation, full-restore-to-effective-max, transaction-failure
      restoration of traits + equipment; effective-maxima reporting.
- [ ] 3.4 Annotate new tests with `covers_requirement` for the four delta
      requirements once synced (main-spec indexing ordering per AGENTS.md);
      run `tools.spec_traceability check`.

## 4. Regression and handoff

- [ ] 4.1 Focused suites: `world.rules` (combat, modifiers, overwhelm,
      resist, preview), `commands`, `web.webclient` panels; then the
      non-browser suite once with `--parallel 16 --noinput --keepdb`.
- [ ] 4.2 Confirm the P1 inertness import-allowlist test still passes (this
      change is the authorized consumer expansion); record any deviation
      from the parent design here (the §6 gauge amendment is already applied
      in the parent doc); run `openspec validate
      wire-equipment-combat-modifiers --strict`.
