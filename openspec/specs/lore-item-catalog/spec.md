# lore-item-catalog Specification

## Purpose
Holds the behavioral invariants that follow from an item's declared mechanical shape, independent of which items the world happens to contain: what an item with no mechanics may and may not do, what non-sellability costs, what registration does and does not entitle an item to, and what must hold when an item is retired.

## Requirements

### Requirement: Retiring an item key leaves no dangling reference
An item key that leaves the registry SHALL leave every surface that names items in the same change. Every loader, validator, and registry that can name an item key SHALL fail closed on a key the registry does not define — raising and naming the offending key and its owning surface — rather than skipping the reference, substituting a placeholder, or degrading to an unnamed item. This SHALL hold for shop offered keys and shop offers, equipment modifier bindings and equipment-effect entries, item-effect profiles, starting kits, character presets, and quest objectives and rewards alike, so that a half-completed removal is impossible to ship rather than merely discouraged.

#### Scenario: A shop offer naming a retired key fails the catalog load
- **WHEN** a shop's offered keys or offers name an item key the registry does not define
- **THEN** the catalog load raises naming that key, and no merchant is constructed with a partial inventory

#### Scenario: An equipment binding naming a retired key fails startup
- **WHEN** an equipment-effect entry or modifier binding names an item key the registry does not define
- **THEN** the rulebook load raises naming that key rather than leaving an orphaned entry

#### Scenario: A usable-item profile naming a retired key fails startup
- **WHEN** an item-effect profile names an item key the registry does not define
- **THEN** the two-sided close raises naming that key

#### Scenario: A kit, preset, or quest naming a retired key is rejected
- **WHEN** a starting kit, a character preset, or a quest objective or reward names an item key the registry does not define
- **THEN** its validator rejects that record naming the key, rather than granting nothing or granting an unnamed item

#### Scenario: A completed retirement leaves the catalog closed
- **WHEN** an item key is removed from the registry together with every reference to it
- **THEN** startup succeeds, every loader closes with no unbound key and no orphaned entry, and no surface reports a missing item
