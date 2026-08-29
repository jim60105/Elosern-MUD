## ADDED Requirements

### Requirement: Skill heal magnitude scales by the merged heal_gain percent

The skill-heal magnitude funnel SHALL read the caster's magic stat through the
same equipment-adjusted magic path as magic-school damage, and SHALL apply the
merged bundle's `heal_gain` signed percentage (rule-table and equipment
contributions merged) with one normative formula: compute the unamplified base
amount as today (`max(round(adjusted_magic × multiplier), heal.floor)`), then
`max(floor(base_amount × (1 + percent/100)), heal.floor)`. Consumable item-use
healing SHALL keep its flat rulebook amount and SHALL NOT be scaled by
`heal_gain`.

#### Scenario: Holy gear amplifies a skill heal

- **WHEN** an actor wearing a `heal_gain +20%` accessory casts a heal whose
  unamplified base amount is 40
- **THEN** the restored amount is 48, capped at the effective maximum

#### Scenario: Rounding is floored, not banker-rounded

- **WHEN** the unamplified base amount is 3 and `heal_gain` is +20%
- **THEN** the restored amount is 3 (floor of 3.6), not 4

#### Scenario: Potions ignore heal_gain

- **WHEN** the same actor drinks a registered healing potion
- **THEN** the restore amount equals the item-effect rulebook amount exactly
