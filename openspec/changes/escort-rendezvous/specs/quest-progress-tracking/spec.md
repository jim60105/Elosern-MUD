# Spec Delta

## MODIFIED Requirements

### Requirement: Room arrival drives REACH and ESCORT through supported persistent room hooks
REACH SHALL retain player-arrival, supported anchor/XYZ/bound-instance and companion co-presence behavior. ESCORT SHALL evaluate complete exact protected bindings using destination or rendezvous mode after applicable owner traversal, possessed protected-actor movement and follower settlement. Destination SHALL require every protected identity living at its validated locator. Rendezvous SHALL require exact protected and meeting identities living at the same authoritative position, with any published typed relation satisfied. Ordinary room identity SHALL remain distinct from wilderness provider/coordinate identity; recycled room objects SHALL not prove wilderness co-location. An original-body or unrelated-companion presence gate SHALL not apply to ESCORT. Actor absence, different identity, dead state or relation mismatch SHALL not satisfy a predicate.

#### Scenario: Destination waits for the last protected actor
- **WHEN** the owner arrives before all protected actors at a declared anchor, XYZ or bound instance
- **THEN** progress remains unchanged until all exact protected actors arrive living; another companion or same-name actor cannot substitute

#### Scenario: Rendezvous works at different actual locations
- **WHEN** the same published related roles meet at two different ordinary locations in independent fixtures, and at a valid wilderness position in another fixture
- **THEN** each actual reunion satisfies the rendezvous predicate with no fixed destination or original-body requirement

#### Scenario: Recycled wilderness rooms do not prove reunion
- **WHEN** meeting actors occupy different coordinates or different providers despite sharing recycled room/display identity
- **THEN** the predicate remains unsatisfied

#### Scenario: Typed relation and exact actors are required
- **WHEN** a same-name impostor, dead/missing actor or wrong published relation is supplied
- **THEN** the real rendezvous does not complete

#### Scenario: REACH behavior remains owner-arrival gated
- **WHEN** a player enters its existing matching REACH locator with valid companion co-presence
- **THEN** existing progress and instance-interaction behavior is preserved

#### Scenario: Anchor arrival completes a matching REACH stage
- **WHEN** the player enters an `AnchorRoom` whose `anchor_key` matches the active stage locator
- **THEN** that stage advances or completes in the same room-receive hook

#### Scenario: Grid arrival uses exact XYZ identity
- **WHEN** the player enters a `GridRoom` with the active REACH stage's exact `(x, y, z)` tuple
- **THEN** the stage advances without a room dbref stored in the definition

#### Scenario: Bound instance arrival uses the accepted record
- **WHEN** the player enters the `InstanceRoom` whose dbref is stored in the current record
- **THEN** a BOUND_INSTANCE REACH stage advances

#### Scenario: Companion co-presence satisfies arrival
- **WHEN** the player arrives at a matching destination and at least one bound companion is
  present there after the follow moves complete
- **THEN** the REACH or ESCORT stage advances exactly once, and the repeated post-follow
  observation advances nothing a second time

#### Scenario: Escort requires every protected entity alive and present
- **WHEN** the player reaches an ESCORT destination while one protected entity is absent or has zero HP
- **THEN** the stage remains unchanged; it advances only after all protected entities arrive alive

#### Scenario: Existing instance interaction behavior remains intact
- **WHEN** a player enters an `InstanceRoom`
- **THEN** `interacted` becomes true and quest arrival observation also runs

#### Scenario: Arrival requires a bound companion present in the destination
- **WHEN** ordinary REACH arrival observation evaluates a matching locator
- **THEN** its existing owner-arrival and companion co-presence gate applies; ESCORT uses its exact protected predicate with no unrelated-companion gate

#### Scenario: Observation is re-run once after companion follow moves complete
- **WHEN** companion follow moves complete after an arrival
- **THEN** arrival observation is re-run once so first-arrival co-presence is visible, with the one-transition rule making the repeated observation idempotent

#### Scenario: ESCORT requires a protected entity roster
- **WHEN** an ESCORT arrival is evaluated
- **THEN** at least one protected entity is required

### Requirement: Wilderness rooms do not advertise an arrival hook that normal traversal bypasses
Terrain rooms SHALL retain no false player room-arrival hook or invented wilderness destination locator. Wilderness traversal SHALL provide its authoritative settled role movement to the escort evaluator separately. Existing destination families SHALL remain unchanged.

#### Scenario: Wilderness role movement reaches rendezvous without a room hook
- **WHEN** a protected NPC or possessed actor steps to a live meeting role's exact provider/coordinate position
- **THEN** rendezvous evaluation runs from settled movement, while the ordinary REACH room-arrival hook remains absent

#### Scenario: Wilderness traversal does not produce false quest progress
- **WHEN** a player enters or steps through wilderness with no satisfied exact rendezvous binding
- **THEN** no ordinary room-arrival hook or invented wilderness destination progress occurs; real settled role movement separately reaches the rendezvous evaluator

### Requirement: Arrival observation advances at most one per event and never exceeds quantity
Arrival and escort role-result observation SHALL cap progress and transition each record at most once per stable authoritative source identity, including across pre-follow/post-follow hooks and restart. The source SHALL remain the same through related encounter activation and final movement evaluation. An intermediate stage SHALL never cause another stage transition or final-group resolution from the same source.

#### Scenario: Pre-follow and post-follow share one source
- **WHEN** room receive, encounter activation and follower completion observe one traversal
- **THEN** each relevant record advances at most one stage and a later-stage match from the same source is ignored

#### Scenario: Replayed source remains consumed after restart
- **WHEN** the same settled movement result is replayed after committed reload
- **THEN** no progress, group resolution, payout or later-stage transition is repeated

#### Scenario: First arrival with quantity one completes the stage

- **WHEN** the player arrives at a matching destination with companion co-presence and the stage quantity is 1
- **THEN** progress becomes 1, the stage completes exactly once, and a repeated post-follow observation advances nothing

#### Scenario: Arrival never over-fills progress

- **WHEN** a matching arrival would advance progress beyond the objective quantity
- **THEN** progress is capped at the quantity and the quest transitions at most once

#### Scenario: Post-follow re-observation never re-counts the same arrival
- **WHEN** the post-follow re-observation (party-follow D-2) runs and a companion was already present in the destination
- **THEN** the re-run is skipped because the first observation has already advanced every matching stage for that event, so it SHALL NOT re-count the same arrival event

### Requirement: Stage completion advances exactly once and releases obsolete runtime bindings
Existing stage completion SHALL cap progress, release obsolete stage pins/bindings, reset per-stage counted state and enter at most one next contiguous stage or terminal completion. Terminal `COMPLETED`, `FAILED` and `INVALIDATED` records SHALL ignore later progress. Escort membership reasons SHALL remain valid across intermediate stages only while the definition explicitly retains that protected binding; terminal transitions SHALL release that record's reasons. Declared exclusive final results SHALL arbitrate before a completion or reward becomes eligible.

#### Scenario: Intermediate arrival cannot settle a final result
- **WHEN** a multistage alternative completes an intermediate arrival or clue stage
- **THEN** it advances one stage, releases obsolete pins, and neither invalidates alternatives nor plans the terminal reward

#### Scenario: All terminal states reject future progress
- **WHEN** later matching movement, combat or inventory events reach completed, failed and invalidated records
- **THEN** each remains unchanged

#### Scenario: Intermediate objective enters the next stage
- **WHEN** a matching event satisfies a non-final stage
- **THEN** the record advances by one stage, resets progress to zero, clears bindings, and remains active

#### Scenario: Final objective completes the quest
- **WHEN** a matching event satisfies the final stage
- **THEN** state becomes `COMPLETED`, progress is capped at the objective quantity, and bindings are
  cleared

#### Scenario: Instance pin is released on stage exit
- **WHEN** a bound-instance stage advances or completes
- **THEN** its exact quest pin is absent before the transition returns, while room deletion and promotion
  remain exclusively owned by map-instance reclamation

#### Scenario: One transfer advances a delivery stage at most once
- **WHEN** a single committed transfer carries more of the objective's item than the delivery stage
  still needs
- **THEN** the stage advances exactly once, progress is capped at the objective quantity, and the
  surplus does not carry into the next stage

#### Scenario: A terminal record ignores a later matching transfer
- **WHEN** later matching transfer reaches completed, failed or invalidated quest history
- **THEN** the terminal record stays unchanged

## ADDED Requirements

### Requirement: Indexed authoritative role events drive escort evaluation
`evaluate_escort_event` SHALL consume owner/package/source/tick and owner-resolved settled role provenance through indexed owned bindings/groups. It SHALL join the event transaction and return unsatisfied, stage_advanced, resolved or already_observed plus affected identities, with invalid_source/role_unavailable failures. Movement, activation, binding and living-state boundaries SHALL reach it without global player/story scans.

#### Scenario: Non-player movement reaches the same evaluator
- **WHEN** a scheduled meeting role moves, an encounter activates a relevant role, a protected binding is accepted, or a relevant living state changes
- **THEN** the same evaluator revalidates relevant owned identities without a player-body arrival or global log scan

#### Scenario: Fabricated observation is rejected
- **WHEN** a caller supplies a source without owner-resolvable movement/activation/binding/living-state provenance
- **THEN** `invalid_source` returns before any stage, group, knowledge or reward write

#### Scenario: Complete indexed authoritative role events drive escort evaluation contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** Evaluation SHALL consume role movement, activation, acceptance/binding and living-state changes through indexed owner/package/role/outcome references. It SHALL inspect only relevant owned bindings, never scan every player or generated story per movement. `evaluate_escort_event` SHALL accept owner, package, source identity, tick and owner-resolved committed event provenance; return `unsatisfied`, `stage_advanced`, `resolved`, or `already_observed` plus affected record/group identities; and refuse `invalid_source` or `role_unavailable` as appropriate. It SHALL join the authoritative event transaction; standalone acceptance/activation evaluation SHALL join that operation's outer transaction. Prose or fabricated observation dictionaries SHALL have no mutation authority.

### Requirement: Escort finding does not disclose hidden actor positions
Actual presence and permitted interaction SHALL determine finding and clues. Evaluation MAY inspect actual meeting positions but SHALL not reveal them to the player or uninformed speakers. Participant knowledge SHALL be recorded through narrative owners and upstream phase transitions; reunion acknowledgment and its closure interaction SHALL precede everyday dialogue. Prior history/persona/memory SHALL remain; failure SHALL not select successful reunion content.

#### Scenario: Actual reunion changes participant conversation only
- **WHEN** reunion commits and the actual participants complete acknowledgment and closure
- **THEN** reopening their conversation shows everyday greeting/topics with prior history preserved, and an uninformed third party has no reunion knowledge

#### Scenario: Hidden target cannot become a clue by reference
- **WHEN** an objective refers to a distant meeting actor whose position the speaker does not know
- **THEN** dialogue and player hints omit that position until an explicit permitted information transfer occurs
