## MODIFIED Requirements

### Requirement: The creation panel is an exact read-only creation-mode panel
The production presentation registry SHALL register `creation` schema version 3. Its available
payload SHALL contain exactly `schema_version`, `available`, `kind`, `draft`, `presets`, `custom`,
and the optional `proposal`; `available` SHALL be true and `kind` SHALL be `creation`.
`schema_version` SHALL be integer 3. The `proposal` key SHALL be present only while the
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
- **THEN** `creation` reports `available` true, `kind` `creation`, schema version 3, the preset
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

#### Scenario: A schema version 2 payload is rejected
- **WHEN** a `creation` panel payload declares `schema_version` 2 or any other version
- **THEN** exact-schema validation rejects it on both the presenter and the mirrored browser
  validator rather than accepting a stale shape
