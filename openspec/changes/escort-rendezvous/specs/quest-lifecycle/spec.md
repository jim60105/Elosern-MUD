# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: QuestRecord is JSON-safe persisted state with three stored states`
- TO: `### Requirement: QuestRecord is JSON-safe persisted state with explicit terminal invalidation`

## MODIFIED Requirements

### Requirement: QuestRecord is JSON-safe persisted state with explicit terminal invalidation
Quest records SHALL retain existing deterministic identity, definition/issuer, progress, deadline/tick, tracking and counted-defeat fields, while adding distinct terminal `INVALIDATED` state with a structured obsolete-outcome reason and JSON-safe package/group/acceptance-sequence/protected-role binding metadata. The stored vocabulary SHALL contain `IN_PROGRESS`, `COMPLETED`, `FAILED`, and `INVALIDATED`. Terminal records SHALL retain history and no active stage bindings. Invalidation SHALL carry no failure penalty, payout, or retry path after group resolution. Unaccepted definitions SHALL remain absence of a quest record. Existing normal defaults SHALL remain; no migration or compatibility adapter SHALL be introduced.

#### Scenario: Invalidated record round-trips
- **WHEN** an accepted alternative is invalidated and its serialized record is reloaded
- **THEN** its distinct state, structured reason, issuer, group and acceptance sequence are preserved with no live objects or active stage pins

#### Scenario: Tracking and deadlines ignore invalidated history
- **WHEN** tracking, deadline processing, action/arrival planners, detail views and objective presentation inspect an invalidated record
- **THEN** it is terminal, cannot be tracked active or expired as a new failure, shows its reason, and never gains progress or payout

#### Scenario: A record round-trips through JSON
- **WHEN** a record containing integer dbrefs and tuple bindings is serialized to its storage dict,
  passed through JSON serialization, and reconstructed
- **THEN** every field equals the original, including `issuer_key` and `counted_defeat_ids`, and the stored value contains no
  live entity reference

#### Scenario: Unaccepted definition has no record
- **WHEN** a definition is registered but never accepted by a character
- **THEN** that character's quest log has no record for the definition

#### Scenario: Accepting never tracks
- **WHEN** a character accepts a definition
- **THEN** the created record carries `tracked` false and an empty counted-identity tuple

#### Scenario: A legacy-shaped entry without the key loads untracked
- **WHEN** a stored quest-log entry dict carries every other field but no `tracked` key
- **THEN** the record loader returns `tracked=False` without rewriting the stored entry

#### Scenario: An entry missing the issuer key is rejected, not defaulted
- **WHEN** a stored quest-log entry dict carries every other field but no `issuer_key` key
- **THEN** the strict reader raises `QuestDataError` and no lifecycle operation proceeds

#### Scenario: An entry with a malformed issuer key is rejected
- **WHEN** a stored entry carries an `issuer_key` that does not parse under the shared grammar
- **THEN** the strict reader raises `QuestDataError` and the stored value is neither rewritten nor
  coerced

#### Scenario: The counted-identity tuple tracks credited defeats
- **WHEN** a record credits individuals for its current DEFEAT objective
- **THEN** `counted_defeat_ids` is a JSON-safe tuple of the integer persistent identities already credited for that objective, defaulting to empty and cleared on stage transition together with the existing runtime bindings
- **AND** a new objective therefore counts its own identities from empty, so counted-set residue can never cap later stages

#### Scenario: The issuer key is required and grammar-validated
- **WHEN** a record is created or read
- **THEN** `issuer_key` is a required non-empty string naming the commission the record was accepted under
- **AND** the strict reader validates it against the shared issuer-key grammar and rejects a missing or malformed value rather than defaulting it — a record must always say which issuance governs its reward and settlement

#### Scenario: The tracked flag is a boolean defaulting to false
- **WHEN** a record is created or a stored entry is loaded
- **THEN** `tracked` is a boolean defaulting to false and accepting a quest never sets it
- **AND** a stored entry whose dict carries no `tracked` key loads as `tracked=False`

#### Scenario: A legacy entry without counted ids loads empty
- **WHEN** a stored entry carries no `counted_defeat_ids` key
- **THEN** it loads as empty without rewriting the stored entry

#### Scenario: Unaccepted and abandoned representations
- **WHEN** a definition is unaccepted or a quest is abandoned
- **THEN** unaccepted is represented by absence and abandonment uses `FAILED` with reason `abandoned`

### Requirement: accept_quest creates one deterministic active record
Acceptance SHALL retain existing definition/issuance validation, deterministic record numbering, accepted tick/deadline, no automatic tracking, and existing hunt/site guarantees. Escort acceptance SHALL additionally revalidate actual issuer scope and current offer capability, unresolved exclusive group, exact protected role identity, co-location, living state and membership ownership. The relevant physical actor SHALL use existing possession actor/owner mapping. All declared protected roles SHALL be available. One owning outer transaction SHALL create the record, bind exact actors, add party reasons, allocate the group's monotonic sequence and record authorized dialogue/acceptance knowledge. Full general quota SHALL permit temporary joining. Any later write failure SHALL restore quest, party, component and dialogue caches. Terminal retry SHALL remain allowed for unrelated definitions under existing rules; resolved exclusive alternatives SHALL refuse every retry.

#### Scenario: Acceptance returns the committed bound record
- **WHEN** an authorized available multi-role escort is accepted at full general quota
- **THEN** the returned record equals a fresh read, binds every exact published protected actor and commits unique reasons and acceptance sequence together

#### Scenario: Acceptance refuses a partial protected roster
- **WHEN** any required actor is dead, missing, remote, substituted, or owned by another player
- **THEN** the named refusal creates no record, source reason, authority change or partial roster

#### Scenario: Stale capability or resolved group refuses acceptance
- **WHEN** an old offer is submitted after its phase or exclusive outcome has changed
- **THEN** acceptance returns `offer_stale` or `outcome_resolved` without retroactive record creation

#### Scenario: Acceptance faults restore all surfaces
- **WHEN** failures are injected after record, binding, membership and dialogue writes
- **THEN** database reload and live caches match baseline and no acceptance event is committed

#### Scenario: First acceptance succeeds
- **WHEN** a character accepts a known definition under a registered issuance with no previous record
  for it
- **THEN** one stage-zero `IN_PROGRESS` record is stored with quest ID `<definition-key>:1` and the
  supplied issuer key

#### Scenario: Duplicate active acceptance is rejected
- **WHEN** the character accepts a definition for which an `IN_PROGRESS` record already exists
- **THEN** `QuestAlreadyActive` is raised and the quest log is unchanged

#### Scenario: Acceptance under an unregistered issuance is rejected
- **WHEN** the character accepts a known definition naming an issuer key with no registered issuance
- **THEN** acceptance raises a named error and the quest log is unchanged

#### Scenario: Terminal quest may be retried deterministically
- **WHEN** a previous unrelated record is completed or failed and the definition remains currently available
- **THEN** existing next-number acceptance retains terminal history; a resolved exclusive alternative instead refuses with outcome_resolved

#### Scenario: Explicit deadline is converted to ticks
- **WHEN** a definition with `deadline_hours=72` is accepted at tick T
- **THEN** its deadline is `T + 72 * CLOCK_YAML["seconds_per_hour"]`

#### Scenario: No-deadline definition remains without a deadline
- **WHEN** a definition with `deadline_hours=None` is accepted
- **THEN** the record's `deadline_tick` is `None`

#### Scenario: The same definition can be held twice under different issuers
- **WHEN** a character completes a definition issued by a guild branch and later accepts the same
  definition from a private commissioner
- **THEN** the new record carries the private issuer key while the terminal record retains the guild
  issuer key

#### Scenario: Species-hunt acceptance guarantees ordinary-eligible targets
- **WHEN** a species hunt is accepted and the region already holds enough reachable living ordinary-eligible individuals
- **THEN** acceptance succeeds without the manager creating anything

#### Scenario: Provisioning fills a shortfall through its owner only
- **WHEN** a species hunt needs more ordinary-eligible targets than currently live in the region and placement capacity permits more
- **THEN** the ambient/site owner provisions the difference within its capacity and ownership rules, and the hunt accepts in the same transaction

#### Scenario: An illegal hunt is refused with no partial state
- **WHEN** provisioning cannot legally satisfy the quantity — capacity full, ownership blocked, or the only source a cleared site whose recovery condition is not due
- **THEN** acceptance is refused with a named reason, and a database before/after comparison shows neither a quest record nor any created or moved individual

#### Scenario: A standing site clear-out binds the site's own individuals
- **WHEN** a clear-out is accepted while the site owns at least the required living individuals
- **THEN** the new record's objective target set is exactly those individuals, the record carries no instance pin, and the site's own individuals are unchanged in number

#### Scenario: A cleared one-shot site refuses permanently
- **WHEN** a clear-out over a cleared one-shot site is accepted
- **THEN** acceptance is refused with the site-cleared reason, and the quest log, the site's durable state, and every individual it owns equal their pre-acceptance values

#### Scenario: A due recoverable site is bound only after it has recovered
- **WHEN** a clear-out over a cleared recoverable site is accepted before its authored in-game condition matures
- **THEN** acceptance is refused with its named reason, no individual is created, and the site's cleared state is unchanged

#### Scenario: Acceptance never populates a site
- **WHEN** a clear-out is accepted against a site the world has not yet populated
- **THEN** acceptance is refused with the not-yet-populated reason, and a before/after comparison shows the site still unpopulated with no individual created for it

#### Scenario: The returned record carries the binding
- **WHEN** a clear-out acceptance succeeds
- **THEN** the returned record's objective target set equals the site's living individuals that were bound, the same set a fresh read of the quest log returns, and a rollback of an injected failure restores the log to its pre-acceptance value

#### Scenario: The new record carries deterministic acceptance metadata
- **WHEN** accept_quest creates a record
- **THEN** its deterministic `quest_id` uses the definition key and that character's next acceptance number
- **AND** its `accepted_tick` is the current world tick
- **AND** its `deadline_tick` is either `None` or the accepted tick plus the definition's positive hours converted with `CLOCK_YAML`

#### Scenario: Species-hunt acceptance requires eligible targets in region
- **WHEN** the definition's current stage is a regional species hunt
- **THEN** acceptance additionally requires that enough reachable, living, ordinary-eligible target individuals exist within the objective's declared region to satisfy the quantity

#### Scenario: Hunt provisioning flows only through owning managers
- **WHEN** the deterministic core obtains the species-hunt target guarantee
- **THEN** it goes through the existing ambient/site managers — never by creating, moving, or deleting individuals directly
- **AND** those managers honor habitat, authored placement capacity, ownership markers, and current site state
- **AND** provisioning does not rebuild existing eligible individuals and does not early-recover a cleared site

#### Scenario: Clear-out acceptance reads the site's own population
- **WHEN** the definition's current stage is a bound clear-out over an authored site
- **THEN** acceptance additionally requires that the site currently owns at least the objective's quantity of living individuals
- **AND** that guarantee is a read of the site owner's own state and population — acceptance does not create, populate, move, recover, or delete an individual

#### Scenario: The site's durable state is the sole answer
- **WHEN** clear-out acceptance consults the site
- **THEN** the site's durable lifecycle state is the sole answer — world absent, unknown site, never populated, cleared, or short — and no path early-recovers a site
- **AND** a site the world has not yet populated refuses with its own named reason, distinct from both a cleared site and a shortfall

#### Scenario: A satisfied guarantee binds exactly the site's individuals
- **WHEN** the clear-out guarantee holds
- **THEN** acceptance binds exactly the site's living individuals as the record's stage-zero objective targets through the existing binding writer, inside the same all-or-nothing transaction as the record write, and creates no instance pin: the site is a permanent wilderness location, not a spawned scene

#### Scenario: The refusal vocabulary is closed and named
- **WHEN** clear-out acceptance refuses
- **THEN** the reason is one of `world_unavailable`, `unknown_site`, `site_unpopulated`, `site_cleared`, and `site_short`

#### Scenario: Acceptance is one all-or-nothing transaction
- **WHEN** guarantee, binding, and record creation run
- **THEN** they form one all-or-nothing transaction: any validation or manager failure rolls back all of them, leaving no active record, no binding, and no partial target arrangement
- **AND** when the condition cannot be legally satisfied, acceptance is refused with a named reason before any persistence

#### Scenario: The returned record is the persisted bound record
- **WHEN** a binding acceptance completes
- **THEN** the record the operation returns is the persisted, bound record rather than the unbound value written a moment earlier

### Requirement: bind_stage_runtime attaches only current-stage instance and entity identities
Current-stage binding SHALL retain exact live entity IDs, disjoint objective/protected sets, immutable identical-rebind behavior and named conflict refusal. Escort protected roles SHALL resolve through published package/role identity to the same exact NPC at acceptance and every evaluation. A supplied pinned room SHALL remain an actual existing instance; permanent destination resolution SHALL be separate and SHALL create no fake instance pin. Meeting roles SHALL retain upstream bindings and SHALL never be added to the protected roster by proximity.

#### Scenario: Permanent destination creates no instance pin
- **WHEN** an escort binds protected actors for an anchor or XYZ destination
- **THEN** exact protected IDs persist without passing the permanent room to the instance-only pin contract

#### Scenario: Substitution and overlapping sets refuse
- **WHEN** a caller substitutes a same-name NPC, changes an existing role binding or overlaps objective/protected IDs
- **THEN** binding refuses before any record or pin change

#### Scenario: Runtime binding stores identities and pins the instance
- **WHEN** a current stage is bound to one instance room, two objective targets, and one protected NPC
- **THEN** the record stores the three entity dbrefs in their respective fields and the room contains
  exactly the stage's quest pin

#### Scenario: Objective and protected identities remain distinct
- **WHEN** a stage is bound with the same call's objective targets and protected entities
- **THEN** defeating an objective target cannot match the protected-entity failure set

#### Scenario: Overlapping objective and protected binding is rejected
- **WHEN** the same entity dbref is supplied in `objective_targets` and `protected_entities`
- **THEN** `QuestTransitionError` is raised before the quest log or room pin changes

#### Scenario: Persisted overlapping identity sets are invalid
- **WHEN** strict record parsing finds one dbref in both identity fields
- **THEN** it raises `QuestDataError` and no lifecycle operation mutates that record or its pin

#### Scenario: Conflicting rebind is rejected atomically
- **WHEN** a bound stage is rebound to a different room or entity set
- **THEN** `QuestTransitionError` is raised and the old record and pin remain unchanged

#### Scenario: A duplicate identity across binding sets is rejected
- **WHEN** a dbref is present in both the objective-target and protected-entity sets
- **THEN** the binding rejects it before mutation

#### Scenario: Identical rebinding is idempotent
- **WHEN** an identical binding is repeated
- **THEN** the operation is idempotent, while replacing any existing binding raises before mutation

### Requirement: Multi-attribute lifecycle writes are atomic and cache-consistent
Quest transitions SHALL atomically commit their quest log, pins, party reasons, exclusive group, dialogue/knowledge and applicable settlement effects through their existing owners. Snapshot/restore SHALL include Evennia Attribute/component caches, process registration views where touched, and live possession/session surfaces. Post-commit presentation SHALL not expose rolled-back state. No partial success SHALL be returned.

#### Scenario: Failure after a group or reward write restores baseline
- **WHEN** group, claim, reward, pin or later dialogue persistence raises during a transition
- **THEN** durable and cached state return to pre-operation values including session control if handback occurred

#### Scenario: Pin failure rolls back acceptance or binding
- **WHEN** pin persistence is fault-injected to raise during a runtime binding
- **THEN** the quest record, room pin list, and their in-process attribute values equal their
  pre-operation state

#### Scenario: Quest-log failure restores an already-written pin
- **WHEN** quest-log persistence raises after a pin write
- **THEN** database state and cached room attributes both contain the original pin list

### Requirement: abandon_quest fails only an active quest and releases its runtime binding
Abandonment SHALL retain `FAILED` with reason `abandoned` for an active record, clear its stage bindings/pin and release only its temporary membership reasons through the compensated party/possession APIs. Repeated calls on terminal records SHALL be idempotent and unknown IDs SHALL retain `QuestNotFound`. Completion, actual failure and invalidation SHALL use the same per-record release discipline. Surviving general identity or other valid reasons SHALL remain; no release SHALL delete, regenerate or reset an actor's memory.

#### Scenario: Terminal release preserves unrelated sources
- **WHEN** one of two escort records terminates for completion, abandonment, death, deadline or invalidation
- **THEN** only its reasons/pins are removed and any remaining legitimate membership persists without actor replacement

#### Scenario: Repeated terminal release writes nothing
- **WHEN** the same terminal transition is replayed after reload
- **THEN** no additional handback, phase mutation, source release or reward occurs

#### Scenario: Abandonment records failure and releases a pin
- **WHEN** an active bound-instance quest is abandoned
- **THEN** it is failed with reason `abandoned`, its bindings are cleared, and its exact quest pin is
  absent from the room in the same operation

#### Scenario: Repeated abandonment is harmless
- **WHEN** `abandon_quest()` is called twice for the same quest ID
- **THEN** the second call makes no additional state change and does not fail on the already-removed pin

## ADDED Requirements

### Requirement: Escort lifecycle observations expose named owned operations
`accept_escort_commission` SHALL accept owner, actual interaction actor, package, authorized issuance and expected offer capability and return the persisted bound record/membership effects. `release_escort_bindings` SHALL accept owner, record, terminal reason and source and return terminal state plus removed/preserved sources. Each SHALL own or join the authoritative transaction with compensation and expose the scenario-defined stable failures.

#### Scenario: Downstream caller sees a named rejection without writes
- **WHEN** a consumer invokes escort acceptance with an unauthorized issuer or stolen protected role
- **THEN** it receives the specified reason and unchanged durable/cache state, without requiring knowledge of internal module placement

#### Scenario: Complete escort lifecycle observations expose named owned operations contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** The quest-owned `accept_escort_commission` operation SHALL consume owner, authorized issuance reference, package identity and expected offer capability; return the persisted bound record and membership effects; and report `issuer_unauthorized`, `offer_stale`, `outcome_resolved`, `role_unavailable`, `role_not_co_located`, `membership_owned_elsewhere` or `acceptance_write_failed`. `release_escort_bindings` SHALL consume owner, record identity, validated terminal reason and source identity; return terminal record and removed/preserved sources; and report `control_handback_failed` or `transition_write_failed`. Both SHALL own an outer transaction or join the enclosing authoritative event transaction with equivalent compensation. Callers SHALL receive successful durable results only after commit.

### Requirement: Real actor loss produces an explicit escort lifecycle result
Lawful committed protected death SHALL fail escort as `protected_actor_dead`; essential meeting actor death/removal SHALL transition unavailable as `meeting_actor_unavailable`. Hostile/environmental sources SHALL share the failure planner. Separation SHALL preserve actual location and active binding; knockout SHALL follow existing recovery rules. Deadline/abandonment SHALL retain distinct reasons.

#### Scenario: Hostile and environmental death fail the escort
- **WHEN** a lawful hostile or environmental source commits protected death
- **THEN** its escort fails and releases its reasons without payout or successful reunion dialogue

#### Scenario: Meeting removal is explicit and separation is recoverable
- **WHEN** an essential meeting actor is removed or a follower misses movement
- **THEN** removal transitions the objective unavailable without repair spawn, while mere separation leaves the escort active at the NPC's real location and permits resumption

#### Scenario: Complete real actor loss produces an explicit escort lifecycle result contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** Committed protected death SHALL fail its active escort with `protected_actor_dead`; essential meeting actor death/removal SHALL make it unavailable through `meeting_actor_unavailable`, releasing its own sources. Hostile and environmental sources SHALL use the same failure planner. Deadline and abandonment SHALL retain distinct existing reasons. Separation SHALL preserve actual location and active binding with the existing lost-follow notice. Knockout/recovery SHALL follow existing living-state rules and never fabricate death or reunion.
