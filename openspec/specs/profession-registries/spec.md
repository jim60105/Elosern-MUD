# profession-registries Specification

## Purpose

The authored profession table as game data: a validated rulebook registry of
assembly-time NPC blueprints with keyed frozen reads, whose `default_binding`
value is stored here and first read by the service-anchoring gate.

## Requirements

### Requirement: Professions are one validated rulebook table with keyed frozen reads
<!-- This block is written against the text `place-attendant-profession` leaves behind and
     MUST be archived after it. -->
`world/rules/rulebook/professions.yaml` SHALL declare every authored profession as a list under `professions:` with `schema_version: 1`, and `world/rules/profession_config.py` SHALL expose the loaded table as frozen dataclasses through keyed reads (`get_profession(key)` returning the profession or `None`, and `all_professions()`).

#### Scenario: The shipped table loads and exposes the three replica professions
<!-- Scenario name retained verbatim: a MODIFIED block may not rename or drop an existing
     scenario, so this historical title now covers the whole shipped table. -->
- **WHEN** the professions rulebook is loaded
- **THEN** `get_profession("merchant")` carries a `merchant` and a `scripted_dialogue`
  component, `get_profession("guild_staff")` / `get_profession("guild_examiner")` carry the
  component sets the guild-economy sync attaches, `get_profession("quest_issuer")` carries one
  person-bound `quest_issuer` component, `get_profession("attendant")` carries one place-bound
  `scripted_dialogue` component, and every row's `schedule_template` and `default_tier` are null

#### Scenario: Keyed reads never mutate the table
- **WHEN** a consumer calls `get_profession` twice for one key
- **THEN** both calls return equal frozen values and no mutation of the cached table is possible

#### Scenario: Loader follows the guild_config family
- **WHEN** `profession_config.py`'s load and cache code is inspected
- **THEN** it follows the `guild_config.py` load/cache family

#### Scenario: Each row's exact fields
- **WHEN** a profession row is validated at load
- **THEN** it carries exactly: a non-empty unique `key`; a `components:` list of `{type, default_binding}` pairs; a nullable `schedule_template`; and a nullable `default_tier`

#### Scenario: The shipped table's exact membership
- **WHEN** the shipped table is loaded
- **THEN** it contains exactly the `merchant`, `guild_staff`, `guild_examiner`, `quest_issuer` and `attendant` professions, each with `schedule_template: null` and `default_tier: null`

#### Scenario: The merchant blueprint trades and answers
- **WHEN** the `merchant` row is read
- **THEN** it carries a place-bound `merchant` component and a place-bound `scripted_dialogue` component, so every shopkeeper both trades and answers

#### Scenario: The guild_staff blueprint mirrors the synced host tuple
- **WHEN** the `guild_staff` row is read
- **THEN** it mirrors the guild-hall host component tuple that sync attaches

#### Scenario: The guild_examiner blueprint is a prescribed reusable subset
- **WHEN** the `guild_examiner` row is read
- **THEN** it is the prescribed examiner/dialogue blueprint (a reusable subset; sync attaches no examiner-only host today)

#### Scenario: The quest_issuer blueprint may not anchor a roster row
- **WHEN** the `quest_issuer` row is read
- **THEN** it is the person-bound commission blueprint that no roster row may anchor

#### Scenario: The attendant blueprint is talk-only
- **WHEN** the `attendant` row is read
- **THEN** it is the place-bound talk-only blueprint carrying one `scripted_dialogue` component

### Requirement: Every malformed profession file is rejected by name before anything is cached
`profession_config.py` SHALL validate the whole file batch-first and raise `ProfessionConfigError` with a message naming the offense — and cache nothing — for every malformed-file offense enumerated in the scenarios below.

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

#### Scenario: A missing or wrong schema_version is rejected
- **WHEN** a profession file omits `schema_version` or sets it wrong
- **THEN** loading raises `ProfessionConfigError` naming the offense, and nothing is cached

#### Scenario: A missing professions list is rejected
- **WHEN** a profession file has no `professions:` list
- **THEN** loading raises naming the offense, and nothing is cached

#### Scenario: An unknown top-level key is rejected
- **WHEN** a profession file declares a top-level key the schema does not know
- **THEN** loading raises naming the offense, and nothing is cached

#### Scenario: An empty or duplicate profession key is rejected
- **WHEN** a profession file has a row with an empty `key`, or two rows sharing one `key`
- **THEN** loading raises naming the offense, and nothing is cached

#### Scenario: A binding outside the vocabulary is rejected
- **WHEN** a component entry's `default_binding` is outside `person|place`
- **THEN** loading raises naming the offense, and nothing is cached

### Requirement: default_binding is a validated vocabulary consumed by the anchoring gate
Each component entry's `default_binding` SHALL be one of `person` or `place`, validated at load;
the value SHALL be stored on the frozen component row and SHALL be consumed by profession
assembly, which copies it onto every component it creates (see the `service-anchoring`
capability). No runtime service gate SHALL read the profession table directly — gates read the
component's persisted binding.

#### Scenario: Binding vocabulary is enforced at load
- **WHEN** a row declares `default_binding: portable`
- **THEN** loading raises naming the row and the invalid binding value

#### Scenario: Assembly copies the binding onto created components
- **WHEN** assembly creates a component from a row whose `default_binding` is `place`
- **THEN** the created component persists `service_binding` `place` exactly as authored

#### Scenario: Runtime gates never read the profession table
- **WHEN** `service_gate.py` and every rewired service caller are searched for
  `profession_config` imports
- **THEN** none exist; availability comes from persisted component bindings only

### Requirement: The component-type vocabulary is contract-pinned to the component classes
The profession loader SHALL define a closed mapping from component `type` strings to the
component classes declared in `typeclasses/components.py`, and a contract test SHALL fail when a
component class exists in that module without a vocabulary entry or a vocabulary entry names no
existing component class.

#### Scenario: A new component class without a vocabulary entry fails the contract
- **WHEN** a new component class is added to `typeclasses/components.py` and the vocabulary lacks
  its snake-case type key
- **THEN** the contract test fails naming the unmapped class
