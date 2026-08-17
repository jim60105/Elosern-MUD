## Purpose

The v5 `context_actions` panel's `suggestions` envelope contract: the per-status closed schema on
both available forms, the bounded card vocabulary (known-action and freeform), the state-backed
exploration presenter reading an immutable session snapshot, and the client mirror with the
repository-wide parity contract. The write side (trigger service) is a later change; this
capability pins the read-side contract.

## Requirements

### Requirement: The context_actions panel carries a suggestions envelope at version 5

The production presentation registry SHALL register `context_actions` at schema version 5. Every
available form (combat and exploration) SHALL contain exactly the version-5 field set of its kind
plus a `suggestions` object; the registered common unavailable form SHALL keep its exact field
set, reason, and semantics with `schema_version` equal to 5. The `suggestions` object SHALL
contain exactly `status` and, present exactly when `status` is `ready` or `degraded`, `cards`:
`status` SHALL be one of `"generating"`, `"ready"`, `"degraded"`, or `"unavailable"`, `cards`
SHALL be present iff `status` is `ready` or `degraded`, and server validation SHALL reject
unknown statuses, missing or extra fields, and cards under `generating`/`unavailable`. The combat
form SHALL emit exactly `{"status": "unavailable"}` and SHALL NOT consult suggestion state. The
presenter SHALL be read-only: it SHALL NOT mutate traits, resources, buffs, sexual state,
battlefield, session, quest, location, party, or world time, and SHALL emit no live object or
filesystem reference.

#### Scenario: Combat reports suggestions unavailable
- **WHEN** a puppeted WebClient in an active combat session receives a full snapshot at version 5
- **THEN** the combat form carries the exact `suggestions` object `{"status": "unavailable"}` while every combat field serializes identically to the version-4 form

#### Scenario: The unavailable form carries no suggestions
- **WHEN** the active puppet is creation-pending or has no location
- **THEN** `context_actions` uses the common unavailable form whose field set and reason are identical to the version-4 form, whose `schema_version` equals 5, and which contains no `suggestions` object

#### Scenario: A generating state carries no cards
- **WHEN** the exploration snapshot reports `status` `"generating"`
- **THEN** the exploration form's `suggestions` is exactly `{"status": "generating"}` and rejected by validation the moment a `cards` field appears

#### Scenario: The common unavailable form rejects suggestions
- **WHEN** a non-available `context_actions` payload at version 5 carries a `suggestions` field
- **THEN** the common-unavailable-form validation (registry + client mirror) rejects it — the field set stays exactly `schema_version`, `available`, `reason` — and a synchronous per-panel test asserts the shared unavailable builder was not altered

### Requirement: Suggestion cards are a bounded closed exact shape

Every `suggestions.cards` entry SHALL contain exactly `kind`, `action_code`, `label`, `params`,
and optionally `hint`. `kind` SHALL be `"known_action"` or `"freeform"`; `action_code` SHALL be a
stable identifier in `ACTION_CODE_ALLOWLIST`, and for `freeform` cards SHALL be exactly
`"explore.talk_freeform"`; `label` SHALL contain at least one CJK code point and SHALL be 1..24
code points; optional `hint` SHALL be at most 60 code points. For `known_action` cards `params`
SHALL be exactly the matching canonical `AffordanceView` entry's validator-normalized payload —
an object with one to four keys whose values are safe integers, bounded strings, or the literal
boolean `true` for the `explore.look` room-survey form (`{"room": true}`); any other boolean
value SHALL be rejected. For `freeform` cards `params` SHALL be exactly `{"npc_id": <positive
int>}`. Card counts SHALL follow status: `ready` sets SHALL contain 3..5 cards and `degraded`
sets SHALL contain 0..5 cards; the server validator and the client mirror SHALL enforce the same
bounds. Validation SHALL reject unknown keys, unknown action codes, wrong `freeform` payload
shapes, out-of-bound labels, hints, params, and counts.

#### Scenario: A ready set is bounded to three to five exact cards
- **WHEN** a snapshot `ready` set contains two or six validated cards
- **THEN** the server validator rejects the payload and the client mirror rejects it identically

#### Scenario: A degraded set may be empty
- **WHEN** a `degraded` suggestions object carries zero cards
- **THEN** both validators accept it (the guarantee that a v1 room never reaches zero is a producer property, not a validator rule)

#### Scenario: Freeform cards bind one present NPC only
- **WHEN** a `freeform` card's `params` is not exactly `{"npc_id": <positive int>}` or its `action_code` is not `"explore.talk_freeform"`
- **THEN** server and mirror reject the card

#### Scenario: The room-survey param shape is accepted
- **WHEN** a `known_action` card carries the canonical `explore.look` room-survey params `{"room": true}`
- **THEN** both validators accept it, and any other boolean value anywhere in `params` is rejected

### Requirement: Exploration suggestions render from an immutable session snapshot

The exploration available form's `suggestions` SHALL be assembled only from
`context.options_state` — an immutable `OptionsSnapshot` — and from the deterministic
`default_cards()` derivation over the **same fresh affordance tuple just serialized into the
form** (one build, two consumers; the affordance-contract change defines `default_cards(affordances, ...)`).
The presenter SHALL NOT read the raw session, generation-side metadata, or any transport
artifact. The `OptionsSnapshot` SHALL be created by the ingress/coordinator from
`session.ndb.options_state` through a factory that deep-copies the displayed cards into
immutable card representations (frozen, no shared mutable dicts), so repeated renders of one
snapshot are stable even if the async writer later replaces the session state object. When the
snapshot is absent or its status is `"unavailable"`, the form SHALL emit `status: "unavailable"`;
`"generating"` SHALL emit the status alone; `"ready"` SHALL emit exactly the snapshot's
`displayed` cards; `"degraded"` SHALL emit `default_cards(affordances)` as its cards. A `ready`
snapshot whose `displayed` set is missing or fails the v5 shape gate SHALL emit `"unavailable"`
with a bounded diagnostic log and SHALL NOT fabricate cards. A `degraded` derivation whose cards
fail the v5 shape gate (the vocabulary bounds display names at 128 code points without a CJK
requirement, while suggestion labels are 1..24 CJK code points) SHALL likewise emit
`"unavailable"` with a bounded diagnostic log — the panel SHALL stay available and no
shape-invalid card SHALL reach the wire. Contexts built without snapshot state (default `None`)
SHALL behave exactly as before.

#### Scenario: A ready display survives later re-renders
- **WHEN** a session's snapshot reports `ready` and repeated snapshots and updates are rendered
- **THEN** the exploration form renders the same displayed cards at each render and never consults `default_cards()` or generation metadata

#### Scenario: An absent snapshot is inert
- **WHEN** no snapshot exists for the session (the trigger service has not populated state)
- **THEN** the exploration form emits `status: "unavailable"` and the panel remains schema-valid at version 5

#### Scenario: A corrupted ready snapshot cannot fabricate cards
- **WHEN** a snapshot reports `ready` but its `displayed` set is missing or fails validation
- **THEN** the presenter emits `{"status": "unavailable"}` and a bounded diagnostic log entry, and no card is emitted

#### Scenario: One affordance build feeds both the form and the fallback
- **WHEN** the exploration form is rendered with a `degraded` status
- **THEN** the `affordances` list in the payload and the input to `default_cards(affordances)` are the identical tuple, so the subset contract (`degraded` cards ⊆ current affordances) holds by construction

#### Scenario: A shape-invalid degraded derivation fails closed to unavailable
- **WHEN** the exploration form is rendered with a `degraded` status and the derived rule cards fail the v5 shape gate (for example an ASCII or over-24-code-point display name, which the affordance vocabulary bounds at 128 code points without a CJK requirement)
- **THEN** the presenter emits `{"status": "unavailable"}` with a bounded diagnostic log, the panel stays available and schema-valid at version 5, and no shape-invalid card reaches the wire

### Requirement: The v5 client mirror and parity contract enforce the suggestions shape

`web/static/webclient/js/elosern/protocol.js` SHALL register `context_actions` at version 5 in
`PANEL_ALLOWLIST` and SHALL validate every v5 form — unavailable, combat, and exploration — with
the same exact-field, status, card-shape, and count bounds as the server validator. A payload at
any other version SHALL be rejected per the registered-version contract. The repository-wide
parity contract SHALL assert numerically identical Python/JS bounds and shared enum fragments for
the suggestions section.

#### Scenario: A version-4 payload is rejected by the mirror
- **WHEN** the browser receives a schema-valid-at-4 `context_actions` payload without `suggestions`
- **THEN** the client mirror rejects it and the existing recovery/sync discipline applies

#### Scenario: Python and JS bounds never diverge
- **WHEN** the parity contract test runs
- **THEN** every `OPTIONS_*` constant pair and every status/kind/action-code fragment matches between `combat_panel.py`/`affordances.py` and `protocol.js`
