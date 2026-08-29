# Tasks: wire-equipment-combat-modifiers

Depends on `add-equipment-effect-rulebook` (rulebook + roster must be
synced/merged first; the parent design §6 gauge-sync amendment ships in this
change's commit).

## 1. Bundle accessor and merge

- [x] 1.1 Implement `equipment_adjustments(entity)` in
      `world/rules/equipment_effects.py`: function-local import of
      `normalized_equipment` (module-level deps stay lore/rulebook-only),
      per-worn combat-field fold (flat/percent kinds), malformed storage →
      empty bundle, no writes; frozen-bundle return.
- [x] 1.2 Merge the equipment bundle after rule-table matching in
      `evaluate_combat_modifiers()` and
      `evaluate_combat_modifiers_no_create()` (both via `_merge_adjustments`).
- [x] 1.3 Add `combat_modifiers.adjusted_agility(entity, modifiers=None)`
      with the ≥ 0 floor; route `combat._to_hit`, `overwhelm` estimation,
      `sexual_resist` scoring, and `disengage`'s flee contest through it;
      leave `combat.roll_initiative` raw (documented exception).

## 2. Gauge ceiling sync and heal scaling

- [x] 2.1 Implement the recompute-from-scratch gauge-limit sync in
      `world/rules/equipment.py` (`mod = Σ worn gauge_caps` per gauge, base
      untouched, absent gauge traits skipped, function-local import of the
      rulebook accessor; settle `current` down to any lowered ceiling) and
      call it inside `toggle_equipment`'s transaction; snapshot/restore
      trait storage alongside the equipment attribute snapshot.
- [x] 2.2 Apply the normative heal formula in `combat._heal_magnitude()`
      (`max(floor(base_amount × (1 + pct/100)), heal.floor)` over the
      unchanged unamplified base); leave item-use heal amounts unscaled.
- [x] 2.3 Regression-verify gauge maxima reporting (`(base + mod)` in the
      strict status read model and panel surfaces) renders effective
      maxima after sync — presentation code is expected to need no changes;
      change it only if a test proves otherwise.

## 3. Tests

- [x] 3.1 Unit: bundle stacking (multi-item additive), malformed → empty,
      accessor purity (no state writes), no parallel equipment formula
      (structural test per the equipment-effects delta scenario).
- [x] 3.2 Behavior (fixed RNG): to-hit/damage with worn gear through live
      resolution; preview/resolve cost agreement with `mp_cost`/`sp_cost`
      gear; resist-score pickup; overwhelm-estimator agreement with live
      math; agility floor equality (to-hit and flee-contest scenarios);
      `heal_gain` floored scaling (base 3 × +20% → 3) and unscaled potion
      heal; golden fixed-seed tests stay green.
- [x] 3.3 Behavior (EvenniaTest): equip/unequip gauge sync — raised headroom
      with heal past the old max, unequip settling excess current to the
      lowered ceiling (status read model renders, no error), repeated-toggle
      no-accumulation, full-restore-to-effective-max, transaction-failure
      restoration of traits + equipment; effective-maxima reporting.
- [x] 3.4 Annotate new tests with `covers_requirement` for the four delta
      requirements once synced (main-spec indexing ordering per AGENTS.md);
      run `tools.spec_traceability check`.

## 4. Regression and handoff

- [x] 4.1 Focused suites: `world.rules` (combat, modifiers, overwhelm,
      resist, preview), `commands`, `web.webclient` panels; then the
      non-browser suite once with `--parallel 16 --noinput --keepdb`.
- [x] 4.2 Confirm the P1 inertness import-allowlist test still passes (this
      change is the authorized consumer expansion); record any deviation
      from the parent design here (the §6 gauge amendment is already applied
      in the parent doc); run `openspec validate
      wire-equipment-combat-modifiers --strict`.

      Deviations recorded:
      (a) inertness allowlist expanded with `combat_modifiers.py` and
      `equipment.py`; the dormant heal-dormancy inertness test was deleted
      because heal scaling is now live (its contract moved to
      `test_equipment_combat_wiring.py`).
      (b) `effective_power` stays raw — no equipment-aware power accessor
      (rubber-duck rejection; equipment folds at each consumer instead).
      (c) `test_overwhelm_threshold.py` fixture pins defender agility to
      1000 so the harness's own bundle reads stay neutral.
      (d) two delta requirements (dual-component agility, heal scaling)
      were amended into the change specs and synced into `openspec/specs/`
      as part of this change.
      (e) rubber-duck run 2: no blocking findings; its one non-blocking
      finding (per-entity serialization of the gauge read-modify-write
      against a concurrent toggle) is deferred — the single-player runtime
      serializes command execution per entity today, P2 adds no new
      concurrent writer, and pre-toggle equipment paths were equally
      unlocked. Revisit if concurrent entity writers ever land.
