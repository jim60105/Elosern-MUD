## ADDED Requirements

### Requirement: Creation race display names travel with opaque keys
The creation panel SHALL use schema version 6. Each custom.races option SHALL contain exactly key, display_name_zh, description and subraces, with display_name_zh a non-empty string of at most 128 code points sourced from the race registry. Every preset race key SHALL resolve to one such option. Clients SHALL render that display name in race controls, presets and confirmation while preserving keys in actions.

#### Scenario: Preset and custom agree
- **WHEN** a preset and a custom option use the same race key
- **THEN** both show the supplied registry display name and selection still submits only the original key

#### Scenario: Invalid label is rejected
- **WHEN** a v6 race label is absent/blank/overlong or a preset names an absent race option
- **THEN** both exact validators reject the panel and no raw-key fallback is invented

### Requirement: Creation resource and offense labels are distinguishable
Creation allocation and preview prose SHALL distinguish the mana resource axis from magic offense using canonical localized labels, while preserving all allocation keys, bounds and totals.

#### Scenario: Both axes are present
- **WHEN** a creation profile carries mana and magic offense
- **THEN** their labels are distinguishable and changing either control updates only its existing axis

## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 6. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`.
`schema_version` SHALL be integer 6. The `proposal` key SHALL be present only while the
authenticated session holds a transient concept proposal and SHALL carry exactly the shape defined
by the transient-fill contract (the base `revision`/`race`/`subrace`/`allocations`/`persona` keys
plus the optional `display_name`, `age`, `apparent_age`, `background`, and `affinity_elements`
transient-fill keys); the presenter SHALL render it from an immutable session snapshot copy. The
presenter SHALL derive every finite control and preview from immutable registries and the
deterministic starting-profile resolver, SHALL emit no live object reference and no filesystem
path, and SHALL NOT mutate `creation_pending`, the wizard draft, the session proposal slot, traits,
identity attributes, location, or world time. The whole panel SHALL use the registered common
unavailable form outside `creation` mode and when the global prerequisite fails; a failure confined
to one field, preset, or profile SHALL NOT fabricate a value.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 6, the preset
  cards, the custom-form descriptor, and the current server-persisted draft while a before/after
  comparison of canonical game state is unchanged

#### Scenario: Activated and combat characters do not receive the creation panel
- **WHEN** the active puppet is not creation-pending or is in an active combat session
- **THEN** `creation` uses its schema-valid unavailable form and contains no preset card, field,
  draft, or proposal

#### Scenario: Creation presentation stays read-only
- **WHEN** the creation panel is built for a pending character with a saved draft, a pending session
  proposal, and a disguise-independent empty trait set
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, identity attributes,
  traits, and world time are byte-for-byte unchanged and no skill, equipment, inventory, or
  import-schema field is exposed

#### Scenario: A stale schema version is rejected
- **WHEN** a `creation` panel payload declares `schema_version` 5, 4, 3, 2, or any version other than 6
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

### Requirement: Creation presentation derives finite controls from immutable registries
The `presets` array SHALL contain at most 8 preset cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), and `background` (1..256), derived from `PLAYER_PRESET_REGISTRY` and the race registry rather than duplicated literals. The `custom` object SHALL contain exactly `name`, `age`, `races`, `subraces`, `profiles`, `affinity`, and `sex`. `name` SHALL contain exactly `min_length` 1 and `max_length` 64, mirroring the deterministic display-name bound (the shared entity-key contract). `age` SHALL contain exactly `age_minimum` 0, `age_maximum` 10000, `apparent_age_minimum` 0, and `apparent_age_maximum` 10000. `races` SHALL be a list of at most 8 race options, each with exactly `key` (1..64), `display_name_zh` (non-empty 1..128), `description` (1..512), and `subraces` (a list of subrace keys or a single null). `subraces` SHALL map at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and `specialty`, each 1..256 code points. `profiles` SHALL contain at most 16 entries, one per race/subrace combination, each with exactly `race`, `subrace` (null or a key), `budget`, and `axes`; each axis SHALL contain exactly `axis`, `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum` within JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`. `affinity` SHALL map each race key (`human`, `beastfolk`, `elf`) to exactly `maximum` (integer `2`, `1`, and `0` respectively) and `elements` (exactly the eight lore element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`). `sex` SHALL be a nonempty list of at most 8 sex options in `SEX_VALUES` order, each with exactly `key` (1..64 code points, one of the `SEX_VALUES` members) and `label` (1..64 code points of server-owned Traditional Chinese text derived server-side, never duplicated in the browser), covering every `SEX_VALUES` member exactly once. The `custom` descriptor SHALL NOT contain persona, skill, equipment, inventory, starting-magic, or import-only fields merely because a character-card schema defines them; persona prose values appear only inside `draft.persona` and the transient `proposal` payload, never in control metadata.

Every preset race key SHALL resolve to a custom race option; its display name is reused for preset/confirmation display without changing action keys.

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships for human, beastfolk, and elf
- **THEN** every race option carries its registry display name, description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the age fields advertise a minimum of 0, `name` advertises `min_length` 1 and `max_length` 64, and `affinity` advertises the race-dependent maximum (human 2, beastfolk 1, elf 0) with the eight element choices

#### Scenario: Custom descriptor advertises server-labelled sex options
- **WHEN** the custom descriptor ships for a pending character
- **THEN** `custom.sex` lists every `SEX_VALUES` member exactly once in registry order, each carrying the server-owned Traditional Chinese label (女性 for `female`, 男性 for `male`, 其他 for `other`) with no label literal duplicated in browser code

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field
