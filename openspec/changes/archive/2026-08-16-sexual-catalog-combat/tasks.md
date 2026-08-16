## 1. Confirm the dependency surface this change reads

- [x] 1.1 Confirm `sexual-act-seeds` has landed with `COMBAT_ACTS` containing exactly
  `combat_tease`, `TargetSpec.SINGLE`, `actor_counters=("hostile_act_count",)`,
  `participant_counters=()`.
- [x] 1.2 Confirm `world/rules/sexual_state.py`'s `hostile_act_count`/`climax_count`/
  `climax_extension_count` and their sole mutators (`record_hostile_act`, `record_climax_count`,
  `record_climax_extension`) are unchanged, and that `climax_count`/`climax_extension_count` are
  each credited only by the climax-settlement clock, never by an act's own `actor_counters`.
- [x] 1.3 Confirm `world/rules/rulebook/combat_modifiers.yaml`'s `high_arousal_agility_accuracy_
  penalty` row (`{field: arousal, gte: 高度}` → `{agility: "-20%", accuracy: -15}`) is unchanged —
  design.md's Impact/Risks claim for `combat_charm`/`combat_bind_caress` depends on it firing
  exactly as described.
- [x] 1.4 Confirm `world/rules/rulebook/sexual_act_effects.yaml`'s `climax_extension_threshold: 20`
  and `participant_multipliers` ladder (`{"1": 1.0, "2": 1.1, "3+": 1.2}`) are unchanged — design.md
  D-4's worst-case arithmetic for the three `base_pleasure=30` acts depends on both.
- [x] 1.5 Confirm `world/rules/rulebook/sexual_pleasure.yaml`'s `sensitivity_multipliers` floor
  (`普通: 1.0`) and `shame_multipliers`' lowest non-`成癮` value (`強烈: 0.65`) are unchanged — D-4's
  worst-case claim uses both as the floor inputs.

## 2. `world/skills/sexual_acts/combat.py`: Tier 1 (two acts)

- [x] 2.1 Extend `COMBAT_ACTS`'s `_act_family("戰鬥", ...)` call with the two Tier 1 rows from
  design.md D-1 (`combat_tease_whisper`, `combat_tease_touch`), each `unlock={"hostile_act_count":
  5}`, `target_spec=TargetSpec.SINGLE`, `actor_pleasure_ratio=0.4`,
  `actor_counters=("hostile_act_count",)`, `participant_counters=()`, `sexual_events=()`,
  `resistible=True`, with `actor_part == target_part` per the table.

## 3. `world/skills/sexual_acts/combat.py`: Tier 2 (three acts)

- [x] 3.1 Add `combat_charm` (`unlock={"hostile_act_count": 20}`, `target_part="頸項"`,
  `base_pleasure=20`, otherwise matching Tier 1's shape).
- [x] 3.2 Add `combat_bind_caress` (same unlock, `target_part="大腿"`, `base_pleasure=20`).
- [x] 3.3 Add `combat_forced_pleasure` (same unlock, `target_part="私處"`, `base_pleasure=24`).

## 4. `world/skills/sexual_acts/combat.py`: Tier 3 (two acts)

- [x] 4.1 Add `combat_forced_climax` (`unlock={"hostile_act_count": 40, "climax_count": 30}`,
  `target_part="私處"`, `base_pleasure=30`, `actor_pleasure_ratio=0.4`, otherwise matching Tier 2's
  shape).
- [x] 4.2 Add `combat_relentless_torment` (same unlock, `target_part="臀部"`, `base_pleasure=30`,
  `actor_pleasure_ratio=0.6`).

## 5. `world/skills/sexual_acts/combat.py`: Tier 5 (one AREA act)

Tier 4 (搾取) is deliberately NOT built by this change: no cross-entity resource-transfer effect
exists in the schema (design.md D-2). This is a resolved deferral, not an open task.

- [x] 5.1 Add `combat_climax_domination` (`unlock={"hostile_act_count": 80,
  "climax_extension_count": 30}`, `target_spec=TargetSpec.AREA`, `actor_part="私處"`,
  `target_part="私處"`, `base_pleasure=30`, `actor_pleasure_ratio=0.4`,
  `actor_counters=("hostile_act_count",)`, `participant_counters=()`, `sexual_events=()`,
  `resistible=True`).

## 6. Behaviour tests for the delta spec

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and note the canonical
  requirement IDs for `sexual-catalog-combat::*` from this change's delta spec.
- [x] 6.2 Add `world/skills/sexual_acts/tests/test_combat_catalog.py` (new `EvenniaTest`-based
  module) covering each delta-spec scenario: a Tier 1 act absent below threshold and present at it;
  `combat_forced_climax`'s compound gate; `combat_climax_domination`'s compound gate; every act
  crediting `hostile_act_count` on the actor only, never the target; `compute_pleasure_gain`'s
  worst-case (`普通` sensitivity, `強烈` shame, `participant_count == 2`) evaluation for
  `combat_forced_climax` clearing `climax_extension_threshold`; the actor-side comparison between
  `combat_forced_climax` and `combat_relentless_torment` at matched inputs; `combat_climax_
  domination` declaring `TargetSpec.AREA` while every other act declares `TargetSpec.SINGLE`; every
  act declaring `sexual_events == ()`.
- [x] 6.3 Apply `covers_requirement("sexual-catalog-combat::<id>")` (using the IDs from 6.1) to each
  test function whose assertions establish that requirement.
- [x] 6.4 Run `uv run --locked python -m tools.spec_traceability check` and confirm every
  `sexual-catalog-combat` requirement is covered.

## 7. Full verification

- [x] 7.1 Run `uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests
  world.rules.tests` and confirm the whole package suite passes, including
  `test_registry_structure.py` and `test_acceptance.py` against the now-nine-row `COMBAT_ACTS`
  tuple.
- [x] 7.2 Run `uv run --locked python -m compileall -q world`.
- [x] 7.3 Run `openspec validate sexual-catalog-combat --strict` and resolve any reported issue.
- [x] 7.4 Confirm no file outside `world/skills/sexual_acts/combat.py`, the new
  `world/skills/sexual_acts/tests/test_combat_catalog.py`, the pinned SEXUAL_ACT key set in
  `world/skills/tests/test_registry.py` (the one content-specific collateral, per the shared
  handoff), and this change's own artifacts was touched — in particular, confirm
  `world/rules/action.py` and `world/rules/rulebook/combat_modifiers.yaml` both have zero diff
  from this change.
