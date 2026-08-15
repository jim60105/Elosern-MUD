## Why

The combat-modifier rule table (`world/rules/rulebook/combat_modifiers.yaml`) declares four adjustment
fields whose production code has no sink: `defense` and `atk_phys` (flat bonuses from
`defense_instinct`, `guardian_instinct`, `retainer_martial_training`, `dual_wield_style`) never enter
the damage formula, and `mp_cost`/`sp_cost` (percentage reductions from `precise_mana_control`,
`extreme_endurance`) never adjust the resource check or deduction. `combat-modifier-table`'s main spec
(lines 107-117) explicitly defers consumption of these four keys to "later changes" — this change is
that later change. The remaining keys (`agility`, `accuracy`, `actions_per_turn`) already have live
sinks; this change completes the contract so every declared field in the table is consumed
deterministically.

## What Changes

- Apply the flat `atk_phys` bundle value to the attacker's physical attack stat inside the damage
  magnitude computation (`world/rules/combat.py` `_handle_damage`), and the flat `defense` bundle
  value to the defender's defense stat; both enter the formula at exactly the point the effective
  stat is read, before multiplier/rounding for attack and as part of the subtracted defense term.
- Extract shared pure stat helpers in `world/rules/combat.py` so the overwhelm expected-damage
  estimator (`world/rules/overwhelm.py` `_expected_damage_per_attack`) and the monster
  highest-expected-damage skill choice (`world/rules/monster_behaviour.py` `_choose_skill`) mirror
  the live damage math instead of reading raw stats.
- Apply the percentage `mp_cost`/`sp_cost` bundle values to BOTH the resource check and the resource
  deduction in `world/rules/action.py` (`_step2_resource_check`, `_step6_resource_deduction`) and to
  the mirrored check in `world/rules/action_preview.py` `_skill_wide_failure`, via one shared pure
  cost-adjustment helper in `world/rules/combat_modifiers.py`. Rounding is floor; the adjusted cost
  is clamped at zero. The staged `resource_spend` description carries the adjusted amount so event
  logs and the `trait_delta` entry report the real deduction.
- Adjust inline YAML comments in `world/rules/rulebook/combat_modifiers.yaml` where the claimed
  magnitude now has a live effect (no numeric recalibration is needed; the seed values remain small
  flat/percentage adjustments consistent with the skills' flavor).
- Tests: damage with/without `defense`/`atk_phys` rules (including magic-school attacks, which the
  `atk_phys` bonus must not touch), resource cost with/without reductions including the zero clamp
  and fractional-grant percentages, preview/preflight/resolve parity for adjusted costs, and a check
  that the status panel presentation is unchanged.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `combat-modifier-table`: amends the "eight previously-dead passive_buff/combat_prediction skills"
  requirement so the `defense`, `atk_phys`, `mp_cost`, `sp_cost` vocabulary keys are no longer
  "owned by later changes" but are consumed by the deterministic combat/resource math; adds explicit
  sink requirements for the flat damage adjustments and the percentage cost adjustments, including
  rounding/clamping semantics and preview/preflight parity.

## Impact

- `world/rules/combat.py` — damage magnitude uses adjusted attack/defense; new shared stat helpers
  consumed by overwhelm and monster behaviour estimators.
- `world/rules/action.py` — `_step2_resource_check` and `_step6_resource_deduction` use adjusted
  costs (staged amount and recheck both adjusted).
- `world/rules/action_preview.py` — resource check uses the same adjusted cost from the no-create
  bundle so preview, preflight, and resolve agree.
- `world/rules/combat_modifiers.py` — new pure `apply_cost_modifier` helper (floor rounding, zero
  clamp) owning the cost vocabulary; no change to bundle evaluation or merge semantics.
- `world/rules/overwhelm.py`, `world/rules/monster_behaviour.py` — expected-damage surfaces consume
  the shared adjusted stat helpers.
- `world/rules/rulebook/combat_modifiers.yaml` — comment-only updates.
- Deterministic integer discipline: adjusted costs are integers (floor of the percentage-scaled
  amount); no floats enter stored state.
