## MODIFIED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and the `services`-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and
`InventoryPanel` — the held-item bag plus the equipment presentation) SHALL render only their OOB data. The local map SHALL render the
`local_map` v1 lattice with its states, actionable adjacent nodes, a legend + detail line, and
colorblind-safe (not-color-only) encoding. The art panel SHALL render the `art` payload as a cover-style
16:9 scene with its contextual portrait overlay, and SHALL render a truthful scene placeholder (never an
invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB
channel is unavailable. The shop, quest-board, and lore panels SHALL render only their `services` payload,
and the inventory panel SHALL render the `services` panel's `inventory.rows` — each row's `display_name`,
its `held` count and its `equipped` flag — bounded by the payload's row cap, together with the equipment
presentation built from the `character` panel's `equipment` rows (`slot`, `item_key`, `display_name`).
The inventory panel SHALL NOT render an item rarity, a per-item statistics line, or a comparison tooltip,
because the inventory rows carry no such field, and SHALL NOT render a use, consume, or equip control,
because the payload advertises no such action. No surface SHALL invent data (a dedicated party panel is
not built here).

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders the validated panel when available
- **WHEN** the `art` payload is available
- **THEN** the surface renders the scene cover-style 16:9 with its contextual portrait overlay and the scene label and alternative text outside the bitmap

#### Scenario: Services and inventory are backed only
- **WHEN** the shop, quest, lore, or inventory panel renders
- **THEN** the shop/quest/lore render only the `services` payload and the inventory renders only the `services` panel's inventory rows and the `character` panel's equipment rows, with no invented stock, quest, lore, bag row, rarity, statistic, or equipment slot

#### Scenario: Services unavailable surfaces render only the registry-owned reason
- **WHEN** the `services` OOB channel is unavailable
- **THEN** the shop, quest-board, lore, and inventory panels render only the registry-owned reason message, with no fabricated wallet, stock, quest, lore, rank, bag row, or equipped-item values

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete.
The settings overlay SHALL expose fonts, type scale, reduced-motion, the text-to-HTML toggle, and colorblind
options and SHALL emit `options.*`. The creation overlay SHALL implement a presets/custom/concept wizard
with the adult gate applied to BOTH the age and the apparent_age fields and an activate transition, and
SHALL emit `creation.*`. The `MapOverlay` SHALL re-render its available/unavailable branch whenever the
`local_map` OOB read model is updated, so a replaced payload never leaves a stale state. A surface with
no backing OOB read model today — a dedicated Party/companion panel, the intimate/adult status collapsible,
and the event-log Toasts surface — MUST NOT be built here or mocked to look real. The held-item bag is
NOT among them: it is backed by the `services` panel's `inventory` section, which the server builds for
any actor in exploration mode independently of any service host, so the bag SHALL be built from
`services.inventory.rows`, bounded by the payload's row cap, with `pagination.inventory_total` surfaced
only as the count of rows actually shipped and never as a claim about untruncated holdings. On completion of the showcase wave the required-component
manifest SHALL be frozen at the complete set and the component-coverage gate SHALL enforce that frozen set.

#### Scenario: Creation gate rejects both underage fields
- **WHEN** the creation wizard submits an age or an apparent_age below 18
- **THEN** the adult gate rejects the record before activation

#### Scenario: Settings emit options and honor reduced motion
- **WHEN** a settings control changes
- **THEN** it emits the matching `options.*` envelope and reduced-motion is reflected in the app-wide motion tokens

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no Party panel, intimate/adult collapsible, or event-log Toasts surface is present and none presents invented data

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `services` panel commits an `inventory` section
- **THEN** the bag renders that section's rows with their display names, held counts and equipped flags, bounded by the payload's row cap, and states the cap in words when the listing reaches it

#### Scenario: The manifest is frozen
- **WHEN** the showcase wave completes
- **THEN** the required-component manifest is frozen at the complete set and the component-coverage gate enforces it
