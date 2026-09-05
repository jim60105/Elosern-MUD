# Delta spec: profession-registries (profession-rulebook-registry)

New capability: the authored profession table as game data. Assembly-time semantics only; the
`default_binding` value is stored here and first read by the service-anchoring gate.

## ADDED Requirements

### Requirement: Professions are one validated rulebook table with keyed frozen reads
`world/rules/rulebook/professions.yaml` SHALL declare every authored profession as a list under
`professions:` with `schema_version: 1`, and `world/rules/profession_config.py` SHALL expose the
loaded table as frozen dataclasses through keyed reads (`get_profession(key)` returning the
profession or `None`, and `all_professions()`), following the `guild_config.py` load/cache family.
Each profession row SHALL carry exactly: a non-empty unique `key`; a `components:` list of
`{type, default_binding}` pairs; a nullable `schedule_template`; and a nullable `default_tier`.
The shipped table SHALL contain exactly the `merchant`, `guild_staff`, and `guild_examiner`
professions replicating the component combinations `world/rules/guild_economy.py` assembles
today, each with `schedule_template: null` and `default_tier: null`.

#### Scenario: The shipped table loads and exposes the three replica professions
- **WHEN** the professions rulebook is loaded
- **THEN** `get_profession("merchant")` carries one `merchant` component and
  `get_profession("guild_staff")` / `get_profession("guild_examiner")` carry the component sets
  the guild-economy sync attaches today, and every row's `schedule_template` and `default_tier`
  are null

#### Scenario: Keyed reads never mutate the table
- **WHEN** a consumer calls `get_profession` twice for one key
- **THEN** both calls return equal frozen values and no mutation of the cached table is possible

### Requirement: Every malformed profession file is rejected by name before anything is cached
`profession_config.py` SHALL validate the whole file batch-first and raise `ProfessionConfigError`
with a message naming the offense — and cache nothing — for each of: missing or wrong
`schema_version`; missing `professions:` list; unknown top-level key; empty or duplicate
profession `key`; a `components:` entry whose `type` is not in the component-type vocabulary; a
`default_binding` outside `person|place`; a `schedule_template` that is neither null nor a key of
the loaded schedule-template rulebook; and a `default_tier` that is neither null nor a key of the
static-tier registry.

#### Scenario: An unknown component type names the offender
- **WHEN** a profession file declares `type: blacksmith` with no such component class
- **THEN** loading raises `ProfessionConfigError` naming the profession key and the unknown type,
  and `get_profession` serves no partially-loaded table

#### Scenario: A schedule template that does not exist is rejected
- **WHEN** a row sets `schedule_template: night_shift` and no such template key exists in the
  schedule rulebook
- **THEN** loading raises naming the row and the unknown template key

#### Scenario: A tier outside the static-tier registry is rejected
- **WHEN** a row sets `default_tier: mythic` and `STATIC_TIER_REGISTRY` has no `mythic` key
- **THEN** loading raises naming the row and the unknown tier key

### Requirement: default_binding is a validated vocabulary stored for later consumers
Each component entry's `default_binding` SHALL be one of `person` or `place`, validated at load;
the value SHALL be stored on the frozen component row and SHALL NOT be read by any runtime gate,
component, or presentation surface until the service-anchoring change consumes it.

#### Scenario: Binding vocabulary is enforced at load
- **WHEN** a row declares `default_binding: portable`
- **THEN** loading raises naming the row and the invalid binding value

#### Scenario: Nothing reads the binding yet
- **WHEN** the repository is searched for consumers of `ProfessionComponent.default_binding`
- **THEN** the only readers are the profession loader itself and its tests

### Requirement: The component-type vocabulary is contract-pinned to the component classes
The profession loader SHALL define a closed mapping from component `type` strings to the
component classes declared in `typeclasses/components.py`, and a contract test SHALL fail when a
component class exists in that module without a vocabulary entry or a vocabulary entry names no
existing component class.

#### Scenario: A new component class without a vocabulary entry fails the contract
- **WHEN** a new component class is added to `typeclasses/components.py` and the vocabulary lacks
  its snake-case type key
- **THEN** the contract test fails naming the unmapped class
