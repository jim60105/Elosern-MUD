## Why

The binding inventory-drawer design identifies items by a stable type symbol, rarity treatment, and short description, but `ITEM_REGISTRY` currently exposes only a name, price-table key, and sellability. The WebClient therefore cannot render a faithful item grid without guessing from `item_key` or player-facing text.

## What Changes

- Add immutable, registry-owned presentation metadata to every registered `ItemDefinition`: a closed item-kind key, closed SVG icon key, closed rarity key, and bounded Traditional Chinese summary.
- Define one frozen item-presentation value object and its closed enums in `world/lore/items.py`; item identity and visual meaning remain one reviewed registry entry per item key.
- Require the metadata for every registry item, validate enum membership and bounded text at registry test time, and preserve the existing key, display name, price-table key, and sellability contracts.
- Reserve numeric item attributes and equipped-item comparison values for a later deterministic equipment-effects change. This change MUST NOT present numeric combat or recovery values that the rules engine does not currently resolve.

## Capabilities

### New Capabilities
- `item-presentation-metadata`: immutable, validated visual identity metadata for registered items.

### Modified Capabilities
- `shop-economy`: frozen item identities gain required immutable presentation metadata while numeric trade rules remain in YAML.

## Impact

- `world/lore/items.py` and its registry tests gain presentation enums, frozen metadata, and complete values for the existing registry entries.
- Later presentation changes can consume these fields through read-only presenters; this change does not alter persistent inventory, equipment, economy, imports, command behavior, OOB payloads, or the Vue client.
- No dependencies are added and no migration or backward-compatibility path is required because item data is registry-owned and the project has no released users.
