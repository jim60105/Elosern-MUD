# quest-lifecycle Specification

## Purpose
Persistent deterministic per-character quest records and their lifecycle operations — accept, abandon,
stage binding, completion, and failure — with every multi-attribute write atomic and cache-consistent.

## Requirements

### Requirement: QuestRecord is JSON-safe persisted state with three stored states
`world/quests/runtime.py` SHALL define `QuestState` values `IN_PROGRESS`, `COMPLETED`, and `FAILED`, and a
frozen `QuestRecord` containing `quest_id`, `definition_key`, `issuer_key`, `state`, `stage_index`,
`stage_progress`, `deadline_tick`, `accepted_tick`, `stage_room_id`, `objective_target_ids`,
`protected_entity_ids`, `failure_reason`, `tracked`, and `counted_defeat_ids`. Records SHALL be stored as plain
JSON-safe dicts in `PlayerCharacter.db.quest_log`.

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

### Requirement: Tracking state is bounded deterministic quest state
`world/quests/runtime.py` SHALL provide a tracking operation that sets `tracked` on exactly one
record of a character's quest log, validating the whole log through the shared validate-before-
replace lifecycle discipline before any write. Tracking true SHALL be rejected when the target
record is not `in_progress`, and rejected when the character already carries three tracked
`in_progress` records and the target is not already tracked; untracking SHALL always be permitted
for an existing record.

#### Scenario: Tracking up to the cap succeeds
- **WHEN** a holder with two tracked active quests tracks a third active record
- **THEN** exactly that record's `tracked` becomes true and the log round-trips through storage

#### Scenario: The fourth tracked quest is refused
- **WHEN** a holder with three tracked active quests attempts to track a fourth active record
- **THEN** the operation raises the transition error and no record's tracked state changes

#### Scenario: Terminal records cannot be tracked
- **WHEN** tracking true is attempted on a completed or failed record
- **THEN** the operation raises the transition error before any write

#### Scenario: Untracking is always permitted
- **WHEN** a holder untracks a tracked record or untracks an already-untracked record
- **THEN** the operation succeeds idempotently and only that record's state is affected

#### Scenario: A rejected tracking operation changes nothing
- **WHEN** a tracking operation is rejected
- **THEN** it raises the module's transition error and leaves the quest log byte-for-byte unchanged

#### Scenario: Only lifecycle writers assign tracked
- **WHEN** any caller attempts to assign `tracked`
- **THEN** no caller outside the quest lifecycle module and the deterministic core may assign it

### Requirement: Every lifecycle operation validates before replacing the quest log
Every public lifecycle operation SHALL parse and validate every quest-log entry it touches before any
write. A malformed record, unknown active definition, stale stage, out-of-range stage index, progress
exceeding the objective quantity, or invalid state transition SHALL raise a named `QuestDataError` or
`QuestTransitionError` and SHALL leave the complete quest log and all instance pins unchanged.

#### Scenario: Malformed persisted data fails without a partial write
- **WHEN** a quest log contains one malformed dict and an operation targets a different valid record
- **THEN** the operation raises `QuestDataError` and neither record nor any pin is modified

#### Scenario: Missing definition is reported
- **WHEN** an active record references a definition absent from `QUEST_DEFINITION_REGISTRY`
- **THEN** lifecycle access raises `QuestDataError` naming the missing key instead of silently skipping
  or reinterpreting the record

#### Scenario: Duplicate quest ids are rejected
- **WHEN** a quest log contains two records with the same deterministic quest ID
- **THEN** every lifecycle operation raises `QuestDataError` before it mutates any record or pin

#### Scenario: An active record is consistent
- **WHEN** validation inspects an active record
- **THEN** it must reference a known definition whose stage index is in range and still matches, and carry progress within the current objective's quantity

#### Scenario: A terminal record is final
- **WHEN** validation inspects a terminal record
- **THEN** no runtime bindings may remain, and a `FAILED` record must carry its reason

#### Scenario: Success replaces the log list wholesale
- **WHEN** a lifecycle operation succeeds
- **THEN** it persists one replacement quest-log list rather than mutating a nested dict in place

### Requirement: accept_quest creates one deterministic active record
`accept_quest(actor, definition_key, issuer_key)` SHALL reject an unknown definition, reject when the
actor already has an active record for that definition, and reject when
`resolve_issuance(definition_key, issuer_key)` returns no issuance — a record SHALL never be created
pointing at a commission that does not exist. Otherwise it SHALL create an `IN_PROGRESS` stage-zero
record carrying the supplied `issuer_key`.

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
- **WHEN** the previous record for a definition is `COMPLETED` or `FAILED` and the character accepts it
  again
- **THEN** a new active record is stored with the next acceptance number and the terminal history is
  retained

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

### Requirement: abandon_quest fails only an active quest and releases its runtime binding
`abandon_quest(actor, quest_id)` SHALL transition an active record to `FAILED` with
`failure_reason="abandoned"`, clear its runtime bindings, and release its current stage's instance pin.
Calling it again for the same terminal record SHALL be an idempotent no-op returning that record. An
unknown quest ID SHALL raise `QuestNotFound` without mutation.

#### Scenario: Abandonment records failure and releases a pin
- **WHEN** an active bound-instance quest is abandoned
- **THEN** it is failed with reason `abandoned`, its bindings are cleared, and its exact quest pin is
  absent from the room in the same operation

#### Scenario: Repeated abandonment is harmless
- **WHEN** `abandon_quest()` is called twice for the same quest ID
- **THEN** the second call makes no additional state change and does not fail on the already-removed pin

### Requirement: bind_stage_runtime attaches only current-stage instance and entity identities
`bind_stage_runtime(actor, quest_id, *, room=None, objective_targets=(), protected_entities=())` SHALL
accept only an active current stage. A supplied room SHALL be an existing `InstanceRoom`; supplied
entities SHALL be live `LivingEntity` objects. It SHALL persist integer dbrefs, keep objective targets
separate from protected entities, and pin the room with
`quest:<character-id>:<quest-id>:stage:<stage-index>`.

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
Operations that update both a quest log and an instance pin SHALL preflight the complete transition,
perform both writes in one `transaction.atomic()` block, and restore pre-operation Evennia attribute
values if any write raises. No successful exception path SHALL leave only one side changed.

#### Scenario: Pin failure rolls back acceptance or binding
- **WHEN** pin persistence is fault-injected to raise during a runtime binding
- **THEN** the quest record, room pin list, and their in-process attribute values equal their
  pre-operation state

#### Scenario: Quest-log failure restores an already-written pin
- **WHEN** quest-log persistence raises after a pin write
- **THEN** database state and cached room attributes both contain the original pin list

### Requirement: Generated quest definitions resolve after a server restart
The system SHALL restore all generated quest definitions, their issuances, and spawn requirements
from the durable store at startup, before any player quest-log read, so persisted records referencing
generated definitions resolve normally. Restoration SHALL cover both issuer kinds: a guild issuance
SHALL be restored into the guild offer registry and a private commission into the quest issuance
registry, each through its own sole writer.

#### Scenario: Accepted generated quest remains readable after restart
- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** `guild log` and all other quest-log reads succeed and list the accepted quest

#### Scenario: Accepted generated quest remains abandonable after restart
- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** the player can abandon that quest without error

#### Scenario: Restore is idempotent across repeated restarts
- **WHEN** the server restarts multiple times with generated quests in the store
- **THEN** each generated quest is registered exactly once and quest-log reads succeed

#### Scenario: A restored private commission resolves its reward
- **WHEN** the server restarts after a player accepted a generated privately-commissioned quest
- **THEN** that record's issuance resolves, its reward and settlement mode are recoverable, and the
  quest-log read succeeds

### Requirement: Quest lifecycle transitions emit boundary events
Every successful quest lifecycle transition (accept, stage transition,
abandon, complete, fail) SHALL emit one `quest_transition` info event through the `world.observability`
facade at the transition's durable commit point, with `char`, `quest`, `issuer`, `stage_from`, and
`stage_to` context.

#### Scenario: An acceptance event names the governing commission
- **WHEN** a character accepts a definition under a registered issuance and the write commits
  durably
- **THEN** the `quest_transition` event's context carries the accepted record's `issuer_key` as
  `issuer`

#### Scenario: A removal event names the removed record's commission
- **WHEN** a committed log replacement removes a stored record
- **THEN** the `quest_transition` event's context carries that record's stored `issuer_key` as
  `issuer`

#### Scenario: The issuer names the governing commission
- **WHEN** a `quest_transition` event is emitted
- **THEN** `issuer` names the governing commission: new and changed records carry the record's `issuer_key`, and a removed record carries the `issuer_key` of the pre-write stored entry (which the strict diff signature has already validated)

#### Scenario: Rolled-back operations stay silent
- **WHEN** a lifecycle operation rolls back
- **THEN** it MUST NOT emit the `quest_transition` event

#### Scenario: Restore failures surface as warn events
- **WHEN** a best-effort quest-log restore fails
- **THEN** it surfaces as a `rollback_restore_failed` warn event instead of a silent pass

#### Scenario: Instrumentation does not alter semantics
- **WHEN** boundary events are emitted
- **THEN** lifecycle atomicity and validation semantics MUST NOT change

### Requirement: Bound-stage bindings survive every substitution attempt
For a bound-target stage, the record's `objective_target_ids` SHALL be the complete set of individuals
whose defeat counts. Individuals of the same species at other locations, ordinary ambient respawns, and
fresh individuals from a recovered site SHALL never satisfy those bindings, regardless of matching
species or variant identity.

#### Scenario: A recovered site's newcomers do not clear an old hunt
- **WHEN** a bound clearing quest is active, its bound individuals were defeated, and its site later recovers fresh individuals
- **THEN** the old record's progress does not advance from the newcomers, and any newly issued quest binds the newcomers as its own fresh targets

#### Scenario: Ambient respawns never substitute
- **WHEN** an ambient individual of the same species and variant dies while a bound stage is active
- **THEN** the bound stage's progress is unchanged

#### Scenario: Newcomers are bindable only after creation
- **WHEN** a site recovers fresh individuals
- **THEN** those newcomers can only ever be referenced by bindings made after their creation, and site recovery state and quest republish decisions remain mutually consistent
