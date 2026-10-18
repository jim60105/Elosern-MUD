# Spec Delta

## MODIFIED Requirements

### Requirement: Lineage identity and inventory rarity use backed fields
Lineage graph rows with the same element/style name SHALL be distinguished using their supplied root-node display names joined with ‧ and keep their owned/total count beside that identity. Inventory rarity framing SHALL use committed presentation metadata and retain a non-colour label.

#### Scenario: The collapsed chain row lays out its identity and meter
- **WHEN** a graph row renders
- **THEN** it places its owned/total count (or 已全數見頂 when consumed) immediately after an identity column shared by every row, with no chain meter; the root subtitle joins the graph's supplied root display names, omitted when equal to the label, and no name is derived from a skill key

#### Scenario: Rarity borders stay visible without colour
- **WHEN** an item's rarity frame renders
- **THEN** each rarity draws a distinct border pattern at a width where the pattern is visible (uncommon dotted and rare dashed at 2px, epic double and legendary ridge at 3px) with a faint tint, and common and unknown items remain neutral

#### Scenario: Same element has two lineages
- **WHEN** two graphs share an element label but have distinct root-node display names
- **THEN** both root names are readable beside their own owned/total count

#### Scenario: Unknown item has no rarity
- **WHEN** an inventory row has null presentation
- **THEN** no rarity or item-kind value is inferred from its key
