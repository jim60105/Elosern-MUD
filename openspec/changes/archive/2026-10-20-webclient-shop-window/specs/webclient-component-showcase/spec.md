# Spec Delta

## MODIFIED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `SceneBackdrop`, `ReferenceArtwork`, the services-backed panels (`QuestBoard` and
`LoreDrawer`), the `ShopWindow` (backed by `services` and `item_holdings`), and the party window's
`PartyBagTab` (backed by `party_inventory` and `item_holdings`) SHALL render only committed OOB data.

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders validated content when available
- **WHEN** the art payload is available
- **THEN** the backdrop renders the 16:9 scene with its external scene label and alternative text, and a framed-portrait surface renders a catalog entry it is given with the shared rect crop

#### Scenario: Services and inventory are backed only
- **WHEN** a services-backed panel renders
- **THEN** it renders only committed panel fields and locally mapped controls, with no invented world, item, or mechanic data

#### Scenario: Inventory inspection is equivalent for focus and hover
- **WHEN** a committed row with presentation is hovered or focused
- **THEN** both story states expose the same committed name, kind, rarity, summary, count, equipped marker, and action availability, and focus references the inspector through `aria-describedby`

#### Scenario: Unknown item metadata degrades visibly and safely
- **WHEN** an inventory row has `presentation` null and `action` null
- **THEN** its story renders the neutral unknown state with real name and quantity and no inferred metadata or action

#### Scenario: Inventory use confirmation is showcased
- **WHEN** the actionable healing-potion story activates its tile
- **THEN** the story opens the labelled confirmation and dispatches only after confirm

#### Scenario: Disabled item reasons are showcased
- **WHEN** the full-HP potion or sixth-accessory story activates its tile
- **THEN** the story displays the committed rejection reason without dispatch

#### Scenario: Equipment and five accessories are showcased
- **WHEN** the equipment stories render direct toggle and five-accessory states
- **THEN** committed equipped markers and the five-item accessory summary render without a locally inferred slot or replacement

#### Scenario: Services unavailable surfaces render only the registered reason
- **WHEN** the services OOB channel or the `party_inventory` panel is unavailable
- **THEN** shop, quest and lore stories, and the bag tab story respectively, render only the registered reason with no fabricated values or controls

#### Scenario: Local map stories pass the explicit variant and show no layout control
- **WHEN** the local map's showcase stories render
- **THEN** they pass the renderer's explicit variant parameter and SHALL NOT present a layout
  control

#### Scenario: The local map renders the v1 payload in its resolved variant
- **WHEN** the local map renders
- **THEN** it renders the `local_map` v1 payload with its states, actionable adjacent nodes,
  legend and detail line, and not-colour-only encoding, in the placement variant (coordinate
  lattice or radial connected graph) that the payload's `layer` resolves to, and invents no
  distance, bearing, or terrain geometry in either variant

#### Scenario: Portrait catalog entries stay inside their framed surfaces
- **WHEN** portrait catalog entries render
- **THEN** they render only inside the framed-portrait surfaces that consume them, never as a
  standalone catalog strip

#### Scenario: Shop, quest, and lore render only their services payload
- **WHEN** the shop window, quest board, or lore drawer renders
- **THEN** it renders only its services payload, and the shop window's member chips render only `item_holdings` facts

#### Scenario: The inventory renders its committed fields together
- **WHEN** the `PartyBagTab` renders
- **THEN** it renders committed `party_inventory` display name, held count, equipped count, nullable
  presentation, and the use, toggle and give descriptors together with the committed equipment doll
  and the selected item's committed holdings

#### Scenario: Presentation and action come only from committed descriptors
- **WHEN** an inventory row renders its icon map usage or action behavior
- **THEN** the inventory uses its local icon map only from committed icon keys and action behavior
  only from committed action descriptors

#### Scenario: The inventory interaction set invents no mechanic
- **WHEN** the inventory provides inspection and activation (keyboard-equivalent), confirmation for
  usable items, direct equipment toggle, and committed disabled-reason states
- **THEN** it does so without inventing an effect, recovery amount, condition, consumable flag,
  equipment slot, statistic, requirement, set bonus, client-computed comparison, sort, search,
  drag, or drop behavior; its only comparison is the server's `item_holdings` delta and its only
  filter is the selected doll slot

#### Scenario: No surface invents data, party panel included
- **WHEN** any map, art, or services surface renders
- **THEN** none invents data, including a dedicated party panel

#### Scenario: The manifest includes the inventory story set
- **WHEN** the showcase required-set manifest is enumerated
- **THEN** it SHALL include deterministic offline stories and tests for actionable use, use
  confirmation, full-HP rejection, direct equipment toggle, equipped state, five accessories,
  accessory-cap warning, unknown items, and services unavailability
