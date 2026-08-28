## Why

The inventory drawer exposes every held item as a focusable button, but activating a button only selects it for inspection and cannot use, equip, or unequip the item. The deterministic core also lacks item-use mechanics and safe item-specific equipment toggles, so the graphical control cannot truthfully perform the interaction the button implies.

## What Changes

- Add immutable, registry-owned item mechanics that distinguish usable items from equipment, declare consumable versus reusable use, bind deterministic effects and use conditions, and assign equipment to an exact slot without treating presentation metadata as rules data.
- Add an atomic deterministic item-use operation that revalidates current ownership and eligibility, applies the effect, consumes exactly one canonical key and one existing contained-object mirror only for consumables, and leaves all state unchanged on rejection or failure. Healing potions reject use at full HP.
- Allow a successful item use during active combat to consume the player's action for one complete combat round, including player-direction overwhelm compression; a rejected use consumes neither the item nor the turn.
- Add an atomic item-specific equipment toggle that verifies current ownership and item definitions, unequips the selected equipped item, replaces the occupant of a main-hand, off-hand, or armor slot, and never removes an unrelated accessory.
- **BREAKING** Increase `ACCESSORY_MAX_SLOTS` from three to five. A sixth accessory is rejected without automatic replacement; the player must explicitly unequip an accessory first.
- Add exact allowlisted `inventory.use` and `inventory.toggle_equip` WebClient actions whose server adapters re-resolve and re-authorize canonical state instead of routing through the text parser. Evolve `services` to v3 so personal inventory remains available during combat without exposing guild or shop services.
- Extend committed inventory rows with server-authored action descriptors and disabled reasons. Unknown and non-actionable items remain inspectable but cannot dispatch a mutation.
- Make usable-item tiles open an accessible confirmation dialog before dispatch. Equipment tiles toggle immediately; rejected use or a full accessory set uses the existing bounded action-result alert surface. In-flight locking prevents duplicate dispatch.
- Preserve text-client playability through `使用 <item_key>` (`use`) and `裝備 <item_key>` (`equip`), both delegating to the same deterministic operations rather than making item actions WebClient-only.

## Capabilities

### New Capabilities
- `item-use-resolution`: Registry-owned item mechanics, current-state preflight, atomic effect and consumption settlement, named rejections, and combat-turn integration.
- `inventory-item-actions`: Allowlisted item-use and equipment-toggle actions, server-authored inventory affordances, confirmation and alert behavior, refresh semantics, and text-client parity.

### Modified Capabilities
- `equipment-inventory`: Raise the accessory cap to five; define ownership-aware, item-specific toggle, singleton replacement, and exact accessory removal; and keep consumable key-list removal synchronized with any contained-object mirror.
- `player-combat-session`: Admit a preflight-valid item use as the player's action for one complete round while preserving the round on rejected use.
- `webclient-service-menus`: Replace the inventory rows' explicit no-action contract with bounded use or equipment action descriptors and current disabled reasons.
- `webclient-contextual-hud`: Replace the bag tile's inspection-only contract with confirmation-gated use and direct equipment toggling while retaining keyboard access and the frameless drawer.
- `webclient-component-showcase`: Add deterministic showcase coverage for actionable, disabled, confirming, equipped, and accessory-cap inventory states.

## Impact

- Deterministic rules and combat orchestration under `world/rules/`, including inventory planning, HP effects, equipment settlement, and active combat sessions.
- Immutable item definitions under `world/lore/items.py` and read-only equipment constants under `world/skills/equipment.py`.
- Services and character presentation models, validators, serialization, and protocol versions under `world/rules/service_view.py` and `web/webclient/presentation/`.
- The `ui_action` registry and a narrow inventory action adapter under `web/webclient/actions/`.
- The Vue/Pinia inventory drawer, action-result alert flow, accessible dialog behavior, component tests, stories, and showcase coverage.
- Player item commands and both command-reference documents required by the command-surface contract.
- Existing persisted inventory and equipment shapes remain key-only and require no migration; the project has no released users and adds no compatibility layer.
