# quest-progress-tracking Specification

## Purpose
Automatic quest progress driven by committed player actions (DEFEAT) and room arrival (REACH/ESCORT),
with stable dbref identity, one transition per event, and instance-pin release on every stage exit.

## Requirements

### Requirement: DEFEAT progress is planned automatically from committed player action events
The quest event-effect planner SHALL inspect `target_defeated` entries produced by an
`ActionResolver` request or the combat upkeep settlement, advancing only active DEFEAT stages
owned by a `PlayerCharacter` actor. Counting SHALL key on the defeated individual's persistent
identity, never display keys, and the quest mutation SHALL commit in the same action or
combat-round transaction as the lethal damage.

#### Scenario: Player defeat advances a matching tier objective automatically
- **WHEN** a player action lethally damages a monster whose tier matches the player's active DEFEAT stage
- **THEN** `ActionResolver.resolve()` commits the damage and increments quest progress without any caller
  invoking a separate observer

#### Scenario: Bound objective matches exact dbref
- **WHEN** two monsters share a display key but only one dbref is in `objective_target_ids`
- **THEN** defeating the unbound monster does not advance the quest and defeating the bound monster does

#### Scenario: A duplicate defeat event for one individual counts once
- **WHEN** the planner is presented twice with the same defeat entry for one individual against the same active record
- **THEN** the objective's progress advances once across both presentations

#### Scenario: A bound companion's kill advances the owner's objective
- **WHEN** a bound, non-knocked-out companion defeats a monster matching the owner's active DEFEAT stage
- **THEN** the owner's quest progress advances in the same action transaction with the same cap and
  one-transition rules

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion defeats a matching-tier monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Another character's action grants no ordinary kill credit
- **WHEN** an NPC that is not a bound companion, a different `PlayerCharacter`, or a monster defeats a matching-tier monster
- **THEN** the quest owner's ordinary DEFEAT progress is unchanged

#### Scenario: Quest planner failure rejects the complete action
- **WHEN** the quest planner cannot stage a valid transition because the actor's active record is
  malformed
- **THEN** the action rejects before commit and target HP, resources, progression, quest log, and pins
  all remain unchanged

#### Scenario: AREA defeat entries aggregate without skipping stages
- **WHEN** one AREA action defeats three matching targets while the current objective needs two
- **THEN** progress reaches two, the current stage transitions exactly once, and the surplus kill is not
  applied to the next stage

#### Scenario: An attributed upkeep kill advances the matching objective
- **WHEN** the player's damaging rate tick causes the lethal HP crossing of a monster matching the player's active DEFEAT stage
- **THEN** the quest log advances in the same combat-round transaction with the same cap and one-transition rules

#### Scenario: A simulated or unattributed upkeep kill grants no quest progress
- **WHEN** a lethal rate tick fires inside a guild examination, or an upkeep tick has no resolvable source
- **THEN** no quest DEFEAT stage advances and no protected-entity failure occurs

#### Scenario: A bound non-knocked-out companion kill advances the owner's stage
- **WHEN** the acting entity is a bound companion of the owner (per the party binding) and is not knocked out
- **THEN** the owner's matching stage advances under the same aggregation, cap, and one-transition rules as the owner's own

#### Scenario: Bound-target objective matches target_id against the bound id set
- **WHEN** the objective is bound-target
- **THEN** matching is `data["target_id"]` against the record's `objective_target_ids`

#### Scenario: Unbound tier objective matches the declared monster_tier
- **WHEN** the objective is an unbound tier objective
- **THEN** matching is against its declared `monster_tier`

#### Scenario: Regional species-hunt objective uses the species-hunt rules
- **WHEN** the objective is a regional species-hunt objective
- **THEN** matching follows the species-hunt rules below

#### Scenario: Duplicate or redelivered entries for counted identities advance nothing
- **WHEN** a duplicate or redelivered `target_defeated` entry names an individual identity this record has already counted for its current objective
- **THEN** the entry advances nothing, because each record keeps the set of individual identities already counted for its current objective

#### Scenario: Planner aggregation caps progress with one transition and no surplus carryover
- **WHEN** several matching defeat entries appear in one EventLog for a quest
- **THEN** the planner SHALL aggregate every matching entry into that one EventLog per quest, cap progress at the current objective quantity, perform at most one stage transition, and discard surplus kills rather than applying them to the next stage

### Requirement: Room arrival drives REACH and ESCORT through supported persistent room hooks
REACH SHALL retain player-arrival, anchor/XYZ/bound-instance and companion co-presence behavior as its scenarios state. ESCORT SHALL evaluate complete exact protected bindings in destination or rendezvous mode after owner traversal, possessed-actor movement and follower settlement. Destination SHALL require every protected identity living at its validated locator; rendezvous SHALL require exact protected and meeting identities living at one position with any declared relation satisfied.

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

#### Scenario: Room and wilderness identity stay distinct for ESCORT
- **WHEN** an arrival or rendezvous is evaluated at a room or wilderness position
- **THEN** Ordinary room identity SHALL remain distinct from wilderness provider/coordinate identity, and recycled room objects SHALL not prove wilderness co-location. An original-body or unrelated-companion presence gate SHALL not apply to ESCORT, and actor absence, a different identity, dead state or relation mismatch SHALL not satisfy a predicate.

### Requirement: Wilderness rooms do not advertise an arrival hook that normal traversal bypasses
Terrain rooms SHALL retain no false player room-arrival hook or invented wilderness destination locator. Wilderness traversal SHALL provide its authoritative settled role movement to the escort evaluator separately. Existing destination families SHALL remain unchanged.

#### Scenario: Wilderness role movement reaches rendezvous without a room hook
- **WHEN** a protected NPC or possessed actor steps to a live meeting role's exact provider/coordinate position
- **THEN** rendezvous evaluation runs from settled movement, while the ordinary REACH room-arrival hook remains absent

#### Scenario: Wilderness traversal does not produce false quest progress
- **WHEN** a player enters or steps through wilderness with no satisfied exact rendezvous binding
- **THEN** no ordinary room-arrival hook or invented wilderness destination progress occurs; real settled role movement separately reaches the rendezvous evaluator

### Requirement: Stage completion advances exactly once and releases obsolete runtime bindings
Stage completion SHALL cap progress, release obsolete stage pins/bindings, reset per-stage counted state and enter at most one next contiguous stage or terminal completion. Terminal `COMPLETED`, `FAILED` and `INVALIDATED` records SHALL ignore later progress. Escort membership reasons SHALL stay valid across intermediate stages only while the definition retains that protected binding, and terminal transitions SHALL release that record's reasons.

#### Scenario: Intermediate arrival cannot settle a final result
- **WHEN** a multistage alternative completes an intermediate arrival or clue stage
- **THEN** it advances one stage, releases obsolete pins, and neither invalidates alternatives nor plans the terminal reward

#### Scenario: Physical final condition during an intermediate transition stays unresolved
- **WHEN** one source advances an intermediate stage and also leaves the exact reunion roles co-located, and the source is replayed after reload
- **THEN** candidate eligibility uses the pre-event stage and consumed transition state, the group remains unresolved, active alternatives retain entitlement, no no-commission fallback runs, and replay grants no second-stage progress

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

#### Scenario: Exclusive results arbitrate before eligibility
- **WHEN** a declared exclusive final result becomes satisfiable
- **THEN** Declared exclusive final results SHALL arbitrate before a completion or reward becomes eligible.

### Requirement: Change 15 exposes a deterministic no-AI completion seam for Phase 4
An integration test SHALL synchronize the hand-written catalog, accept its introductory hunt, resolve a
player's lethal action against a matching monster through `ActionResolver`, and observe the quest become
completed without directly calling quest progress functions or importing `world/ai/`.

#### Scenario: Hand-written hunt completes through ordinary combat resolution
- **WHEN** AI services are unavailable and an integration test accepts the catalog hunt through the
  lifecycle API and resolves its fight through `ActionResolver`
- **THEN** deterministic resolution produces a `COMPLETED` record ready for change 16, without claiming
  that change 15 alone supplied player commands or a world encounter

#### Scenario: Completed record is suitable for change 16
- **WHEN** the seam produces its completed record
- **THEN** the record SHALL be suitable for change 16's future player-facing accept/combat-entry/turn-in and reward settlement

#### Scenario: API-level test is not milestone proof
- **WHEN** this API-level test passes
- **THEN** it SHALL NOT be treated as proof that the player-playable Phase-4 milestone is complete before that command-level change-16 integration exists

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
- **WHEN** final post-follow observation runs after ordinary REACH consumed its transition while an unrelated general companion was already at the destination and protected escort actors arrive with the followers
- **THEN** the consumed REACH transition is not repeated, the settled ESCORT pass still evaluates the newly arrived exact protected roster and activated meeting roles, and persisted source identity prevents a second transition

### Requirement: Species-hunt objectives match by variant membership, region, and persistent identity
The quest planner SHALL evaluate a regional species-hunt DEFEAT objective against the `target_defeated`
entry's species/variant identity fields: an entry counts only when its species key equals the
objective's species key, its variant key is one of the objective's countable variant keys, and the
defeated individual's location resolved inside the objective's declared region at defeat time.
Matching SHALL NOT consult display names, guild rank, or a single stat.

#### Scenario: A countable stronger variant counts once
- **WHEN** a general hunt counts eligible variants and a stronger same-species individual inside the region is defeated
- **THEN** progress advances by one for that identity, and a duplicate event for it advances nothing

#### Scenario: An unlisted variant does not count
- **WHEN** a defeated individual's variant is a registered variant of the species but not among the objective's countable variants
- **THEN** progress does not advance

#### Scenario: Outside the region does not count
- **WHEN** an individual of the right species and a countable variant is defeated outside the declared region
- **THEN** progress does not advance

#### Scenario: Ordinary targets alone always suffice
- **WHEN** a hunt's ordinary-eligible targets were guaranteed at acceptance and all counted defeats are ordinary variants
- **THEN** the objective completes without requiring any stronger variant

#### Scenario: Tier-only kills never satisfy a species hunt
- **WHEN** a tier-only monster without species identity is defeated inside the region
- **THEN** the species-hunt objective's progress is unchanged

#### Scenario: Each distinct persistent individual identity counts at most once per record
- **WHEN** eligible defeats are counted for one record
- **THEN** each distinct persistent individual identity counts at most once, composing with the already-counted-identity dedupe

#### Scenario: Stronger same-species variants count once and are never required
- **WHEN** stronger same-species variants appear in a general hunt
- **THEN** one stronger individual never counts twice and is never required when ordinary-eligible targets suffice

#### Scenario: A specific-variant hunt counts only its named variants
- **WHEN** a hunt's countable variants name specific variants
- **THEN** only those variants are counted

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
