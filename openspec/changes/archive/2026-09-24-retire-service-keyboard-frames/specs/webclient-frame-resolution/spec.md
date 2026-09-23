## ADDED Requirements

### Requirement: The resolver table completes with the combat and creation families

The resolver table SHALL additionally implement, and produce the menus the migrated push sites produce today: combat family (panel `context_actions` combat form, selection state owned by the combat model) — `combat.root` `{}`, `combat.categories` `{}`, `combat.category` `{categoryIndex}`, `combat.group` `{categoryIndex, groupIndex}`, `combat.skill` `{skillKey}`, `combat.target` `{skillKey}`, `combat.forfeit` `{}`; creation family (panel `creation`) — `creation.root` `{}`, `creation.presets` `{}`, `creation.form` `{view: "custom" | "concept"}` resolving to the wizard's empty marker frame, `creation.confirm` `{kind, presetKey?}`. The table SHALL NOT implement a services family: the committed `services` panel has no dock frame; every service surface renders in its reference drawer directly from the committed panel, so any `services.*` descriptor resolves to the shared unresolvable marker as an unregistered source. The table SHALL NOT implement a dialogue family: the committed dialogue panel has no dock frame; the caption's dialogue variant derives its rows directly from the committed panel through the shared view model without any descriptor. An out-of-range index or absent key SHALL resolve to the shared unresolvable marker like a lost identity.

#### Scenario: Every completed-table source resolves from a live snapshot

- **WHEN** each combat and creation source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its migrated push site produced, with the same row keys, server-authored payloads, and titles

#### Scenario: No services descriptor is registered

- **WHEN** any `services.*` descriptor (for example `services.guild` or `services.stock`) resolves against any committed state
- **THEN** resolve returns the shared unresolvable marker (an unregistered source), and no router frame in any live mode ever holds a `services.*` descriptor

#### Scenario: No dialogue descriptor is registered

- **WHEN** `dialogue.root` resolves against any committed state
- **THEN** resolve returns the shared unresolvable marker (an unregistered source), and no router
  frame in any live mode ever holds a `dialogue.root` descriptor

## REMOVED Requirements

### Requirement: The resolver table completes with the services, combat, and creation families
**Reason**: The services family (`services.root|guild|board|quests|quest-detail|shop|stock|sell|confirm`) has no remaining push site: every service surface is a frameless reference drawer rendered from the committed `services` panel, so its resolvers and menu model are deleted.
**Migration**: The combat and creation families move unchanged into "The resolver table completes with the combat and creation families", which also states that no services descriptor is registered. Tests annotated with the old ID re-anchor to the new one.
