# Proposal

## Why

Adding equipment requires repeating its key in the item catalog, a Python enum, and a YAML effect table. An author should be able to find and change an item's definition and dedicated effects together, without learning how the engine assembles them.

## What Changes

- Make `content/items/` the sole authored source for item definitions and their dedicated use and equipment effects. Keep shared timing, equipment budgets, price bands, shop stock, and offers separate.
- **BREAKING (authoring and internal API only):** Remove Python item rows, the per-item `EquipmentModifierKey` enum and `modifier_key` field, and standalone per-item effect rows. Use the stable item key for effect lookup; retain the existing inventory representation, game behavior, and presentation order.
- Show each loaded item's repository-relative source file in the existing read-only GM world-data detail. Preserve its existing registry and reference links.
- Amend architectural decision D9 during implementation to allow typed, declarative content under `content/`; apply it only to items in this change. Do not migrate other content or change save formats, map editing, combat rules, commerce, or runtime ownership.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lore-item-catalog`: Require an ordered, typed item catalog authored in YAML, with source diagnostics and one accepted source per key.
- `equipment-effects`: Bind an inline effect record by its item's key, preserving explicit empty utility effects and existing validation.
- `item-effect-rulebook`: Put ordered use effects on their item and retain the separate shared use-time setting.
- `item-use-resolution`: Update the definition of an equippable item without changing settlement semantics.
- `gm-world-data`: Expose loaded item source provenance in the existing detail response and view.

## Impact

- Affects `world/lore/items/`, the item/equipment effect loaders and their lookup consumers, the GM world-data detail, and test fixtures that instantiate equipment.
- The map editor's reference-context source discovery must cover the relocated files so independent freshness checking keeps working. The existing image already copies `content/`.
- Existing stored item identifiers, presentation values, display order, rule values, and effect dispatch stay unchanged. No data migration or dual-read fallback.
