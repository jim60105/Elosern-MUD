## MODIFIED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and the `services`-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and `InventoryPanel` — the held-item bag plus the equipment presentation) SHALL render only their OOB data. The local map SHALL render the `local_map` v1 lattice with its states, actionable adjacent nodes, a legend + detail line, and colorblind-safe (not-color-only) encoding. The art panel SHALL render the `art` payload as a cover-style 16:9 scene with its contextual portrait overlay, and SHALL render a truthful scene placeholder (never an invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable. The shop, quest-board, and lore panels SHALL render only their `services` payload. The inventory panel SHALL render the `services` panel's inventory rows as tiles carrying their committed `display_name`, `held` count, `equipped` flag, and nullable presentation metadata, together with the equipment presentation built from the `character` panel's equipment rows (`slot`, `item_key`, `display_name`). A non-null presentation supplies only the committed kind, icon key, rarity, and summary; a null presentation is an explicit unknown-item state. The inventory SHALL render its local icon map only from the committed icon key, SHALL provide keyboard-equivalent inspection, and SHALL render no use, consume, equip, drag, drop, sort, filter, or search control. It SHALL render no numeric stat, requirement, effect, set bonus, or comparison tooltip because neither committed panel carries those facts. No surface SHALL invent data (a dedicated party panel is not built here).

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders the validated panel when available
- **WHEN** the `art` payload is available
- **THEN** the surface renders the scene cover-style 16:9 with its contextual portrait overlay and the scene label and alternative text outside the bitmap

#### Scenario: Services and inventory are backed only
- **WHEN** the shop, quest, lore, or inventory panel renders
- **THEN** the shop/quest/lore render only the `services` payload and the inventory renders only the services inventory rows, their committed presentation data, and character equipment rows, with no invented stock, quest, lore, bag row, item metadata, statistic, or equipment slot

#### Scenario: Unknown item metadata degrades visibly and safely
- **WHEN** an inventory row's committed `presentation` is null
- **THEN** the inventory story renders the labelled neutral unknown-item state with the row's real name and quantity, and no inferred icon, rarity, kind, summary, statistic, or action

#### Scenario: Inventory inspection is equivalent for focus and hover
- **WHEN** a committed row has non-null presentation data and its tile is hovered or focused
- **THEN** both Storybook interaction states expose the same committed name, kind, rarity, summary, count, and equipped marker without a state-changing control, and the focused tile uses `aria-describedby` to reference its inspector

#### Scenario: Services unavailable surfaces render only the registry-owned reason
- **WHEN** the `services` OOB channel is unavailable
- **THEN** the shop, quest-board, lore, and inventory panels render only the registry-owned reason message, with no fabricated wallet, stock, quest, lore, rank, bag row, or equipped-item values
