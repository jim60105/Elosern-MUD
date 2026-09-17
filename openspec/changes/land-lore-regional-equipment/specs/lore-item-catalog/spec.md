## ADDED Requirements

### Requirement: Catalogued equipment binds completely and stays inside its rarity budget
Every catalogued equipment item SHALL declare an equipment slot and a modifier binding whose value equals the item's own key, and SHALL have exactly one rulebook entry under that key. Every adjustment the codex publishes for an equipment item SHALL fall inside the budget column its field maps to for that item's registered rarity, and the rarity the codex states SHALL be the rarity the registry declares — so a codex number can never authorise more than its rarity affords.

#### Scenario: Every catalogued equipment item is bound on both sides
- **WHEN** the catalogued equipment roster is compared against the equipment-effect rulebook
- **THEN** each item declares a slot and a modifier key equal to its own key, each has exactly one rulebook entry, and no rulebook entry is orphaned

#### Scenario: Codex numbers are budget-legal at their stated rarity
- **WHEN** each codex adjustment is checked against the budget column for its field at the item's registered rarity
- **THEN** every flat, percent, soft-percent, exposure-bias, and gauge value is within that column's ceiling

#### Scenario: An over-budget codex number cannot ship
- **WHEN** a catalogued equipment item is authored with an adjustment above its rarity's ceiling
- **THEN** the rulebook load fails at startup and the roster test fails, before the item can be equipped by anyone

### Requirement: Regional equipment is registered without a storefront
The catalog SHALL register the codex's Beastfolk Kingdom, elven, and dungeon-trophy equipment — 獸人重鎚, 獸人連射短弓, 獸人陣地長槍, 獸人雙爪刃, 獸人導靈短杖, 精靈長弓, 龍之巢穴戰利品劍, 獸人厚甲, 獸人輕行衣, 精靈森林輕紗, 獸人部族圖騰, 獸人疾風耳環 — as fully bound equipment that no shop offers. These pieces SHALL remain equippable, inspectable, and referenceable by quests, loot, presets, and starting kits; their absence from every shop reflects that their codex provenance reaches no existing storefront, not a defect in their data.

#### Scenario: The regional roster is complete and equippable
- **WHEN** the twelve regional equipment keys are inspected
- **THEN** each resolves complete identity, presentation, slot, and binding, and each can be equipped into its declared slot from inventory

#### Scenario: No shop stocks a regional piece
- **WHEN** every shop's offered keys are inspected
- **THEN** none of the twelve regional keys appears

#### Scenario: Registry-only equipment still reaches a player through a non-shop grant
- **WHEN** a regional piece is placed in an entity's inventory by any non-shop path
- **THEN** it equips and its adjustments apply exactly as a purchased item's would
