# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The context_actions panel carries a suggestions envelope at version 6`
- TO: `### Requirement: The context_actions panel carries a suggestions envelope at version 7`


- FROM: `### Requirement: The v6 client mirror and parity contract enforce the suggestions shape`
- TO: `### Requirement: The v7 client mirror and parity contract enforce the suggestions shape`


## MODIFIED Requirements

### Requirement: The context_actions panel carries a suggestions envelope at version 7

The production presentation registry SHALL register `context_actions` at schema version 7. The
`suggestions` object SHALL contain exactly `status` and, present exactly when `status` is `ready`
or `degraded`, `cards`. `status` SHALL be one of `"generating"`, `"ready"`, `"degraded"`, or
`"unavailable"`, and `cards` SHALL be present iff `status` is `ready` or `degraded`. Server
validation SHALL reject unknown statuses, missing or extra fields, and cards under
`generating`/`unavailable`.

#### Scenario: Combat reports suggestions unavailable
- **WHEN** a puppeted WebClient in an active combat session receives a full snapshot at version 7
- **THEN** the combat form carries the exact `suggestions` object `{"status": "unavailable"}` while the combat field shape is the v7 party contract owned by webclient-combat-menu

#### Scenario: The unavailable form carries no suggestions
- **WHEN** the active puppet is creation-pending or has no location
- **THEN** `context_actions` uses the common unavailable form whose field set and reason are identical to the version-4 form, whose `schema_version` equals 7, and which contains no `suggestions` object

#### Scenario: A generating state carries no cards
- **WHEN** the exploration snapshot reports `status` `"generating"`
- **THEN** the exploration form's `suggestions` is exactly `{"status": "generating"}` and rejected by validation the moment a `cards` field appears

#### Scenario: The common unavailable form rejects suggestions
- **WHEN** a non-available `context_actions` payload at version 7 carries a `suggestions` field
- **THEN** the common-unavailable-form validation (registry + client mirror) rejects it — the field set stays exactly `schema_version`, `available`, `reason` — and a synchronous per-panel test asserts the shared unavailable builder was not altered

#### Scenario: Available forms carry their version-5 field set plus suggestions
- **WHEN** either available form (combat or exploration) is built at version 7
- **THEN** exploration preserves its exact prior field set and combat follows the exact v7 party field set; each carries its suggestions object

#### Scenario: The common unavailable form keeps its version-4 semantics
- **WHEN** the registered common unavailable form is built at version 7
- **THEN** it keeps its exact field set, reason, and semantics with `schema_version` equal to 6

#### Scenario: Combat never consults suggestion state
- **WHEN** the combat form is rendered
- **THEN** it emits exactly `{"status": "unavailable"}` without consulting suggestion state

#### Scenario: The presenter is read-only
- **WHEN** the suggestions presenter renders any form
- **THEN** it mutates no traits, resources, buffs, sexual state, battlefield, session, quest,
  location, party, or world time, and emits no live object or filesystem reference

### Requirement: The v7 client mirror and parity contract enforce the suggestions shape

`web/static/webclient/js/elosern/protocol.js` SHALL register `context_actions` at version 7 in
`PANEL_ALLOWLIST` and SHALL validate every v7 form — unavailable, combat, and exploration — with
the same exact-field, status, card-shape, and count bounds as the server validator. A payload at
any other version SHALL be rejected per the registered-version contract.

#### Scenario: A version-4 payload is rejected by the mirror
- **WHEN** the browser receives a schema-valid-at-4 `context_actions` payload without `suggestions`
- **THEN** the client mirror rejects it and the existing recovery/sync discipline applies

#### Scenario: Python and JS bounds never diverge
- **WHEN** the parity contract test runs
- **THEN** every `OPTIONS_*` constant pair and every status/kind/action-code fragment matches between `combat_panel.py`/`affordances.py` and `protocol.js`

#### Scenario: The repository-wide parity contract covers suggestions
- **WHEN** the repository-wide parity contract is evaluated
- **THEN** it asserts numerically identical Python/JS bounds and shared enum fragments for the suggestions section

#### Scenario: A version-5 payload is rejected by the mirror
- **WHEN** the browser receives a schema-valid-at-5 `context_actions` payload
- **THEN** the client mirror rejects it and the existing recovery/sync discipline applies

