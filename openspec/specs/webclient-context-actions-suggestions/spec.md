## Purpose

The v5 `context_actions` panel's `suggestions` envelope contract: the per-status closed schema on
both available forms, the bounded card vocabulary (known-action and freeform), the state-backed
exploration presenter reading an immutable session snapshot, and the client mirror with the
repository-wide parity contract. The write side (trigger service) is a later change; this
capability pins the read-side contract.

## Requirements

### Requirement: The context_actions panel carries a suggestions envelope at version 5

The production presentation registry SHALL register `context_actions` at schema version 5. The
`suggestions` object SHALL contain exactly `status` and, present exactly when `status` is `ready`
or `degraded`, `cards`. `status` SHALL be one of `"generating"`, `"ready"`, `"degraded"`, or
`"unavailable"`, and `cards` SHALL be present iff `status` is `ready` or `degraded`. Server
validation SHALL reject unknown statuses, missing or extra fields, and cards under
`generating`/`unavailable`.

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

#### Scenario: Available forms carry their version-5 field set plus suggestions
- **WHEN** either available form (combat or exploration) is built at version 5
- **THEN** it contains exactly the version-5 field set of its kind plus a `suggestions` object

#### Scenario: The common unavailable form keeps its version-4 semantics
- **WHEN** the registered common unavailable form is built at version 5
- **THEN** it keeps its exact field set, reason, and semantics with `schema_version` equal to 5

#### Scenario: Combat never consults suggestion state
- **WHEN** the combat form is rendered
- **THEN** it emits exactly `{"status": "unavailable"}` without consulting suggestion state

#### Scenario: The presenter is read-only
- **WHEN** the suggestions presenter renders any form
- **THEN** it mutates no traits, resources, buffs, sexual state, battlefield, session, quest,
  location, party, or world time, and emits no live object or filesystem reference

### Requirement: Suggestion cards are a bounded closed exact shape

Every `suggestions.cards` entry SHALL contain exactly `kind`, `action_code`, `label`, `params`,
and optionally `hint`. `kind` SHALL be `"known_action"` or `"freeform"`. `label` SHALL contain at
least one CJK code point and SHALL be 1..24 code points; optional `hint` SHALL be at most 60 code
points. Card counts SHALL follow status: `ready` sets SHALL contain 3..5 cards and `degraded` sets
SHALL contain 0..5 cards.

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

#### Scenario: Action codes are allowlist-bound
- **WHEN** a card is validated
- **THEN** its `action_code` is a stable identifier in `ACTION_CODE_ALLOWLIST`, and a `freeform` card's `action_code` is exactly `"explore.talk_freeform"`

#### Scenario: Known-action params mirror the canonical affordance payload
- **WHEN** a `known_action` card is validated
- **THEN** its `params` must be exactly the matching canonical `AffordanceView` entry's validator-normalized payload — an object with one to four keys whose values are safe integers, bounded strings, or the literal boolean `true` for the `explore.look` room-survey form (`{"room": true}`) — and any other boolean value is rejected

#### Scenario: Both validators enforce the same bounds
- **WHEN** any card set is validated
- **THEN** the server validator and the client mirror enforce the same bounds

#### Scenario: Malformed card content is rejected
- **WHEN** a payload carries unknown keys, unknown action codes, wrong `freeform` payload shapes, or out-of-bound labels, hints, params, or counts
- **THEN** validation rejects it

### Requirement: Exploration suggestions render from an immutable session snapshot

The exploration available form's `suggestions` SHALL be assembled only from
`context.options_state` — an immutable `OptionsSnapshot` — and from the deterministic
`default_cards()` derivation over the **same fresh affordance tuple just serialized into the
form**. The presenter SHALL NOT read the raw session, generation-side metadata, or any transport
artifact. A freshness gate over the snapshot's situation fingerprint decides what each status
emits.

#### Scenario: A ready display survives later re-renders in the same situation
- **WHEN** a session's snapshot reports `ready`, its fingerprint equals the current fingerprint,
  and repeated snapshots and updates are rendered
- **THEN** the exploration form renders the same displayed cards at each render and never consults
  `default_cards()` or generation metadata

#### Scenario: An absent snapshot is inert
- **WHEN** no snapshot exists for the session (the trigger service has not populated state)
- **THEN** the exploration form emits `status: "unavailable"` and the panel remains schema-valid at version 5

#### Scenario: A stale ready snapshot is unavailable
- **WHEN** a snapshot reports `ready` but its fingerprint differs from the actor's current
  exploration situation after combat or relocation
- **THEN** the presenter emits `{"status": "unavailable"}` with a bounded diagnostic, emits no
  stale displayed card, and leaves scheduling to the lifecycle trigger

#### Scenario: A corrupted ready snapshot cannot fabricate cards
- **WHEN** a current snapshot reports `ready` but its `displayed` set is missing or fails validation
- **THEN** the presenter emits `{"status": "unavailable"}` and a bounded diagnostic log entry, and no card is emitted

#### Scenario: One affordance build feeds both the form and the fallback
- **WHEN** the exploration form is rendered with a current `degraded` status
- **THEN** the `affordances` list in the payload and the input to `default_cards(affordances)` are the identical tuple, so the subset contract (`degraded` cards ⊆ current affordances) holds by construction

#### Scenario: A shape-invalid degraded derivation fails closed to unavailable
- **WHEN** the exploration form is rendered with a current `degraded` status and the derived rule cards fail the v5 shape gate (for example an ASCII or over-24-code-point display name, which the affordance vocabulary bounds at 128 code points without a CJK requirement)
- **THEN** the presenter emits `{"status": "unavailable"}` with a bounded diagnostic log, the panel stays available and schema-valid at version 5, and no shape-invalid card reaches the wire

#### Scenario: The snapshot factory deep-copies into immutable cards
- **WHEN** the ingress/coordinator creates the `OptionsSnapshot` from `session.ndb.options_state`
- **THEN** the factory deep-copies the displayed cards into immutable card representations (frozen, no shared mutable dicts), so repeated renders of one snapshot are stable even if the async writer later replaces the session state object

#### Scenario: The presentation-context factory carries the fingerprint
- **WHEN** the shared presentation-context factory builds a context
- **THEN** it additionally carries the current read-only exploration situation fingerprint

#### Scenario: The unavailable gate
- **WHEN** the snapshot is absent, its status is `"unavailable"`, the current fingerprint is absent, or a non-unavailable snapshot's fingerprint differs from the current fingerprint
- **THEN** the form emits `status: "unavailable"`

#### Scenario: Each current status emits its defined payload
- **WHEN** the snapshot reports a status with a current fingerprint
- **THEN** `"generating"` emits the status alone only when its fingerprint is current, `"ready"` emits exactly the current snapshot's `displayed` cards, and `"degraded"` emits `default_cards(affordances)` only when its fingerprint is current

#### Scenario: The affordance-contract change defines the derivation entry point
- **WHEN** the degraded fallback needs the derivation
- **THEN** it is the affordance-contract change's `default_cards(affordances, ...)`, one build consumed by both the form and the fallback

#### Scenario: Snapshot-less contexts are unchanged
- **WHEN** contexts are built without snapshot state (default `None`)
- **THEN** they behave exactly as before

#### Scenario: The freshness gate mutates nothing
- **WHEN** the freshness gate evaluates a snapshot
- **THEN** it is read-only and does not schedule, evict, or mutate state

### Requirement: The v5 client mirror and parity contract enforce the suggestions shape

`web/static/webclient/js/elosern/protocol.js` SHALL register `context_actions` at version 5 in
`PANEL_ALLOWLIST` and SHALL validate every v5 form — unavailable, combat, and exploration — with
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

### Requirement: The dock suggestion pane is the single suggestion surface
The action dock's 建議 pane SHALL be the only surface rendering `suggestions.cards`, and its
presentation SHALL follow the committed `suggestions.status` exactly, per the status scenarios
below. The narrative stream SHALL render no suggestion line, card group, or stream-end block
under any status, including a ready group followed by appended narrative.

#### Scenario: Generating then ready replaces in place inside the pane
- **WHEN** the trigger service publishes `suggestions.status = "generating"` and a later commit
  reports `ready` with 3–5 cards
- **THEN** the pane shows the muted generating state first and then exactly one card group with
  no duplicated or stacked cards, and the narrative stream shows no suggestion content

#### Scenario: The narrative stream never carries suggestion cards
- **WHEN** a `ready` card group is committed while narrative lines continue to append
- **THEN** no card, generating line, or stream-end block appears anywhere outside the dock pane

#### Scenario: A pane card dispatches the shared contract
- **WHEN** the player activates a `ready` card in the pane
- **THEN** the dispatch is the shared dock card's `ui_action` envelope for that card, and a
  `freeform` card dispatches `explore.talk_freeform` with `speech: label` and exactly one echo

#### Scenario: Degraded rule cards appear only in the pane
- **WHEN** the AI service is offline and the committed status is `degraded`
- **THEN** the pane shows the rule cards with the muted note and no suggestion content renders
  anywhere else

#### Scenario: Dismiss keeps the committed-state invariant
- **WHEN** the player activates `✕ 清除建議` while a mutation is in flight or the request is
  rejected as stale/busy
- **THEN** no `options.dismiss` is admitted and the pane remains exactly as last committed;
  only the next accepted commit decides removal

#### Scenario: Transport reset retires the card presentation
- **WHEN** the browser begins a new transport generation while a `ready` group is displayed
- **THEN** the retired epoch's cards stop being clickable within that same store notification,
  and a later commit presents fresh cards only from the new epoch's snapshot

#### Scenario: Generating renders the muted state in the pane
- **WHEN** the committed status is `generating`
- **THEN** the pane renders the muted `AI 正在構思建議…` state without cards

#### Scenario: Ready replaces the muted state in place through the shared component
- **WHEN** the committed status becomes `ready`
- **THEN** the committed card group replaces the muted state in place, rendered through the shared dock card component (label, optional hint, action-code semantics, digit-key pick affordance, and the draft's card styling)

#### Scenario: Degraded renders rule cards with the note
- **WHEN** the committed status is `degraded`
- **THEN** the pane renders the derived rule cards with the muted unavailable-AI note

#### Scenario: Non-ready states and off-contract panels render no cards
- **WHEN** the status is `unavailable`, or the panel's kind is not exploration, or the panel is absent, or the suggestions section is out of contract
- **THEN** the pane renders no cards

#### Scenario: Pane cards dispatch the shared component's envelope
- **WHEN** a pane card is activated
- **THEN** the dispatch is exactly the `ui_action` envelope the shared dock card component dispatches (`action_code` + params for `known_action`; `explore.talk_freeform` with `speech: label` for `freeform`), with the existing rejection/stale/busy toast surface and the existing input-line echo behavior applying unchanged

#### Scenario: The pane carries dismiss and the chip names the count
- **WHEN** the pane is presented and the scene overview's 建議 footer chip is rendered
- **THEN** the pane carries the `✕ 清除建議` control dispatching `options.dismiss` under the existing confirmation contract, and the footer chip names the committed card count (`建議 (N)`) whenever that count is positive

#### Scenario: A transport reset retires the epoch's cards
- **WHEN** a transport generation reset (`beginTransport`) occurs
- **THEN** the pane's card presentation is retired with the epoch: no card from a retired epoch remains clickable before the first new snapshot arrives
