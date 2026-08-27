## Why

After equipment is relocated into the inventory drawer, its three horizontal text cards still do not match the binding design's compact paper-doll slot language. This visual mismatch can be corrected without changing equipment data, item mechanics, or the inventory item-grid interaction.

## What Changes

- Restyle the shared `EquipmentDoll` as a compact two-column square-slot layout for primary hand, off hand, armor, and an accessory summary.
- Add only fixed local SVG symbols selected by server-authored slot identity, not by an item name or key; show explicit dashed empty slots and visible labels.
- Retain all real equipment names, every accessory row, and unrecognised-slot fallback rows beneath the square layout.
- Expand the existing `Data/EquipmentDoll` and composed inventory Storybook cases for empty, filled, multi-accessory, and unknown-slot states at supported desktop viewports.
- Preserve read-only behavior, drawer focus management, and no numeric item stat, rarity, icon, or comparison claim from the character equipment payload.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: the equipment doll in the inventory drawer adopts the binding square-slot visual language while preserving every server-authored equipment row.

## Impact

- `web/webclient-app/components/EquipmentDoll.vue`, a small local fixed slot-icon map if needed, and existing EquipmentDoll/inventory stories and tests change in the Vue view layer.
- The proposal follows `relocate-inventory-drawer-essentials` and `redesign-inventory-item-grid`, so it has no concurrent ownership conflict with the character-status drawer or inventory grid.
- No OOB shape, registry field, data migration, server rule, equipment mutation, action ID, or tooltip comparison capability changes.
