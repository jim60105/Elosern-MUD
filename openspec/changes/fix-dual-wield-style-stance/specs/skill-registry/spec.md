## ADDED Requirements

### Requirement: dual_wield_style is a PASSIVE stance, not a castable ACTIVE skill

`dual_wield_style` SHALL declare `kind=SkillKind.PASSIVE`, `target_spec=TargetSpec.NONE`, and an
empty `cost` (reclassified from the previous `SkillKind.ACTIVE` with `TargetSpec.SELF` and
`cost={"sp": 8}`, which had no working cast path — `weapon_style` is not registered in
`action.py`'s `_EFFECT_HANDLERS`, so an in-combat cast attempt unconditionally rejected
`UNKNOWN_EFFECT_ID` at effect resolution (out-of-combat attempts rejected earlier as
`SKILL_NOT_USABLE_OUT_OF_COMBAT`)). `effects=["weapon_style:dual_wield"]` SHALL NOT change: the
typed `WeaponStyleEffect` remains the declared stance representation, and the combat adjustment
defined by the `combat-modifier-table` capability (`dual_wield_style_atk_phys_bonus`) continues to
resolve from ownership via the `skill_owned` + `dual_wielding` rule row.

This requirement explicitly amends the sibling requirement
`dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style` (whose text says the
mastery skill "SHALL NOT replace or modify `dual_wield_style`"): the reclassification changes
`kind`/`target_spec`/`cost` only, never the skill's existence, its `effects` string, or its
independence from `dual_blade_mastery` — the sibling's intent (don't fold the stance into the
mastery skill) is preserved.

#### Scenario: dual_wield_style is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player who owns `dual_wield_style` as a passive skill attempts to cast it
- **THEN** the attempt is rejected with `SKILL_NOT_ACTIVE` at the resolver's ownership step (and
  `action_preview` reports the same `SKILL_NOT_ACTIVE` reason) — never `UNKNOWN_EFFECT_ID`

#### Scenario: Ownership still grants the rule-table adjustment
- **WHEN** an entity owns `dual_wield_style` as a passive skill and has two weapons equipped
- **THEN** `evaluate_combat_modifiers(entity)` returns the `atk_phys: 5` adjustment exactly as it
  did before this change
