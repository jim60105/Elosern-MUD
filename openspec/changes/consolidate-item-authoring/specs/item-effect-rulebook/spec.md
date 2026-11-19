# Item Effect Rulebook Delta

## MODIFIED Requirements

### Requirement: A usable item's effects are an ordered list bound by item key
A usable item SHALL author its non-empty effect list alongside its consumption and combat-use flags. The runtime mechanics flags SHALL remain separate from the effect profile, resolved by the item's own key. List order SHALL be application order and non-combat use time SHALL remain a shared setting.

#### Scenario: A registry definition carries no effect identity
- **WHEN** a usable authored row is loaded as a definition and an effect profile
- **THEN** the use-mechanics view contains its two flags with no separate effect ID or parameters; effect resolution finds the profile by the definition's item key

#### Scenario: One item declares several effects applied in order
- **WHEN** a row lists two order-sensitive effects and the item is used successfully
- **THEN** both apply in authored order for that item

#### Scenario: Item row edits do not select a different use duration
- **WHEN** two usable items declare different effects
- **THEN** a successful non-combat use of either charges the same separately configured time cost

### Requirement: The rulebook and the registry align exactly at startup
All and only usable item rows SHALL contribute a use profile at startup. A missing, empty, or invalid use-effect list on a usable item, or a use-effect list on any other item, SHALL reject the catalog before gameplay.

#### Scenario: An orphan rulebook entry fails startup
- **WHEN** an item that does not declare use mechanics supplies use effects
- **THEN** validation rejects the item before gameplay

#### Scenario: A usable item with no rulebook entry fails startup
- **WHEN** an item declares use mechanics but omits its effect list or sets it to null
- **THEN** validation rejects the item before gameplay

#### Scenario: An empty effect list fails startup
- **WHEN** a usable item declares an empty effect list
- **THEN** validation rejects the item before gameplay
