# Spec Delta

## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 8. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`, `portrait`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`. The whole
panel SHALL use the registered common unavailable form outside `creation` mode and when the global
prerequisite fails.

#### Scenario: A pending character receives the creation panel
- **WHEN** a puppeted WebClient session with `creation_pending` true receives a full snapshot
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 8, the preset
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
- **WHEN** a `creation` panel payload declares `schema_version` 7, 6, 5, 4, 3, 2, or any version other than 8
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape

#### Scenario: Schema version ships as the integer 6
- **WHEN** an available `creation` panel payload ships
- **THEN** `schema_version` carries the integer 8

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

## ADDED Requirements

### Requirement: Creation portrait state is a closed read-only union
An available creation panel SHALL carry `portrait` with exactly `status` and state-dependent `artwork` or `reason`. Status SHALL be `empty`, `pending`, `ready`, `failed` or `unavailable`, derived from the pending character’s authorized draft-portrait state. Both validators SHALL reject malformed state combinations; presentation SHALL neither enqueue nor establish policy.

#### Scenario: The five states have exact fields
- **WHEN** an available panel serializes portrait state
- **THEN** empty and pending contain only `status`; ready contains exactly `status` and a canonical `artwork`; failed and unavailable contain exactly `status` and `reason`, a nonblank string of at most 512 code points

#### Scenario: Pending and completion are authoritative
- **WHEN** the receipt’s latest job is pending/in progress, then settles successfully or fails
- **THEN** the panel reports pending, then ready with that exact card or failed with the safe server reason; a character without a receipt reports empty

#### Scenario: Reconnect rebuilds state without writes
- **WHEN** the same pending character reconnects or the server reloads with a valid receipt and job/card state
- **THEN** a full snapshot reconstructs the current portrait state, no request is retried, and no policy, receipt, draft, job, card or file is written by presentation

#### Scenario: Invalid state rejects in both validators
- **WHEN** portrait is missing/null, has an unknown status or extra field, ready has missing/malformed artwork, another status includes artwork, or a reason is absent/blank/nontext/overlong where required
- **THEN** both the presenter validator and the mirrored browser validator reject the whole panel

#### Scenario: Portrait publication preserves local form context
- **WHEN** a matching art settlement republishes freshly decoded portrait state with the same saved custom draft contents after the player edits local identity/story/allocation fields
- **THEN** the creation stage, local step and every unsent value stay unchanged despite a new draft object identity, and a nonmatching character/session receives no portrait data

#### Scenario: Real draft changes retain their synchronization
- **WHEN** saved draft contents change, a confirmed reset or correlated save settles, or creation initializes a new actor presentation context
- **THEN** the existing guarded draft synchronization runs for that lifecycle without being triggered by portrait-only results or revisions
