## Why

The binding design makes the bag drawer the single home for equipment and wallet context, but the current Vue implementation duplicates the drawer title in its body, keeps the equipment doll and wallet in the character-status drawer, and gives the inventory drawer no leading bag symbol or balance subtitle. This separation makes the reference panel feel like a flat list rather than a coherent inventory surface.

## What Changes

- Move the existing read-only `EquipmentDoll` composition from `CharacterStatusDrawer` into `InventoryPanel` and pass the committed `character` panel into the inventory drawer.
- Move the one drawer-layer wallet rendering from character status to the inventory drawer header, formatted as integer copper and shown only when its committed character panel is available.
- Configure the shared `HudDrawer` inventory instance with the existing local bag SVG and wallet subtitle; remove the duplicate `背包 · 裝備` heading from `InventoryPanel`.
- Preserve every drawer's focus trap, scrim, Escape, focus restoration, service-frame ownership, no-action inventory policy, and unavailable behavior.
- Update the inventory and character-status Storybook stories so the actual composed drawer, not an unframed body, is visually reviewable.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: relocate the existing equipment and single wallet presentation to the binding inventory-drawer information architecture.

## Impact

- `web/webclient-app/AppClient.vue`, `InventoryPanel.vue`, `EquipmentDoll.vue`, `CharacterStatusDrawer.vue`, and drawer/component stories change only in the Vue presentation layer.
- Its prerequisite changes — `fix-webclient-character-status-drawer-order`, `add-item-presentation-metadata`, `expose-inventory-item-presentation`, and `add-webclient-intimate-status-section` — are all archived and complete, so this change is unblocked. It preserves the completed 親密狀態 section of the character drawer and removes only the moved equipment and wallet sections; it consumes the archived services-v2 presentation contract without depending on the later grid styling.
- No OOB schema, persistence, server action, item mutation, data migration, or compatibility layer changes in this proposal.
