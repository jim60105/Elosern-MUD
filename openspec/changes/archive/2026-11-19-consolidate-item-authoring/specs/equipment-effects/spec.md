# Equipment Effects Delta

## MODIFIED Requirements

### Requirement: Equipment items bind one-to-one to a closed effect identity
Each item with an equipment slot SHALL carry exactly one inline equipment-effect mapping, bound by its own item key. Non-equipment items SHALL NOT carry that mapping. An effect mapping MAY be explicitly empty for equipment with no effects.

#### Scenario: Equipment without an effect binding fails validation
- **WHEN** a row declares an equipment slot but omits its effect mapping or sets it to null
- **THEN** validation fails before the game starts, identifying the item and field

#### Scenario: Non-equipment items reject effect keys
- **WHEN** a usable item declares an equipment-effect mapping
- **THEN** validation fails before the game starts

#### Scenario: Duplicate modifier bindings fail the load
- **WHEN** an equipment row repeats its effect mapping key
- **THEN** validation rejects the duplicate rather than applying either mapping

#### Scenario: Utility equipment declares an explicit empty binding
- **WHEN** a utility item with an equipment slot declares an empty effect mapping
- **THEN** it can be equipped and supplies no adjustments, immunities, or attached buffs

#### Scenario: Slotless items reject modifier keys
- **WHEN** an inspect-only item declares `equipment_effects` or the retired `modifier_key` field
- **THEN** validation rejects the slotless row

#### Scenario: Unbound keys, orphaned entries, and duplicate bindings fail the load
- **WHEN** a shared equipment budget file declares an independent effect entry for a missing item
- **THEN** the budget file is rejected rather than accepting a second source of equipment effects

#### Scenario: Effects resolve by each equipped item's own identity
- **WHEN** two otherwise equivalent items declare different effects and each is worn in turn
- **THEN** each applies its own effect, without a second identity declaration or effects borrowed from the other item

### Requirement: The equipment-effect rulebook validates a closed schema at load time
The equipment-effect loader SHALL validate inline records and shared budgets through one deterministic validation path with injectable sources. Malformed records SHALL fail with a named source diagnostic and SHALL NOT be repaired, clamped, or silently dropped.

#### Scenario: Out-of-vocabulary field is rejected
- **WHEN** an equipment-effect record carries an unknown field or adjustment key
- **THEN** validation rejects the candidate and identifies the item and invalid field

#### Scenario: The closed entry vocabulary
- **WHEN** equipment effects are validated
- **THEN** supported fields are `adjustments` restricted to `atk_phys`, `defense`, `magic_power`, `agility`, `mp_cost`, `sp_cost`, `pleasure_gain`, and `heal_gain`; `gauge_caps`, `immune`, `attached_buffs`, `exposure_bias`, and optional weapon-only `weapon_damage_multiplier`

#### Scenario: Percent-shaped fields reject flat values
- **WHEN** an `mp_cost` adjustment gives a flat integer
- **THEN** validation rejects the record

#### Scenario: Adjustment fields accept only signed integers or signed percent strings
- **WHEN** a flat `atk_phys`, `defense`, or `magic_power` adjustment or a flat or percent `agility` adjustment is declared
- **THEN** validation accepts in-budget integers for the flat fields and either permitted shape for `agility`; it rejects percent strings for the flat fields and unsupported shapes for `agility`

#### Scenario: Percent-only fields accept signed percent strings only
- **WHEN** an `mp_cost`, `sp_cost`, `pleasure_gain`, or `heal_gain` adjustment is not a signed percent string
- **THEN** validation rejects the record

#### Scenario: Gauge caps are positive integers over the gauge vocabulary
- **WHEN** a gauge cap names a key outside `hp`, `mp`, or `sp`, or has a non-positive or non-integer value
- **THEN** validation rejects the record

#### Scenario: Buff lists and exposure bias are typed
- **WHEN** `immune` or `attached_buffs` is not a list of buff keys, or `exposure_bias` is not a signed integer
- **THEN** validation rejects the record
