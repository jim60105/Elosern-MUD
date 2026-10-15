# Spec Delta

## ADDED Requirements

### Requirement: Shipped weapons have authored selected values backed by real growth evidence
Every shipped weapon SHALL have a recorded initial and selected multiplier or a justified neutral declaration within authored rarity budgets. Real physical weapon upgrades SHALL include nonneutral selected values. The values SHALL be loaded data, never inferred from rarity or progression, and SHALL survive ordinary equipment persistence and reload.

#### Scenario: Real upgrade below subtraction threshold
- **WHEN** real constructed actors commit and reload an adequate weapon/attack upgrade in a case where old subtraction masked damage
- **THEN** the measured successful physical hit has positive marginal growth, with exact inputs and selected value recorded; tiny integer-masked improvements are not claimed universally

#### Scenario: Armor and invariant controls
- **WHEN** committed real equipment changes defense or a weapon is tested against magic/healing controls
- **THEN** positive defense reduces successful damage monotonically, no armor multiplier is added, magic/healing receive no weapon factor and base traits/proficiency/affinity rules remain unchanged


