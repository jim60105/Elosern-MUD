# Item Catalog Delta

## ADDED Requirements

### Requirement: The item catalog has one ordered declarative source
The shipped item catalog SHALL load from `content/items/` as typed, immutable definitions in authored order, keyed by stable `snake_case` identifiers. The loader SHALL reject malformed documents, unknown fields, and duplicate or invalid keys before accepting a candidate and report the source file and applicable item key and field.

#### Scenario: Add equipment by editing one item document
- **WHEN** an author adds a row with a new key, an equipment slot, and a valid effect using the existing vocabulary
- **THEN** the catalog resolves that key and wearing the item applies its authored effect without another registration or a source-code edit

#### Scenario: Authoring order is deterministic
- **WHEN** a synthetic catalog declares source files and rows in an order different from key sort or filesystem order
- **THEN** the loaded catalog follows the declared file order and preserves row order within each file

#### Scenario: Duplicate declaration or invalid field is rejected
- **WHEN** a candidate repeats an item key or YAML mapping key, includes a colon in an item key, or supplies an unknown field or a value of the wrong type
- **THEN** the candidate is rejected and the diagnostic identifies the offending source and the applicable row and field

## MODIFIED Requirements

### Requirement: Retiring an item key leaves no dangling reference
Removing an item row SHALL retire its dedicated effects with it. Every authored external reference to the item key SHALL be removed in the same change. A loader, validator, or registry encountering an undefined item key SHALL reject the reference and identify the key and owning surface.

#### Scenario: A shop offer naming a retired key fails the catalog load
- **WHEN** a shop's offered keys or offers name an item key the registry does not define
- **THEN** the catalog load raises naming that key, and no merchant is constructed with a partial inventory

#### Scenario: An equipment binding naming a retired key fails startup
- **WHEN** the shared budget file still supplies a retired item's effect mapping, or an item row attempts to bind its effects to a separate modifier key
- **THEN** validation rejects those fields and names the owning source

#### Scenario: A usable-item profile naming a retired key fails startup
- **WHEN** the shared use-time file still supplies a retired item's use effects
- **THEN** validation rejects the old per-item field and names the owning source

#### Scenario: A kit, preset, or quest naming a retired key is rejected
- **WHEN** a starting kit, character preset, quest objective, or quest reward names an item key the registry does not define
- **THEN** its validator rejects that record naming the key rather than granting nothing or granting an unnamed item

#### Scenario: A completed retirement leaves the catalog closed
- **WHEN** an item row and all its external references are removed
- **THEN** startup succeeds without editing a second effect table and no definition or effect profile remains for the key

#### Scenario: The fail-closed error names the key and its owning surface
- **WHEN** an authored external reference names an undefined item key
- **THEN** validation identifies the missing key and the surface that names it

#### Scenario: Every item-naming surface participates in the fail-closed check
- **WHEN** an undefined item key appears in shop offered keys, shop offers, starting kits, character presets, or quest objectives or rewards
- **THEN** the corresponding surface rejects it instead of skipping it or substituting a placeholder
