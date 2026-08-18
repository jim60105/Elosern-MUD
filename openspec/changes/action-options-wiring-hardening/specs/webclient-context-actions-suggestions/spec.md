## MODIFIED Requirements

### Requirement: Exploration suggestions render from an immutable session snapshot
The exploration available form's `suggestions` SHALL be assembled only from
`context.options_state` — an immutable `OptionsSnapshot` — and from the deterministic
`default_cards()` derivation over the **same fresh affordance tuple just serialized into the
form** (one build, two consumers; the affordance-contract change defines `default_cards(affordances, ...)`).
The presenter SHALL NOT read the raw session, generation-side metadata, or any transport
artifact. The `OptionsSnapshot` SHALL be created by the ingress/coordinator from
`session.ndb.options_state` through a factory that deep-copies the displayed cards into immutable
card representations (frozen, no shared mutable dicts), so repeated renders of one snapshot are
stable even if the async writer later replaces the session state object. The shared
presentation-context factory SHALL additionally carry the current read-only exploration situation
fingerprint. When the snapshot is absent, its status is `"unavailable"`, the current fingerprint
is absent, or a non-unavailable snapshot fingerprint differs from the current fingerprint, the
form SHALL emit `status: "unavailable"`. `"generating"` SHALL emit the status alone only when its
fingerprint is current; `"ready"` SHALL emit exactly the current snapshot's `displayed` cards; and
`"degraded"` SHALL emit `default_cards(affordances)` only when its fingerprint is current. A ready
snapshot whose `displayed` set is missing or fails the v5 shape gate SHALL emit `"unavailable"`
with a bounded diagnostic log and SHALL NOT fabricate cards. A degraded derivation whose cards
fail the v5 shape gate (the vocabulary bounds display names at 128 code points without a CJK
requirement, while suggestion labels are 1..24 CJK code points) SHALL likewise emit
`"unavailable"` with a bounded diagnostic log — the panel SHALL stay available and no
shape-invalid card SHALL reach the wire. Contexts built without snapshot state (default `None`)
SHALL behave exactly as before. The freshness gate SHALL be read-only and SHALL not schedule,
evict, or mutate state.

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
