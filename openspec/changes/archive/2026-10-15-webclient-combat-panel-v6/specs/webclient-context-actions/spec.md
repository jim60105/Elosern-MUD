## RENAMED Requirements

- FROM: `### Requirement: context_actions is an exact read-only version-5 panel`
- TO: `### Requirement: context_actions is an exact read-only version-6 panel`

## MODIFIED Requirements

### Requirement: context_actions is an exact read-only version-6 panel
The production presentation registry SHALL register panel name `context_actions` at schema
version 6. The panel SHALL expose exactly one available form per mode and the registered common
unavailable form otherwise. The presenter SHALL be read-only: it SHALL NOT mutate traits,
resources, buffs, sexual state, battlefield, session, quest, location, party, or world time, and
SHALL emit no live object or filesystem reference.

#### Scenario: One available form per mode with suggestions
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot, and again when the
  same actor is inside an active combat session
- **THEN** the first `context_actions` payload is the exploration available form and the second is
  the combat available form, each schema-valid at version 6, each carrying exactly its
  `suggestions` envelope, with no cross-form fields

#### Scenario: The unavailable form differs only in schema version
- **WHEN** the active puppet is creation-pending or has no location
- **THEN** `context_actions` reports its registered unavailable form with the same field set,
  reason, and semantics as the version-4 form, its `schema_version` equals 6, and no
  affordance, session, participant, skill, or suggestions data is present

#### Scenario: The exploration form no longer forbids suggestions
- **WHEN** the exploration available form is validated at version 6 with a valid `suggestions`
  envelope and without one
- **THEN** both payloads are accepted — the former version-4 "SHALL NOT contain a suggestions
  section" constraint is gone — and the `affordances` vocabulary contract is unchanged

#### Scenario: The combat form is byte-identical to version 4 plus suggestions
- **WHEN** a combat fixture is validated by the version-6 validator (and by the client mirror)
- **THEN** every combat field serializes exactly as it did at schema version 4, except that
  `schema_version` equals 6, the `suggestions` object `{"status": "unavailable"}` is added (version
  5), and each participant's `conditions` and each skill's `hostile` and `beneficial` are added
  (version 6, owned by `webclient-combat-menu`)

#### Scenario: A possession affordance validates instead of raising
- **WHEN** a bound companion in the room puts an `explore.possess` or `explore.possess_release`
  affordance into the exploration form, or a suggestion card proposes one
- **THEN** params validation runs the registered possession validator (accepting the canonical
  shape, rejecting anything else structurally) and the panel/suggestion path never raises a
  Python error

#### Scenario: The combat available form carries the version-5 field set
- **WHEN** a valid active combat session renders the available payload
- **THEN** it SHALL contain exactly `schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`, `secondary_actions`, `skills`, and `suggestions`, with `available` true, `kind` `"combat"`, and `suggestions` exactly `{"status": "unavailable"}` — the version-3 field contract for the combat fields themselves is preserved (the `webclient-combat-menu` capability owns the combat-field details)

#### Scenario: The exploration available form carries suggestions
- **WHEN** exploration mode renders the available payload
- **THEN** it SHALL contain exactly `schema_version`, `available`, `kind`, `affordances`, and `suggestions`, with `available` true, `kind` `"exploration"`, `affordances` following the exploration-affordances capability contract, and `suggestions` following the `webclient-context-actions-suggestions` capability contract (state-backed per-status envelope); the version-4 prohibition on a `suggestions` section in the exploration form is removed

#### Scenario: Outside both modes the common unavailable form is used
- **WHEN** the mode is creation-pending, absent location, or unknown
- **THEN** the panel SHALL use the registered common unavailable form with its stable code and safe Traditional Chinese message

#### Scenario: The unavailable form field set stays exact at version 5
- **WHEN** the unavailable form is serialized
- **THEN** its exact field set SHALL remain `schema_version`, `available`, and `reason` — it SHALL NOT carry `suggestions` — and its `schema_version` SHALL equal the panel version (6) like every other form

#### Scenario: Every validation is server-side with a strict closed schema
- **WHEN** a candidate payload carries unknown keys, wrong kinds, unpresent fields, underepresent fields, or out-of-bound values
- **THEN** the server validator SHALL reject it, and the production client mirror SHALL enforce the same contract

#### Scenario: Affordance params validation is a total function over the allowlist
- **WHEN** affordance `params` validation runs over the shared vocabulary's `ACTION_CODE_ALLOWLIST`
- **THEN** every code the vocabulary may emit SHALL have a registered payload validator (pinned by a test that the registered-key set covers the allowlist), and an unregistered code SHALL produce a structured protocol rejection naming the code — never a Python `KeyError` escaping into a calling presenter or suggestion validator
