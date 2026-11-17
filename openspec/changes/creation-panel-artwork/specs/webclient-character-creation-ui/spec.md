# Spec Delta

## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 7. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`. The whole
panel SHALL use the registered common unavailable form outside `creation` mode and when the global
prerequisite fails.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 7, the preset
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
- **WHEN** a `creation` panel payload declares `schema_version` 6, 5, 4, 3, 2, or any version other than 7
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

#### Scenario: Schema version ships as the integer 6
- **WHEN** an available `creation` panel payload ships
- **THEN** `schema_version` carries the integer 7

#### Scenario: The proposal key mirrors the transient session proposal
- **WHEN** the authenticated session holds a transient concept proposal
- **THEN** the payload carries the `proposal` key with exactly the shape defined by the
  transient-fill contract — the base `revision`/`race`/`subrace`/`allocations`/`persona` keys plus
  the optional `display_name`, `age`, `apparent_age`, `background`, and `affinity_elements`
  transient-fill keys — and the presenter renders it from an immutable session snapshot copy
- **AND** when the session holds no transient concept proposal, the `proposal` key is absent

#### Scenario: Controls and previews derive from immutable sources
- **WHEN** the presenter builds the panel
- **THEN** every finite control and preview is derived from immutable registries and the
  deterministic starting-profile resolver

#### Scenario: The payload carries no live reference or path
- **WHEN** the presenter emits the `creation` payload
- **THEN** it contains no live object reference and no filesystem path

#### Scenario: Presentation mutates no game state
- **WHEN** the presenter builds and emits the panel
- **THEN** `creation_pending`, the wizard draft, the session proposal slot, traits, identity
  attributes, location, and world time are unchanged

#### Scenario: A partial failure fabricates no value
- **WHEN** a failure is confined to one field, preset, or profile
- **THEN** the panel does not fabricate a value

### Requirement: Creation presentation derives finite controls from immutable registries
The presenter SHALL derive bounded, exact-shape preset cards and custom controls from `PLAYER_PRESET_REGISTRY`, the race registry and the starting-profile resolver, never duplicated literals. Presets SHALL carry `artwork` and custom controls SHALL carry `silhouettes` under the schemas below.

#### Scenario: Preview additions preserve exact control shapes
- **WHEN** finite creation controls are serialized
- **THEN** `presets` contains at most 8 cards, each with exactly `key` (1..64), `display_name` (1..128), `race` (1..64), `race_description` (1..512), nullable `subrace`, `emphasis` (1..256), `background` (1..256), and `artwork`
- **AND** `custom` contains exactly `name`, `age`, `races`, `subraces`, `profiles`, `affinity`, `sex`, and `silhouettes`

#### Scenario: Preset cards render from registry data
- **WHEN** the creation panel ships for a pending character
- **THEN** each preset card names the registry preset key and the registry-derived display name, race, race description, subrace, emphasis, and background with no duplicated string literal

#### Scenario: Custom descriptor carries server-advertised bounds and profiles
- **WHEN** the custom descriptor ships under synthetic race and affinity registries
- **THEN** every race option carries its registry display name, description and subrace list, every (race, subrace) profile carries the exact allocatable axes and budget from `resolve_starting_profile`, the age and name fields retain their schema bounds, and `affinity` advertises each race’s declared maximum and registered element choices

#### Scenario: Custom descriptor advertises server-labelled sex options
- **WHEN** the custom descriptor ships for a pending character
- **THEN** `custom.sex` lists every `SEX_VALUES` member exactly once in registry order, each carrying the server-owned Traditional Chinese label with no label literal duplicated in browser code

#### Scenario: Custom descriptor omits import-only fields
- **WHEN** the custom descriptor is inspected
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-schema field

#### Scenario: The name descriptor mirrors the display-name bound
- **WHEN** the `custom.name` descriptor ships
- **THEN** it contains exactly `min_length` 1 and `max_length` 64, mirroring the deterministic
  display-name bound (the shared entity-key contract)

#### Scenario: The age descriptor carries the exact range bounds
- **WHEN** the `custom.age` descriptor ships
- **THEN** it contains exactly `age_minimum` 0, `age_maximum` 10000, `apparent_age_minimum` 0,
  and `apparent_age_maximum` 10000

#### Scenario: Race options carry their exact fields
- **WHEN** the `custom.races` list ships
- **THEN** it is a list of at most 8 race options, each with exactly `key` (1..64),
  `display_name_zh` (non-empty 1..128), `description` (1..512), and `subraces` (a list of subrace
  keys or a single null)

#### Scenario: The subraces map carries bounded localized fields
- **WHEN** the `custom.subraces` map ships
- **THEN** it maps at most 16 subrace keys to exactly `display_name_zh`, `common_name_zh`, and
  `specialty`, each 1..256 code points

#### Scenario: Profiles carry the exact seven-axis shape
- **WHEN** the `custom.profiles` list ships
- **THEN** it contains at most 16 entries, one per race/subrace combination, each with exactly
  `race`, `subrace` (null or a key), `budget`, and `axes`; each axis contains exactly `axis`,
  `label`, `explanation`, `minimum`, and `maximum`, with `axis` from `hp`, `mp`, `sp`, `atk_phys`,
  `agility`, `defense`, or `magic_power`, integer `budget`/`minimum`/`maximum` within
  JavaScript-safe range, and the seven-axis set matching `resolve_starting_profile`

#### Scenario: The affinity map carries race maxima and element choices
- **WHEN** the `custom.affinity` map ships
- **THEN** it maps each advertised race key to exactly `maximum` (that race’s declared integer bound) and `elements` (the registered element choices, each with `key` and `label`, derived from `ELEMENT_REGISTRY`)

#### Scenario: The sex descriptor lists every server value once
- **WHEN** the `custom.sex` list ships
- **THEN** it is a nonempty list of at most 8 sex options in `SEX_VALUES` order, each with exactly
  `key` (1..64 code points, one of the `SEX_VALUES` members) and `label` (1..64 code points of
  server-owned Traditional Chinese text derived server-side, never duplicated in the browser),
  covering every `SEX_VALUES` member exactly once

#### Scenario: Persona prose never enters control metadata
- **WHEN** the `custom` descriptor ships for a character-card-capable schema
- **THEN** it contains no persona, skill, equipment, inventory, starting-magic, or import-only
  fields merely because a character-card schema defines them, and persona prose values appear only
  inside `draft.persona` and the transient `proposal` payload, never in control metadata

#### Scenario: Preset race keys resolve to custom race options
- **WHEN** a preset card's race key is checked against the custom descriptor
- **THEN** every preset race key resolves to a custom race option and its display name is reused
  for preset/confirmation display without changing action keys

### Requirement: Creation race display names travel with opaque keys
Each custom.races option SHALL contain exactly key, display_name_zh, description and subraces, with display_name_zh a non-empty string of at most 128 code points sourced from the race registry. Every preset race key SHALL resolve to one such option. Clients SHALL render that display name in race controls, presets and confirmation while preserving keys in actions.

#### Scenario: Preset and custom agree
- **WHEN** a preset and a custom option use the same race key
- **THEN** both show the supplied registry display name and selection still submits only the original key

#### Scenario: Invalid label is rejected
- **WHEN** a race label is absent/blank/overlong or a preset names an absent race option
- **THEN** both exact validators reject the panel and no raw-key fallback is invented

## ADDED Requirements

### Requirement: Preset cards carry a server-built artwork descriptor
Every preset card's `artwork` SHALL be one canonical artwork descriptor built by the server from the card's own preset key. It SHALL offer the preset's official default image as its only image attempt when the mounted catalog admits one, and SHALL always carry the built-in alpha terminal. Building it SHALL create no character, gallery record, job or stored file.

#### Scenario: A preset with official artwork offers it
- **WHEN** the panel is built while the mounted catalog admits a default image for a synthetic preset's content reference
- **THEN** that card's descriptor carries exactly one image attempt whose resource origin is `official` and whose URL is the catalog's fingerprinted same-origin URL, plus an alpha terminal

#### Scenario: A preset without official artwork resolves the built-in figure
- **WHEN** the panel is built while the catalog holds nothing for a synthetic preset
- **THEN** that card's descriptor carries no image attempt and no fault, and its terminal is the built-in figure named by the preset's declared fallback key, or by the band rule on the preset's declared sex and apparent age when it declares none

#### Scenario: A preset descriptor claims no generation
- **WHEN** any preset card's descriptor is inspected
- **THEN** its `generation_subject` and `generation_state` are null and its `retention_sources` list is empty

#### Scenario: Building preset artwork writes nothing
- **WHEN** the panel is built for a pending character
- **THEN** the gallery record count, the gallery job count, the character's `portrait_policy` and the art store's file set are unchanged

#### Scenario: A malformed preset descriptor rejects the panel
- **WHEN** a preset card omits `artwork`, carries a null, or carries a descriptor whose resource URL does not name the same-origin art route
- **THEN** both the presenter validator and the mirrored browser validator reject the panel

### Requirement: The custom descriptor carries the silhouette table
`custom.silhouettes` SHALL be a list of 1..16 entries, each with exactly `sex`, `apparent_age_minimum`, `apparent_age_maximum` and `artwork`. For every advertised sex the entries SHALL cover the advertised apparent-age range exactly once, with no gap and no overlap. Each `artwork` SHALL be a canonical descriptor carrying no image attempt and the alpha terminal the built-in band rule resolves for that sex and age range.

#### Scenario: Every sex covers the whole apparent-age range
- **WHEN** the silhouette table ships
- **THEN** for each `custom.sex` key the entries naming it, ordered by `apparent_age_minimum`, start at `custom.age.apparent_age_minimum`, end at `custom.age.apparent_age_maximum`, and each entry starts one above the previous entry's maximum

#### Scenario: An entry resolves the band rule's figure
- **WHEN** a pending character whose sex and apparent age fall inside one entry is later resolved by the built-in fallback resolver with no declared key
- **THEN** the resolver's key equals the key of that entry's alpha terminal

#### Scenario: A silhouette entry offers no image attempt
- **WHEN** any silhouette entry's descriptor is inspected
- **THEN** its `attempts` list is empty, its `generation_subject` and `generation_state` are null, and its terminal kind is the alpha mask

#### Scenario: A malformed table rejects the panel
- **WHEN** the table is empty, exceeds 16 entries, names a sex outside `custom.sex`, leaves a gap or an overlap for a sex, or carries a malformed descriptor
- **THEN** both the presenter validator and the mirrored browser validator reject the panel
