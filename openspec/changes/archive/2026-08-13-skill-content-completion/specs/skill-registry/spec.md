## ADDED Requirements

### Requirement: dual_blade_mastery exists as a higher-tier sibling to dual_wield_style
`SKILL_REGISTRY` SHALL contain `dual_blade_mastery` (雙刀流·宗師級), `ACTIVE`,
`TargetSpec.SINGLE`, `cost={"sp": 30}`, `effects=["damage:dark:physical"]`,
`faction_constraint=FactionConstraint.ANY`. This SHALL NOT replace or modify `dual_wield_style`.

#### Scenario: dual_blade_mastery is castable and independent of dual_wield_style
- **WHEN** a player casts `dual_blade_mastery` at a valid `SINGLE` target
- **THEN** the cast resolves successfully via the existing `damage` handler, and owning or not owning
  `dual_wield_style` has no bearing on this skill's availability or cost

### Requirement: guardian_instinct and blade_art_mastery display text reflects character-sheet flavor
`guardian_instinct`'s label/description SHALL read as 護主本能-flavored, and `blade_art_mastery`'s
description SHALL explicitly cover both 劍術 and 刀術. Neither skill's `key` or `effects` SHALL change.

#### Scenario: Effect behavior is unchanged
- **WHEN** `guardian_instinct` and `blade_art_mastery`'s `effects` lists are inspected after this
  change
- **THEN** both are byte-identical to their pre-change values — only `label`/`description` differ
