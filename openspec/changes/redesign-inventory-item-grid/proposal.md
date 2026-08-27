## Why

Even after the inventory drawer owns its header, wallet, and equipment, its flat text rows remain visually and interactively unlike the binding design's compact slot grid. The completed item-presentation projection supplies the missing authoritative icon, rarity, kind, and summary fields needed to replace the list without client-side guessing.

## What Changes

- Replace the held-item text list with responsive native-button inventory tiles using local SVG symbols, stable lower-corner quantities, non-colour-only equipped state, and rarity border treatment from committed row metadata.
- Add one transient item inspector shared by pointer hover and keyboard focus. It shows only committed name, rarity word, kind word, quantity, equipped state, and summary; it never invents numeric stats or comparison values.
- Add a neutral, labelled unknown-item tile for `presentation: null`; it must not infer type, icon, rarity, or summary from the item key or display name.
- Expand the existing Storybook inventory stories with drawer-composed visual states at 1280x720, long labels, each rarity, unknown items, and focused inspection.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: the inventory drawer consumes committed item presentation metadata in a keyboard-accessible tile grid.
- `webclient-component-showcase`: the inventory stories demonstrate committed tile states, including unknown-item degradation and keyboard-equivalent inspection.

## Impact

- `web/webclient-app/components/InventoryPanel.vue` and a small local item-icon/inspector helper implement the view-only interaction and CSS.
- `AppClient.vue` data wiring remains read-only; the drawer's focus trap, action-dock service frame, and OOB dispatch boundary are unchanged.
- Inventory Storybook stories and focused Vitest component tests become the visual and behavioral acceptance surface. Its data prerequisites — `add-item-presentation-metadata` and `expose-inventory-item-presentation` — are archived and complete; `relocate-inventory-drawer-essentials` remains its last prerequisite. The subsequent `restyle-inventory-equipment-slots` proposal owns square-slot styling.
- No server mutation, action identifier, direct state assignment, sorting/filtering policy, gameplay modifier, comparison stat, data migration, or compatibility shim is introduced.
