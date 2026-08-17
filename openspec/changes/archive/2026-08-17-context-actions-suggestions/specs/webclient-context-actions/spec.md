## MODIFIED Requirements

### Requirement: context_actions is an exact read-only version-5 panel

The production presentation registry SHALL register panel name `context_actions` at schema
version 5. The panel SHALL expose exactly one available form per mode and the registered common
unavailable form otherwise:

- In a valid active combat session the available payload SHALL contain exactly `schema_version`,
  `available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, `skills`,
  and `suggestions`, with `available` true, `kind` `"combat"`, and `suggestions` exactly
  `{"status": "unavailable"}` — the version-3 field contract for the combat fields themselves is
  preserved (the `webclient-combat-menu` capability owns the combat-field details).
- In exploration mode the available payload SHALL contain exactly `schema_version`, `available`,
  `kind`, `affordances`, and `suggestions`, with `available` true, `kind` `"exploration"`,
  `affordances` following the exploration-affordances capability contract, and `suggestions`
  following the `webclient-context-actions-suggestions` capability contract (state-backed
  per-status envelope). The version-4 prohibition on a `suggestions` section in the exploration
  form is removed.
- Outside both modes (creation-pending, absent location, unknown) the panel SHALL use the
  registered common unavailable form with its stable code and safe Traditional Chinese message.
  The unavailable form's exact field set SHALL remain `schema_version`, `available`, and `reason`
  — it SHALL NOT carry `suggestions` — and its `schema_version` SHALL equal the panel version (5)
  like every other form.

Every validation SHALL be server-side with a strict closed schema: unknown keys, wrong kinds,
unpresent fields, underepresent fields, and out-of-bound values SHALL be rejected by the server
validator, and the production client mirror SHALL enforce the same contract. The presenter SHALL
be read-only: it SHALL NOT mutate traits, resources, buffs, sexual state, battlefield, session,
quest, location, party, or world time, and SHALL emit no live object or filesystem reference.

#### Scenario: One available form per mode with suggestions
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot, and again when the
  same actor is inside an active combat session
- **THEN** the first `context_actions` payload is the exploration available form and the second
  is the combat available form, each schema-valid at version 5, each carrying exactly its
  `suggestions` envelope, with no cross-form fields

#### Scenario: The unavailable form differs only in schema version
- **WHEN** the active puppet is creation-pending or has no location
- **THEN** `context_actions` reports its registered unavailable form with the same field set,
  reason, and semantics as the version-4 form, its `schema_version` equals 5, and no
  affordance, session, participant, skill, or suggestions data is present

#### Scenario: The exploration form no longer forbids suggestions
- **WHEN** the exploration available form is validated at version 5 with a valid `suggestions`
  envelope and without one
- **THEN** both payloads are accepted — the former version-4 "SHALL NOT contain a suggestions
  section" constraint is gone — and the `affordances` vocabulary contract is unchanged

#### Scenario: The combat form is byte-identical to version 4 plus suggestions
- **WHEN** a v4-compatible combat fixture is validated by the version-5 validator (and by the
  client mirror)
- **THEN** every combat field serializes exactly as it did at schema version 4, with only
  `schema_version` equal to 5 and the `suggestions` object `{"status": "unavailable"}` added