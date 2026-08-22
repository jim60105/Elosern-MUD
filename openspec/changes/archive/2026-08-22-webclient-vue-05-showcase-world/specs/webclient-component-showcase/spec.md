## ADDED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and the `services`-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and
`InventoryPanel` — equipped items only) SHALL render only their OOB data. The local map SHALL render the
`local_map` v1 lattice with its states, actionable adjacent nodes, a legend + detail line, and
colorblind-safe (not-color-only) encoding. The art panel SHALL render the `art` payload as a cover-style
16:9 scene with its contextual portrait overlay, and SHALL render a truthful scene placeholder (never an
invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB
channel is unavailable. The shop, quest-board, and lore panels SHALL render only their `services` payload,
and the inventory panel SHALL render only equipped items. No surface SHALL invent data (a full inventory
bag and a dedicated party panel are not built here).

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders the validated panel when available
- **WHEN** the `art` payload is available
- **THEN** the surface renders the scene cover-style 16:9 with its contextual portrait overlay and the scene label and alternative text outside the bitmap

#### Scenario: Services and inventory are backed only
- **WHEN** the shop, quest, lore, or inventory panel renders
- **THEN** the shop/quest/lore render only the `services` payload and the inventory renders only equipped items, with no invented stock, quest, lore, or bag contents

#### Scenario: Services unavailable surfaces render only the registry-owned reason
- **WHEN** the `services` OOB channel is unavailable
- **THEN** the shop, quest-board, lore, and inventory panels render only the registry-owned reason message, with no fabricated wallet, stock, quest, lore, rank, or equipped-item values
