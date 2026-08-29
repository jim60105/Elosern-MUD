# Tasks: add-equipment-worn-grace-rules

Depends on P2 (merge + equipment_effects module + heal funnel) and P4
(effective-exposure contexts; recommended order).

## 1. Condition mechanism

- [x] 1.1 Reuse the shipped `worn_item_keys(entity)` accessor in
      `world/rules/equipment_effects.py` as the fact source (pure stored
      read via the function-local import, malformed → empty frozenset, no
      writes). Deviation from the design's working name
      `worn_item_keys_from_storage`: P2 already shipped the identical
      contract under `worn_item_keys`, so no new function is added
      (recorded in 4.2).
- [x] 1.2 Extend `world/rules/rulebook/schema.py`: generic `equipment_worn`
      branch (membership in `context["worn_item_keys"]`, missing fact →
      condition fails, non-string value → `ValueError`).
- [x] 1.3 Inject the fact in `combat_modifiers`: both context builders and
      the `matched_combat_modifiers` partial-context `setdefault` beside
      `dual_wielding`.

## 2. Validation and data

- [x] 2.1 Combat-rulebook load-site preflight (before matching/Script
      mirroring): string shape, `ITEM_REGISTRY` membership, `equipment_slot`
      required; plus `sexual_transitions._load_rules` guard rejecting
      `equipment_worn`.
- [x] 2.2 Author the four 恩典 rules in `combat_modifiers.yaml`
      (`sister_vestment_grace` def +4 @ 中等, `saintess_vestment_grace`
      def +6 @ 中等, `holy_emblem_grace` heal_gain +10% @ 高度,
      `pilgrim_medallion_grace` def +2 @ 微興奮) and their four
      `status_display.yaml` label+severity entries.

## 3. Tests

- [x] 3.1 Unit: condition match/no-match/missing-fact/malformed-storage/
      non-string raise; AND-composition with arousal and exposure
      conditions; helper purity — asserts no `entity.equipment`
      materialization and no attribute writes from
      `worn_item_keys_from_storage` and the no-create context.
- [x] 3.2 Loader: combat preflight rejects typo key, consumable key, and
      non-string value before any matching; transition loader rejects the
      vocabulary; shipped rulebooks load clean.
- [x] 3.3 Behavior (fixed RNG): grace fires in live resolution; no-create
      and partial-presentation contexts agree with resolution; unequipped/
      low-arousal silence; emblem grace raises a skill heal through P2's
      funnel; declared multi-accessory stack (聖女聖袍+光輝聖徽+朝聖者銅符,
      arousal 高度) merges def +8 and heal_gain +10% with all three rows
      listed.
- [x] 3.4 Extend the Church named-key invariant test to the grace rules'
      adjustments (no negative Church values); display-coverage test green.
- [x] 3.5 After spec sync, obtain canonical IDs via
      `uv run --locked python -m tools.spec_traceability list` and annotate
      the three covering tests (one per delta requirement, literal IDs,
      substantive assertions), keeping
      `tools.spec_traceability check` green.

## 4. Regression and handoff

- [x] 4.1 Focused suites: `world.rules` (rulebook, combat_modifiers,
      combat heal), `commands.tests`; then the non-browser suite once with
      `--parallel 16 --noinput --keepdb`.
- [x] 4.2 Record deviations (or none) from the parent design here; run
      `openspec validate add-equipment-worn-grace-rules --strict`.

Deviations recorded (design.md D1/D2 updated to match):

- The working-name helper `worn_item_keys_from_storage` was dropped: P2
  already shipped the identical contract under `worn_item_keys`, which this
  change reuses as the single pure stored-equipment fact read.
- Plan review (Rubber Duck run 1) folded the malformed-context edge into
  the evaluator's fail-closed normalization: a `worn_item_keys` context
  fact that is not a set/frozenset contributes no keys instead of raising
  or substring-matching; non-string *condition values* still raise.
- Post-implementation review (Rubber Duck run 2) found `equipment_worn:
  null` bypassed the combat preflight (`rule.when.get(...)` treated the
  declared null as an absent condition). Fixed: preflight keys off
  `"equipment_worn" not in rule.when` and rejects any non-string value,
  with a regression test. No spec change required — the delta already
  mandated rejecting non-string values at load.

Verification: focused 209 tests + full non-browser suite 5079 OK (fresh
DB, `--parallel 16 --noinput`), display-coverage and
rule↔test-correspondence gates green, `tools.spec_traceability check`
1104/1104 (0 uncovered), `openspec validate --strict` passed.
