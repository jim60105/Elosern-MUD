## Why

Eight registered skills (`defense_instinct`, `blade_art_mastery`, `extreme_endurance`,
`magic_circle_comprehension`, `precise_mana_control`, `retainer_martial_training`, `guardian_instinct`,
`reincarnation_boon_yuka`) declare `passive_buff:*` or `combat_prediction:*` effects with no consumer
anywhere — owning them does nothing. `world/rules/rulebook/combat_modifiers.yaml` already evaluates
buff-origin and sexual-field-origin rows through one condition engine with no source-branching
(`buff-handler-integration` spec). Per the approved skill-system redesign (design doc D2, §3.2), the
cheapest, most-consistent fix is to give that engine a `skill_owned` condition primitive rather than
hand-writing eight bespoke Python consumers.

## What Changes

- Add a `skill_owned` condition primitive to `world/rules/rulebook/schema.py`'s `evaluate_condition()`
  vocabulary: `{"skill_owned": "<skill_key>"}`, true when `skill_key in entity.skills.owned_keys()`.
- Add one row per affected skill to `world/rules/rulebook/combat_modifiers.yaml`, translating each
  skill's flavor name into a concrete adjustment (e.g. `defense_instinct` → small flat `defense`
  bonus; `reincarnation_boon_yuka`'s `combat_prediction:武感` → an initiative/evasion bonus).
- No change to `evaluate_combat_modifiers()`'s merge behavior — new rows merge via the exact mechanism
  already proven for buff-origin and sexual-origin rows.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `combat-modifier-table`: gains the `skill_owned` condition primitive and eight new seed rows keyed
  off it; the existing "no special-case branch between buff-origin and sexual-origin rows" requirement
  extends to cover ownership-origin rows under the same non-branching guarantee.

## Impact

- `world/rules/rulebook/schema.py` (new condition type), `world/rules/rulebook/combat_modifiers.yaml`
  (new data rows), `world/rules/combat_modifiers.py` (context-building must expose
  `entity.skills.owned_keys()` to the condition evaluator).
- Depends on `skill-effects-typed-model` (uses `RuleTableEffect`'s typed representation to identify
  which skills this applies to, though the rule rows themselves are keyed by skill key string, not by
  the typed effect object).
- Blocks `weapon-style-stance-split` and `conferral-generalization`, both of which build on this
  change's `skill_owned` primitive.
