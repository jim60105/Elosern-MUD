## MODIFIED Requirements

### Requirement: Item mechanics are immutable and independent from presentation

Every registered item SHALL declare exactly one of a usable-item definition,
an equipment-slot definition, or no mechanics. A usable-item definition SHALL
contain a registered deterministic effect key, a boolean consumable flag, and
a combat-use permission. An equipment definition SHALL contain exactly one
`EquipmentSlot` and exactly one registered `EquipmentModifierKey` binding it
to the equipment-effect rulebook; an item whose mechanics are not an
equipment definition SHALL NOT carry a modifier key. The registry SHALL
reject an item that declares both forms, an unknown effect, a malformed
slot, a missing or unknown modifier key on an equipment item, or a modifier
key on any non-equipment item. Presentation kind, icon, rarity, summary,
display name, and price SHALL NOT select or modify mechanics.

#### Scenario: Healing potion resolves registered use mechanics

- **WHEN** the `healing_potion` definition is inspected
- **THEN** it resolves the registered self-heal effect, is consumable, is
  allowed in combat, and carries no equipment slot

#### Scenario: Visual metadata cannot make an item usable

- **WHEN** an inspect-only item's presentation kind is changed to `potion`
  without adding use mechanics
- **THEN** item preflight still rejects it as not usable and no state changes

#### Scenario: Ambiguous item mechanics fail registry validation

- **WHEN** an item definition declares both use mechanics and an equipment
  slot
- **THEN** registry construction fails before the item can be presented or
  used

#### Scenario: Equipment must bind its effect key

- **WHEN** an item definition declares an equipment slot without a registered
  modifier key, or declares a modifier key while carrying no equipment slot
- **THEN** registry construction fails before the item can be presented or
  toggled
