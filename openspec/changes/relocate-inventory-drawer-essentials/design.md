## Context

The reference drawer at `docs/design/elosern-redesign/index.html:957-985` owns three related pieces of information: its bag icon and wallet summary in the header, the equipment section, and the held-item listing. The current application reverses that hierarchy. `HudDrawer` already owns the drawer title but `InventoryPanel` repeats it, while `EquipmentDoll` and the one drawer-layer wallet figure are rendered by `CharacterStatusDrawer`.

`HudDrawer` already provides a focus trap, scrim close, Escape handling, restore-to-opener behavior, responsive drawer geometry, and a local `inventory` SVG path. This change reuses those primitives. It follows `fix-webclient-character-status-drawer-order` so the two changes do not concurrently edit the character drawer template.

## Goals / Non-Goals

**Goals:**

- Give the inventory drawer the reference's information hierarchy without introducing an additional drawer or data source.
- Put the visual leading icon and wallet summary in the shared header, leaving the body for inventory content.
- Render the existing true equipment representation as the first inventory section and retain every named, accessory, and unknown server-authored slot.
- Keep a single wallet figure across the drawer layer and preserve keyboard behavior.

**Non-Goals:**

- No item grid, hover card, rarity treatment, item summary, filters, sorting, search, item comparison, or state-changing affordance. The following visual-grid change owns these concerns.
- No change to `HudDrawer` geometry, animation, focus trap, action-dock router, server APIs, OOB data, or persistent state.
- No second wallet from `services.inventory.wallet`; the balance remains sourced only from the committed character panel.

## Decisions

### Use the existing drawer header as the inventory header

`AppClient` passes `icon="inventory"` and a computed `錢袋 {copper} 銅` subtitle only when the character panel is available and has a valid wallet. `HudDrawer` remains the only source of the title, icon, subtitle, and close control; `InventoryPanel` removes its duplicate heading.

Adding a second bespoke inventory header was rejected because it would duplicate the title, close control, and keyboard ownership already owned by the shared chrome. Showing the services wallet was rejected because the system already declares `character.wallet` authoritative for the drawer-layer balance and a missing character panel must not turn into an invented zero.

### Move the existing doll rather than clone equipment rendering

`InventoryPanel` receives the committed `character` panel and composes the existing `EquipmentDoll` before its held-item content. `CharacterStatusDrawer` stops composing that component and stops rendering its wallet section. The doll continues to read only `character.equipment`, retain the named singleton slots, accessory group, explicit empty states, and unknown-slot passthrough.

Duplicating the doll would create two divergent renderers of the same committed equipment rows. Moving it retains the existing data-bound behavior and makes the subsequent square-slot styling change shared rather than special-cased.

### Define explicit unavailable behavior at the new composition boundary

The inventory drawer's services state remains authoritative for whether the bag itself is available. When services are unavailable or the inventory section is absent, the body renders only the current registry-owned reason or absence message and no doll. When services are available but the character panel is unavailable, the body may render the held items but shows the `EquipmentDoll`'s existing registered unavailable message and leaves the header subtitle blank.

This follows the existing section-by-section degradation rule without mixing two panel owners or fabricating a slot, item, or balance.

### Make the composed drawer story the visual acceptance target

The `World/InventoryPanel` stories render within an open real `HudDrawer` using character and services fixtures. They cover filled and empty equipment, unavailable character metadata, available and unavailable services, and the ceiling state. The component-level `EquipmentDoll` stories remain focused on its slot contract.

This replaces the current generic bordered wrapper, which cannot reveal duplicated headings, header hierarchy, safe content scrolling, or the real drawer width.

## Risks / Trade-offs

- [This conflicts with the active character-status order proposal] -> Declare and respect the dependency on `fix-webclient-character-status-drawer-order`; do not implement until that change is complete.
- [Two panels can become unavailable independently] -> Test all four relevant states and never substitute a wallet, equipment row, or zero count from the other panel.
- [Moving the wallet surprises users of the status drawer] -> The binding design puts the wallet in the inventory header and the drawer remains a single action from the dock; no hidden or duplicated balance remains.
- [The moved doll still looks unlike the reference slots] -> Keep visual square-slot and item-grid treatment deliberately deferred to the next one-day proposal rather than expanding this move into a combined redesign.

## Migration Plan

Land after `fix-webclient-character-status-drawer-order` and before the item-grid visual redesign. The change is client-only and has no persisted layout state or external consumer. Run the affected Vue tests and Storybook visual review at 1280x720; a rollback restores the prior component placement with no data conversion.
