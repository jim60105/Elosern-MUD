## MODIFIED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and services-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and `InventoryPanel`) SHALL render only committed OOB data. The local map SHALL render the `local_map` v1 lattice with its states, actionable adjacent nodes, legend and detail line, and not-colour-only encoding. Art SHALL render the committed scene as a cover-style 16:9 image with contextual portrait overlay and SHALL render a truthful placeholder whenever the asset is missing, pending without a prior image, failed, invalid, or unavailable. Shop, quest, and lore SHALL render only their services payload.

`InventoryPanel` SHALL render committed inventory display name, held count, equipped flag, nullable presentation, and nullable action descriptor together with committed character equipment rows. A non-null presentation SHALL supply only committed kind, icon key, rarity, and summary; a null presentation SHALL remain an explicit unknown-item state. The inventory SHALL use its local icon map only from committed icon keys and action behavior only from committed action descriptors. It SHALL provide keyboard-equivalent inspection and activation, confirmation for usable items, direct equipment toggle, and committed disabled-reason states without inventing an effect, recovery amount, condition, consumable flag, equipment slot, statistic, requirement, set bonus, comparison, sort, filter, search, drag, or drop behavior. Unknown rows SHALL remain visibly inspect-only. No surface SHALL invent data, including a dedicated party panel.

The showcase required-set manifest SHALL include deterministic offline stories and tests for actionable use, use confirmation, full-HP rejection, direct equipment toggle, equipped state, five accessories, accessory-cap warning, unknown items, and services unavailability.

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders validated content when available
- **WHEN** the art payload is available
- **THEN** the surface renders the 16:9 scene with contextual portrait overlay and external scene label and alternative text

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
- **WHEN** the services OOB channel is unavailable
- **THEN** shop, quest, lore, and inventory stories render only the registered reason with no fabricated values or controls
