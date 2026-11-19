# Item Use Resolution Delta

## MODIFIED Requirements

### Requirement: Item mechanics are immutable and independent from presentation
An item SHALL declare immutable use mechanics, equipment mechanics with one slot, or no mechanics. Its own key SHALL resolve its effects. Presentation kind, icon, summary, name, and price SHALL NOT select mechanics. Rarity SHALL constrain validation of authored equipment effects without selecting or scaling them at runtime.

#### Scenario: Healing potion resolves registered use mechanics
- **WHEN** a synthetic combat-permitted, consumable item authoring an HP restoration effect is used on an eligible wounded actor
- **THEN** it restores the authored amount and is consumed, without an equipment slot or a separate effect identifier

#### Scenario: A usable-item definition is mechanics-light by contract
- **WHEN** a consumer reads a loaded usable definition to determine consumption and combat eligibility
- **THEN** the consumer gets the two declared flags and resolves effect magnitude, stat, scope, or status through the profile keyed by the definition's item key

#### Scenario: Visual metadata cannot make an item usable
- **WHEN** an inspect-only item's presentation kind is changed to `potion` without declaring use mechanics
- **THEN** preflight still rejects it as not usable and no state changes

#### Scenario: Ambiguous item mechanics fail registry validation
- **WHEN** a row declares both use mechanics and an equipment slot
- **THEN** validation rejects the item before it can be presented, used, or equipped

#### Scenario: Equipment must bind its effect key
- **WHEN** equipment authoring declares an equipment slot with no inline effect mapping
- **THEN** validation rejects the row rather than accepting an uneffectual missing binding

#### Scenario: Only equipment mechanics may carry a modifier key
- **WHEN** a non-equipment item declares equipment effects under its item key
- **THEN** validation rejects the row rather than publishing effects for a non-equipment key

#### Scenario: The registry rejects malformed mechanics
- **WHEN** an authored row supplies an unknown slot or a non-boolean use flag
- **THEN** validation rejects the row before it is published

#### Scenario: A stored item key still resolves
- **WHEN** equipment storage contains an existing item key and the same item is loaded from an authored document
- **THEN** that key resolves its declared slot and effect with no second saved identifier or save rewrite
