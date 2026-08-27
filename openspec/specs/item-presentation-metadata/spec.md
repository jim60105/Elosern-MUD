# item-presentation-metadata Specification

## Purpose

Define immutable, registry-owned visual identity metadata for registered items.

## Requirements

### Requirement: Registered items have immutable visual identities
`world.lore.items` SHALL define a frozen presentation value for every `ITEM_REGISTRY` item. The value
SHALL include a closed item-kind key, a closed local-SVG icon key, a closed rarity key, and a
bounded Traditional Chinese summary. Inventory and equipment persistence SHALL continue to store
item keys only and SHALL resolve visual identity from the registry at read time.

#### Scenario: Every registered item resolves complete metadata
- **WHEN** each definition in `ITEM_REGISTRY` is inspected
- **THEN** it has a valid kind, icon key, rarity, and non-empty bounded Traditional Chinese summary

#### Scenario: A registry item keeps one visual identity across repeated inventory keys
- **WHEN** a player holds multiple copies of one registered item key
- **THEN** each presentation lookup resolves the same immutable metadata without storing a per-copy duplicate

### Requirement: Item presentation keys are safe, closed renderer contracts
Item kinds, icon keys, and rarity values SHALL be closed `StrEnum` vocabularies owned by `world.lore.items`.
The registry SHALL NOT carry free-form emoji, raw SVG, HTML, image URLs, CSS values, or localized text
used as a renderer selector.

#### Scenario: Invalid visual identity data is rejected during registry validation
- **WHEN** an item definition supplies a value outside a presentation enum or an invalid summary
- **THEN** the registry-focused test fails before a presenter can publish the item

### Requirement: Presentation metadata does not claim unimplemented mechanics
The initial item presentation metadata SHALL NOT contain numeric combat modifiers, recovery values,
requirements, set bonuses, or equipped-item comparison values. A numeric item fact SHALL be added only
by a deterministic rules capability that resolves the same fact during gameplay.

#### Scenario: Presentation-only metadata cannot alter deterministic outcomes
- **WHEN** an item's kind, icon key, rarity, or summary changes while its economy and rules inputs
  remain unchanged
- **THEN** item inventory, equipment, economy, and combat behavior remain unchanged
