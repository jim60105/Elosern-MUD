# Tasks: add-equipment-worn-grace-rules

Depends on P2 (merge + equipment_effects module + heal funnel) and P4
(effective-exposure contexts; recommended order).

## 1. Condition mechanism

- [ ] 1.1 Add pure `worn_item_keys_from_storage(entity)` to
      `world/rules/equipment_effects.py` (normalized-equipment read via the
      function-local import, malformed → empty frozenset, no writes).
- [ ] 1.2 Extend `world/rules/rulebook/schema.py`: generic `equipment_worn`
      branch (membership in `context["worn_item_keys"]`, missing fact →
      condition fails, non-string value → `ValueError`).
- [ ] 1.3 Inject the fact in `combat_modifiers`: both context builders and
      the `matched_combat_modifiers` partial-context `setdefault` beside
      `dual_wielding`.

## 2. Validation and data

- [ ] 2.1 Combat-rulebook load-site preflight (before matching/Script
      mirroring): string shape, `ITEM_REGISTRY` membership, `equipment_slot`
      required; plus `sexual_transitions._load_rules` guard rejecting
      `equipment_worn`.
- [ ] 2.2 Author the four 恩典 rules in `combat_modifiers.yaml`
      (`sister_vestment_grace` def +4 @ 中等, `saintess_vestment_grace`
      def +6 @ 中等, `holy_emblem_grace` heal_gain +10% @ 高度,
      `pilgrim_medallion_grace` def +2 @ 微興奮) and their four
      `status_display.yaml` label+severity entries.

## 3. Tests

- [ ] 3.1 Unit: condition match/no-match/missing-fact/malformed-storage/
      non-string raise; AND-composition with arousal and exposure
      conditions; helper purity — asserts no `entity.equipment`
      materialization and no attribute writes from
      `worn_item_keys_from_storage` and the no-create context.
- [ ] 3.2 Loader: combat preflight rejects typo key, consumable key, and
      non-string value before any matching; transition loader rejects the
      vocabulary; shipped rulebooks load clean.
- [ ] 3.3 Behavior (fixed RNG): grace fires in live resolution; no-create
      and partial-presentation contexts agree with resolution; unequipped/
      low-arousal silence; emblem grace raises a skill heal through P2's
      funnel; declared multi-accessory stack (聖女聖袍+光輝聖徽+朝聖者銅符,
      arousal 高度) merges def +8 and heal_gain +10% with all three rows
      listed.
- [ ] 3.4 Extend the Church named-key invariant test to the grace rules'
      adjustments (no negative Church values); display-coverage test green.
- [ ] 3.5 After spec sync, obtain canonical IDs via
      `uv run --locked python -m tools.spec_traceability list` and annotate
      the three covering tests (one per delta requirement, literal IDs,
      substantive assertions), keeping
      `tools.spec_traceability check` green.

## 4. Regression and handoff

- [ ] 4.1 Focused suites: `world.rules` (rulebook, combat_modifiers,
      combat heal), `commands.tests`; then the non-browser suite once with
      `--parallel 16 --noinput --keepdb`.
- [ ] 4.2 Record deviations (or none) from the parent design here; run
      `openspec validate add-equipment-worn-grace-rules --strict`.
