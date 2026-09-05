## Purpose

The `context_actions` panel contract at schema version 5: the available combat form (preserving
the exact version-4 field contract owned by `webclient-combat-menu`), the available exploration
form carrying the canonical affordance vocabulary (`exploration-affordances`) plus the
state-backed `suggestions` envelope (`webclient-context-actions-suggestions`), and the shared
unavailable form whose field set is unchanged across versions and which carries no `suggestions`.

## Requirements

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
validator, and the production client mirror SHALL enforce the same contract. Affordance
`params` validation SHALL be a total function over the shared vocabulary's
`ACTION_CODE_ALLOWLIST`: every code the vocabulary may emit SHALL have a registered payload
validator (pinned by a test that the registered-key set covers the allowlist), and an
unregistered code SHALL produce a structured protocol rejection naming the code — never a Python
`KeyError` escaping into a calling presenter or suggestion validator. The presenter SHALL be
read-only: it SHALL NOT mutate traits, resources, buffs, sexual state, battlefield, session,
quest, location, party, or world time, and SHALL emit no live object or filesystem reference.

#### Scenario: One available form per mode with suggestions
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot, and again when the
  same actor is inside an active combat session
- **THEN** the first `context_actions` payload is the exploration available form and the second is
  the combat available form, each schema-valid at version 5, each carrying exactly its
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

#### Scenario: A possession affordance validates instead of raising
- **WHEN** a bound companion in the room puts an `explore.possess` or `explore.possess_release`
  affordance into the exploration form, or a suggestion card proposes one
- **THEN** params validation runs the registered possession validator (accepting the canonical
  shape, rejecting anything else structurally) and the panel/suggestion path never raises a
  Python error

### Requirement: The exploration context form enumerates the complete canonical affordance list
The exploration available form's `affordances` SHALL be a bounded list of exactly the
`AffordanceView` objects produced by the shared vocabulary (`exploration-affordances`) in
vocabulary order: at most `MAX_CONTEXT_AFFORDANCES` (320) entries — a bound derived from the
shared v1 caps (≤ 32 interact targets × ≤ 8 affordances per target, ≤ 16 scripted keywords per
host, ≤ 12 exits, ≤ 32 look objects, ≤ 2 baseline, ≤ 2 navigation), so a legal room can never
truncate the list (asserted by a maximal-fixture test). Each action entry SHALL carry `action_id`
in `ACTION_CODE_ALLOWLIST` (no fabricated or `explore.interact` code), a bounded safe `label`,
the validator-normalized `params` (or the freeform binding shape), exact `freeform` and
`navigation` booleans, exact `enabled`, and `disabled_reason` null or an exact object with stable
code and safe Traditional Chinese message. Each navigation entry SHALL carry `surface`
(`"guild"` or `"shop"`), a bounded safe `label`, `navigation` true, exact `enabled`,
`disabled_reason`, and no `action_id`/`params`, and SHALL never be dispatched as a `ui_action`.
The form SHALL fail closed over the OOB envelope byte limit exactly like the version-1
exploration panel: the entry-count bound is a ceiling, not a guarantee that any content fits, so
a form whose canonical serialization exceeds `MAX_CANONICAL_JSON_BYTES` SHALL be rejected by the
server validator rather than emitted. The client's global envelope gate (list-item ceiling) SHALL
clear the maximal affordance list so a large room's form is never rejected before panel
validation. The production client mirror's action-code enumerations (context-action codes,
exploration action ids) and its affordance `params` validation branches SHALL stay in lockstep
with the server vocabulary. `CONTEXT_ACTIONS_ACTION_CODES` is the full 10-code sequence and
SHALL contain every code in `ACTION_CODE_ALLOWLIST`. `EXPLORATION_ACTION_IDS` is intentionally
the target-scoped subset (affordances that require an NPC target identity) — `explore.move`,
`explore.look`, and `explore.wait` are intentionally absent because they are never emitted as
per-target affordances; adding `explore.possess` and `explore.possess_release` brings this list
to seven entries. Every code in each enumeration SHALL have a params branch accepting exactly the
server validator's accepted shape and rejecting everything else; the parity SHALL be pinned by
dependency-free Node test fixtures carrying the server's authoritative code lists and accept/reject
params vectors.

#### Scenario: The context form mirrors the vocabulary exactly
- **WHEN** the exploration form is rendered for a fixture room
- **THEN** its `affordances` equals the vocabulary's `AffordanceView` list for that room (same
  entries, order, ids, labels, params, flags, enabled states, and disabled reasons), and both the
  server validator and the client mirror accept it

#### Scenario: A maximal legal room serializes untruncated
- **WHEN** a fixture room reaches the shared caps (32 targets with full keyword lists, 12 exits,
  32 objects, baseline, navigation)
- **THEN** the exploration form contains every vocabulary entry, passes the server validator, and
  is accepted by the client mirror without truncation

#### Scenario: The client mirror accepts the possession codes
- **WHEN** a version-5 exploration fixture carries an `explore.possess` entry with canonical
  params and an `explore.possess_release` entry with canonical params (both codes carry exactly
  the server validator's accepted `npc_id` shape)
- **THEN** the client mirror's enumeration and params validation accept both, and reject mutated
  params (missing or extra keys, wrong kinds, out-of-range ids) exactly as the server validator
  does
