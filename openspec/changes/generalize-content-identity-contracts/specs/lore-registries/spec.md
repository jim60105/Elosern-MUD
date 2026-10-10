# Spec Delta

## MODIFIED Requirements

### Requirement: Human starting kits express lineage character, not an affluence ladder
Human starting-kit membership SHALL be authored registry data under existing subrace keys. Commoner-lineage kits SHALL preserve equal COMMON rarity profiles without an affluence gradient; noble lineages SHALL retain UNCOMMON inherited arms. General kit existence, equipment-only reference closure and load-time validation SHALL remain owned by player-character-creation. No requirement SHALL list the individual kit items.

#### Scenario: The five human kits match the lineage table
- **WHEN** human kit entries are checked
- **THEN** every current human subrace resolves its declared valid equipment references; existing renamed subrace keys remain unchanged

#### Scenario: The three commoner lineages are equipotent
- **WHEN** commoner lineage kit rarity profiles are compared
- **THEN** each has the same number of COMMON items; content identity differences do not create an affluence gradient

#### Scenario: Wooden club is retired from every kit
- **WHEN** kit equipment is validated
- **THEN** every entry satisfies its authored lineage eligibility, slot and quality rules without a named prohibited-item blacklist

#### Scenario: The lineage kits carry the approved item sets
- **WHEN** kit entries are consumed by character creation
- **THEN** the resulting equipment matches the selected current registry kit rather than duplicated approved key tuples

#### Scenario: The commoner-lineage kits share an identical rarity profile
- **WHEN** commoner lineage kits are inspected
- **THEN** their rarity profiles are identical and all COMMON; individual item selections remain data

#### Scenario: The noble lineages keep their UNCOMMON inherited arms
- **WHEN** the 王族 and 貴族 kits are inspected
- **THEN** they keep their UNCOMMON inherited arms; the equality that matters is among the three commoner lineages

#### Scenario: Rejected items appear in no human kit
- **WHEN** a synthetic kit includes an item violating its declared lineage/quality eligibility
- **THEN** validation rejects the relationship without consulting a historical item-name blacklist

