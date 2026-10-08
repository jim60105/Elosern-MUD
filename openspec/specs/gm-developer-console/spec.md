# gm-developer-console Specification

## Purpose
Provide a protected, recoverable developer console for operator-directed world repair and test setup through validated domain operations and explicit transactional raw editing, separate from player interaction and authored content.

## Requirements

### Requirement: Protected deterministic console boundary

All console routes SHALL reuse landed Developer/superuser access, same-origin session transport, JSON envelopes, CSRF protection on POST, resolver coverage and request/denial events. Only registered owner-backed domain verbs and the server-owned raw editing boundary SHALL apply console state changes; the web layer SHALL validate transport shape and forward without writing persistent fields.

#### Scenario: Access and CSRF matrix
- **WHEN** anonymous, ordinary, Developer and superuser accounts call every console route, and privileged POSTs have missing, invalid or valid CSRF tokens
- **THEN** existing 401 unauthenticated, 403 forbidden and 403 csrf_failed outcomes apply, only privileged valid-token writes reach execution, and every final response has the landed request/access evidence

#### Scenario: Static writer and immutable-reader contracts
- **WHEN** direct web-layer game writes, an unregistered writer call or a reader mutation/import is introduced
- **THEN** the console writer contract or existing S3 reader AST contract fails without exempting readers for the new raw POST

#### Scenario: Offline and authored-data isolation
- **WHEN** the console is used with external generation services offline
- **THEN** local operations remain usable, no authored registry/rulebook/prompt source is written, and game bundle, OOB and /admin/ contracts remain unchanged

#### Scenario: Readers stay immutable
- **WHEN** runtime inspection readers, dashboard GET and recall are exercised
- **THEN** they remain immutable

#### Scenario: Authored-data, AI and bundle isolation guarantees
- **WHEN** the console's isolation guarantees are checked
- **THEN** authored data remains read-only, AI remains unable to apply state, and the isolated GM
  bundle remains operational without LLM/SD services

#### Scenario: Exposed-surface exclusions
- **WHEN** the console's exposed surface is enumerated
- **THEN** arbitrary code execution, typeclass editing, non-Evennia-model raw editing and an audit
  model are not exposed

### Requirement: Tick-conditioned recoverable intervention

Before every dispatched domain verb or raw batch, the console SHALL compare the current in-game tick — read inside the same serialized gameplay boundary that performs the operation — with a process-memory baseline. No baseline after process start, or any difference from it, SHALL require a complete `auto_intervention` save through the existing save subsystem before executing the operation. An unchanged tick SHALL take no new save.

#### Scenario: First write and process restart
- **WHEN** a registered console write is dispatched with no baseline, including the first write after restart with old saves present
- **THEN** an auto_intervention save completes before the operation and the baseline is set to the tick that save represents plus the operation's own advance

#### Scenario: Unchanged and changed ticks
- **WHEN** successive writes occur at the same tick, then player-driven time changes the tick before another write
- **THEN** unchanged-tick writes create no additional save and the changed-tick write creates one before executing

#### Scenario: Console clock advance is absorbed
- **WHEN** advance_clock succeeds and another console write follows without intervening player time
- **THEN** the baseline equals the advanced tick and the next write does not create another save solely because of the GM advance

#### Scenario: Snapshot failure and refusal after save
- **WHEN** required snapshot creation fails, or creation succeeds but the domain operation subsequently rejects
- **THEN** snapshot failure prevents any operation call and retains the prior baseline, while domain refusal leaves game state unchanged, retains the real completed save and reports its identity

#### Scenario: Manual save and no-time player change
- **WHEN** a manual save succeeds, or a player changes state without advancing time after a baseline was recorded
- **THEN** a write at that baseline tick takes no additional save; a failed manual save leaves the baseline unchanged, and the no-time-change case retains the explicitly accepted tick-only trade-off

#### Scenario: Snapshot tick provenance under interleaving
- **WHEN** the live clock advances between a pre-save's database backup and its metadata collection, or a player advances time after a manual save was taken and before the next console write
- **THEN** the save's represented tick and the baseline are the tick the saved database contains, and the later player tick requires a pre-save on the next console write instead of being absorbed

#### Scenario: Serialization contention is refused, not queued
- **WHEN** a console write is dispatched while another snapshot-affecting operation holds the serialization, or a second manual save is attempted while one is running
- **THEN** the console write refuses with `snapshot_failed` and no game write, the manual attempt receives `save_in_progress`, neither is queued into a later success, and the baseline is unchanged

#### Scenario: Unreadable saved world clock
- **WHEN** a completed pre-save's copied database carries no world clock
- **THEN** no live value is substituted, the baseline is left unset so the next console write takes a save, and the operation still reports its real completed save

#### Scenario: Clock-advance absorption detail
- **WHEN** the baseline is recomputed after an executed write attempt
- **THEN** the baseline becomes the tick represented by the save that gated that attempt plus the
  operation's own clock advance — the advanced seconds after a successful in-game clock advance,
  zero otherwise, including for a rejected operation — so a player tick progressed after the gating
  save is never absorbed

#### Scenario: Rejected operation after a completed pre-save
- **WHEN** an operation is rejected after its pre-save completed
- **THEN** it leaves game state unchanged, although the successfully created pre-save remains
  available

#### Scenario: Snapshot failure and serialization refusal semantics
- **WHEN** a snapshot fails, or a console request cannot obtain the serialization it needs
- **THEN** the request returns `snapshot_failed`, leaves the operation unexecuted and the baseline
  unchanged, and does not claim a save was taken

#### Scenario: Manual-save baseline reset
- **WHEN** a manual save succeeds or fails, or a manual-save attempt meets contention
- **THEN** a successful save resets the baseline to the tick its own copied database represents,
  never a later live read; a failed save does not reset it, and a contended attempt keeps its
  existing fail-fast refusal instead of queueing behind a console operation

#### Scenario: Baseline is process-memory only
- **WHEN** the process restarts with old saves present
- **THEN** the baseline was never persisted and is not inferred from old saves

### Requirement: Gameplay-thread serialized console execution

Every console operation SHALL run as one synchronous operation on the gameplay event loop that owns world-state writes, never on the request thread, so that no player action can interleave between its tick check, its state change and any compensation. The pre-save and all snapshot file work SHALL complete on the request thread before that operation.

#### Scenario: Player action cannot interleave with a console operation
- **WHEN** a player inventory or time change is attempted while a console operation is executing on the gameplay event loop
- **THEN** the player change settles entirely before or entirely after the console operation, and no committed player change is lost or resurrected by the operation or by its compensation

#### Scenario: Failed compensation does not clobber a later player change
- **WHEN** a console operation fails and compensates while a player change lands after it
- **THEN** the compensation restores only the state that operation itself touched, the later player change stays committed, and the response and evidence report the refusal truthfully

#### Scenario: No snapshot work on the gameplay event loop
- **WHEN** a console write requires a pre-save
- **THEN** the backup, art mirror and manifest write complete on the request thread before the state change starts, and the operation's own transaction contains no file I/O

#### Scenario: Snapshot work excludes game transactions and the art gate
- **WHEN** snapshot file work runs on the request thread
- **THEN** it runs outside any game transaction and without holding the art gate the gameplay loop
  needs

#### Scenario: Inline execution while the gameplay loop is down
- **WHEN** the gameplay event loop is not running at all — deterministic tests, management commands,
  or a server already shutting down
- **THEN** the operation runs inline on the request thread instead, because no concurrent gameplay
  exists to serialize with

#### Scenario: Nested handoff refuses instead of blocking
- **WHEN** a handoff is attempted from inside a handoff
- **THEN** it refuses with `snapshot_failed` rather than block

#### Scenario: Serialization is taken without waiting
- **WHEN** the console's serialization is acquired
- **THEN** it is taken without waiting — a request that cannot take it refuses rather than queues —
  and the gameplay-thread operation does not take the console's own serialization, so the two can
  never deadlock

### Requirement: Complete validated domain verb batch

The console SHALL expose exactly the approved first batch: `give_item`, `take_item`, `set_wallet`, `set_trait_base`, `set_gauge`, `advance_clock`, `teleport`, `spawn_monster`, `delete_entity`, `set_quest_state`, `set_quest_stage`, `issue_quest`, `retract_memory` and `supersede_memory`. Each SHALL validate argument types, ranges, registry keys, target existence and target kind before its game-state writes.

#### Scenario: Closed registry and verb validation matrix
- **WHEN** every named verb is exercised with valid arguments and each invalid type, range, missing key, missing target and incompatible target-kind case
- **THEN** all fourteen verbs are callable with their specified semantics, every failure has its stable code and no affected game state changes, and an unregistered name is unknown_verb rather than a dynamic import or execution path

#### Scenario: Cascaded failure rollback
- **WHEN** a failure is injected after an initial mutation in each verb, including its dependent settlement or cleanup
- **THEN** persistent rows, Attributes, traits, locations, pins and applicable live registrations match pre-operation state and no success action is reported

#### Scenario: Booleans are rejected as numeric integers
- **WHEN** a numeric integer argument receives a boolean
- **THEN** it is rejected rather than silently treated as an integer

#### Scenario: Failure and atomicity outcomes
- **WHEN** an input is invalid or execution fails
- **THEN** all affected persistent and live cached state is left unchanged and a stable error is
  returned
- **AND** valid operations are all-or-nothing, including cascaded state

### Requirement: Inventory wallet and trait operations

`give_item` and `take_item` SHALL accept a registered item key and positive integer quantity, apply the complete inventory delta and preserve acquisition/quest consequences. The canonical repeated-key inventory SHALL stay authoritative while its existing materialized item objects stay in sync. Taking an equipped item SHALL synchronize its equipment state and gauge limits rather than reject solely because it is equipped.

#### Scenario: Item grant and equipped removal
- **WHEN** registered items are granted in quantity or an equipped item's last held copy is taken
- **THEN** the complete inventory delta and applicable quest progress commit together, and removal updates equipment and gauge limits consistently

#### Scenario: Materialized, key-only and mixed repeated copies
- **WHEN** a key is granted, a key held only as a canonical entry without a contained object is taken, or part of a holding that also has contained objects is taken
- **THEN** the granted key gains exactly one contained object, the key-only removal succeeds without inventing an object, and a partial removal removes only as many contained objects as keys so the canonical key count and the contained objects stay consistent

#### Scenario: Mirror rollback on late failure
- **WHEN** a failure is injected after a granted object was materialized or a taken object deleted
- **THEN** the canonical key list, the contained objects and the live container contents match pre-operation state, with no surplus, missing or stale-cached object

#### Scenario: Invalid economy and numeric input
- **WHEN** wallet receives a negative, fractional or boolean value, an item operation names an unknown key or insufficient quantity, or a trait/gauge value is outside its allowed scale/bounds
- **THEN** the operation returns the applicable validation error and inventory, equipment, gauges, quest consequences and wallet remain unchanged

#### Scenario: True literal trait base
- **WHEN** a target with skill multipliers and disguised stats receives a valid base change
- **THEN** stored true base equals the supplied literal value, derived effects use existing rules, and disguise is neither copied into nor substituted for true traits

#### Scenario: Key materialization and removal synchronization
- **WHEN** a key is granted or taken
- **THEN** granting materializes its contained object, and taking removes one matching held object
  when one exists, so a mixed or key-only holding is never left in a state ordinary drop/give
  refuses and a partial removal never leaves surplus objects

#### Scenario: Wallet, trait and gauge acceptance bounds
- **WHEN** `set_wallet`, `set_trait_base` or `set_gauge` receives a value
- **THEN** `set_wallet` accepts only integer copper at least zero, `set_trait_base` stores a literal
  base within the authoritative trait scale and never a skill-multiplied or disguise value, and
  `set_gauge` changes a known gauge within its authoritative current bounds

#### Scenario: Unknown keys and impossible values reject cleanly
- **WHEN** an unknown item or trait key or an impossible quantity/value is supplied
- **THEN** the operation is rejected without partial writes

### Requirement: Full GM clock settlement

`advance_clock` SHALL accept nonnegative integer seconds within the authoritative single-advance bound and advance the shared world clock using a distinct GM source. It SHALL run the existing full ordered settlement against the applicable world entities and registered world stages, without requiring a bound character or using player time-skip safety gates as a substitute. Settlement failure SHALL restore clock and every touched state surface.

#### Scenario: World-wide settlement and source
- **WHEN** the operator advances valid time with multiple living entities and due world events
- **THEN** all applicable existing settlement stages run in authoritative order with the GM source, the shared clock advances once and no character-local subset is silently omitted

#### Scenario: Boundaries and settlement rollback
- **WHEN** seconds is zero, negative, boolean, fractional, at the maximum bound or above it, or a later settlement stage fails
- **THEN** zero and the valid maximum follow existing clock semantics, invalid values reject without writes, and stage failure restores clock, entity and world-stage state

### Requirement: Map lifecycle verbs with consequences

`teleport` SHALL move a compatible entity to a room with normal departure/arrival consequences for dialogue sessions, party following and instance pins, but no movement time cost. `spawn_monster` SHALL require a valid species/variant pair and room and use authoritative species construction without invented stats. `delete_entity` SHALL invoke Evennia delete hooks and release skip-safety and combat participant registrations.

#### Scenario: Teleport consequences without cost
- **WHEN** an entity with dialogue, companions and instance pins teleports to another room
- **THEN** applicable departure/arrival consequences and pins are consistent at the destination while tick stays unchanged

#### Scenario: Species spawn and placement failure
- **WHEN** a valid species/variant is spawned, or an unknown/mismatched pair, wrong-kind room or placement failure occurs
- **THEN** valid spawn has authoritative species identity/stats in the room and all failed cases leave no partially constructed or placed monster

#### Scenario: Entity deletion lifecycle
- **WHEN** a registered combat or skip-safety participant is deleted
- **THEN** delete hooks execute and its applicable registrations are released, with failure leaving no partial deletion or cleanup

#### Scenario: Deletion is a real delete, not a record wipe
- **WHEN** `delete_entity` runs
- **THEN** it leaves no stale registrations and does not replace deletion with a raw record removal

### Requirement: Quest lifecycle repair and issuance

`set_quest_state` and `set_quest_stage` SHALL update the specified owning character's existing frozen quest record through quest-owned lifecycle operations, using registered definition/state/stage validation, releasing obsolete bindings/pins and creating applicable new bindings/pins. `issue_quest` SHALL validate the registered definition and issuer and create a properly initialized owned record through quest issuance.

#### Scenario: State and stage repair
- **WHEN** a valid existing runtime or generated quest is moved to a valid state or stage
- **THEN** a complete replacement record and its binding/pin consequences commit together under the owning character, using the authoritative definition and settlement rules

#### Scenario: Issuance and invalid lifecycle input
- **WHEN** a registered quest with valid issuer is issued, or an unknown definition, missing record, invalid state/stage/issuer or binding failure is supplied
- **THEN** valid issuance creates a complete initialized record and invalid cases leave the owner's records, bindings, pins and any reward surfaces unchanged

#### Scenario: Repair never fabricates or duplicates
- **WHEN** the console repairs quest lifecycle state
- **THEN** ordinary lifecycle reward/settlement rules remain authoritative, and repair does not
  fabricate unrelated quest structures or duplicate rewards

### Requirement: Append-only memory interventions

`retract_memory` SHALL append a revision making a selected NPC-owned record inactive. `supersede_memory` SHALL link an existing replacement record of the same NPC owner through append-only revisions, refusing a different owner or self-replacement. Original memory content and provenance SHALL remain unchanged; existing effective metadata and owner-generation maintenance SHALL reflect the committed revisions. Raw model rewriting or deletion SHALL NOT be used.

#### Scenario: Retraction and supersession history
- **WHEN** an operator retracts a record or supersedes it with another record owned by the same NPC
- **THEN** the required revision(s) are appended, effective availability/link/history and owner generation update through existing semantics, and original content/provenance remain unchanged

#### Scenario: Invalid replacement and revision rollback
- **WHEN** a record is missing, the target is not NPC-owned, the replacement is itself or belongs to another owner, or the second revision fails
- **THEN** the operation refuses without partial revisions, altered original content, effective metadata or generation changes

### Requirement: Transactional universal Evennia raw editing

A raw write SHALL apply an ordered batch to exactly one existing Evennia object atomically. Supported operations SHALL be `set_attr` with key, optional category and JSON value; `del_attr`; `add_tag` and `remove_tag` with category; and `set_location` without movement settlement.

#### Scenario: Categorized batch and reference round-trip
- **WHEN** an operator sets/deletes categorized Attributes, adds/removes categorized tags and sets location, with object references nested in JSON
- **THEN** the requested ordered changes commit together, categories remain distinct, references become real objects and refreshed data uses the existing S3 serialization

#### Scenario: Batch rollback and forbidden field
- **WHEN** a later operation fails, a reference cannot resolve, an unsupported operation/typeclass change is sent or an unserializable display sentinel is submitted
- **THEN** no part of the batch persists and the current live object handlers remain consistent with rolled-back state

#### Scenario: Raw location bypass
- **WHEN** set_location is used instead of teleport
- **THEN** location changes without movement settlement, dialogue/party/pin repair or movement cost, and the UI continues to identify raw mode as bypassing the rules

#### Scenario: Nested object references resolve
- **WHEN** a raw batch carries nested S3 `{"$ref":"#123"}` values
- **THEN** they resolve to actual existing object references, including S3's optional display
  metadata, and JSON containers and primitives otherwise retain their meaning

#### Scenario: Whole-batch rejection on invalid content
- **WHEN** a batch has an invalid shape or operation, an unresolved or malformed reference, or a
  non-JSON or `$unserializable` sentinel
- **THEN** the whole batch is rejected

#### Scenario: Non-editable displayed fields
- **WHEN** a raw batch targets components, typeclass or other displayed fields
- **THEN** those fields remain non-editable

#### Scenario: Raw bypass scope and retained guarantees
- **WHEN** a raw write executes
- **THEN** it bypasses rule validation and invariant checks, including movement consequences, while
  still requiring access, snapshot policy and transaction safety

### Requirement: Shared console transport results and errors

The portal SHALL expose POST `/gm/api/console/<verb>`, POST `/gm/api/state/object/<dbref>/raw` and read-only GET `/gm/api/console/status`. Failures SHALL retain the standard error object, zh-TW reason and stable code, with snapshot metadata recording any completed pre-save. Clients SHALL branch on code only.

#### Scenario: Routes and reserved status path
- **WHEN** permitted clients GET status, POST a registered/unregistered verb or POST a raw batch
- **THEN** status resolves as a read rather than a verb, only registered verbs dispatch, and write success returns updated state plus truthful save metadata in the landed envelope

#### Scenario: Failure code and save metadata matrix
- **WHEN** each defined domain error occurs before a save or after a completed pre-save
- **THEN** its HTTP status/code and zh-TW message are correct, metadata distinguishes an actual completed save from no save, and no failure claims a successful operation

#### Scenario: Deleted target and world target
- **WHEN** delete_entity or advance_clock succeeds
- **THEN** the response carries the deleted target's identity or updated world-clock state respectively without fabricating an entity read

#### Scenario: Status payload contract
- **WHEN** the status route responds
- **THEN** the payload contains at least `tick`, nullable `baseline_tick` and `will_snapshot`,
  without creating a clock, save or baseline
- **AND** when no world clock exists, `tick` is null and the next write is announced as one that
  would need a save and cannot be submitted

#### Scenario: Write-response metadata contract
- **WHEN** a write is accepted
- **THEN** the response carries real `snapshot: {"taken": bool, "save_id": string|null}` metadata
  and the successful operation's updated target state
- **AND** deleted targets return deletion identity rather than an attempt to read a nonexistent
  object
- **AND** status and pre-execution refusal never claim a snapshot

#### Scenario: Named error codes and statuses
- **WHEN** a defined error occurs
- **THEN** the codes are `unknown_verb` (404), `invalid_argument` (400), `registry_key_not_found`
  (404), `target_not_found` (404), `target_kind_mismatch` (400), `raw_edit_invalid` (400) and
  `snapshot_failed` (500)
- **AND** a write attempted while no world clock exists reports `target_not_found`, and the
  `snapshot_failed` message distinguishes a failed save from a save or console operation already in
  progress

#### Scenario: Retained and unexpected-error statuses
- **WHEN** an access/CSRF/method error or an unexpected execution failure occurs
- **THEN** existing access/CSRF/method errors retain their existing statuses, and unexpected
  execution failures remain visible as HTTP 500 `internal_error`, not relabelled successful or
  validation failures

### Requirement: Contextual portal controls and confirmation

Entity headers SHALL open a 主控台 side drawer containing only applicable verbs. Confirmation SHALL name the operation and display whether the current tick policy predicts a pre-save, explicitly covering the initial no-baseline case. Execution SHALL re-evaluate policy rather than trusting a stale dialog. Cancellation SHALL send no write.

#### Scenario: Entity-kind filtering and raw warning
- **WHEN** character, monster, room, NPC and uncurated object pages are opened and raw edit mode is toggled
- **THEN** only each specified contextual verb set appears, raw editing is available for Evennia objects, and its bypass warning remains visible until edit mode ends

#### Scenario: Memory and world controls
- **WHEN** an NPC memory action or dashboard clock control succeeds
- **THEN** the common confirmation/execution path is used, a result toast appears and memory/history/generation or the world section refreshes without adding polling to runtime pages

#### Scenario: Confirmation freshness and cancellation
- **WHEN** confirmation opens with no baseline, equal tick or differing tick, the game tick changes before submission, or the operator cancels
- **THEN** the displayed notice matches the fetched status, submitted execution uses the actual current policy and real returned save metadata, and cancellation causes no console POST

#### Scenario: Per-kind verb sets in the drawer
- **WHEN** the 主控台 drawer opens
- **THEN** player characters receive item/wallet/trait/gauge/teleport/quest actions, monsters receive
  trait/gauge/teleport/delete actions, and rooms receive spawn_monster

#### Scenario: Raw edit toggle and read-only non-Evennia pages
- **WHEN** the Evennia raw tab is used
- **THEN** it offers an 編輯 toggle with a permanent 繞過規則層 warning throughout edit mode, and
  non-Evennia raw pages remain read-only

#### Scenario: Memory rows and clock control offered
- **WHEN** the portal renders NPC memory rows and the dashboard world section
- **THEN** each NPC memory row offers 撤銷 and 取代, and the dashboard world section offers
  推進時鐘

#### Scenario: Result and failure display
- **WHEN** an operation finishes
- **THEN** results show a toast and refresh the affected section, and failures show code and message

#### Scenario: No extra console routes
- **WHEN** the portal's route table is inspected
- **THEN** no standalone catalogue or placeholder console route was added

### Requirement: Console operational evidence and operator guidance

Every dispatched console operation SHALL emit `gm_action` through the observability facade with operator account, verb or `raw_edit`, target identifiers, bounded argument summary and result in context; completed pre-save identity SHALL be available when taken. Failed snapshots and rejected/execution-failed operations SHALL be visible, not logged as success.

#### Scenario: Success and failure evidence
- **WHEN** a domain verb/raw batch succeeds, rejects or cannot take its required save
- **THEN** the facade records its account, action, target, argument summary and real result/save identity, with no credentials or false committed-success claim

#### Scenario: Complete documentation amendments
- **WHEN** S6 implementation is delivered
- **THEN** both guidance documents describe console-only manual patching and conditional snapshots, AGENTS names every owner/raw path, and authored-source editing and shell bans remain unambiguous

#### Scenario: Facade conventions and freeze-list exclusion
- **WHEN** console events flow through the facade
- **THEN** exceptions follow facade exception rules, context respects credential exclusion and
  one-line truncation, and new production files do not enter the freeze list

#### Scenario: Guidance amendment content
- **WHEN** the implementation amends `AGENTS.md` and `docs/gm/overview.md`
- **THEN** `AGENTS.md` names the four owner console modules and raw boundary, and both documents
  state that manual patching of quest records, money, experience, inventory and combat results
  happens only through the console, with conditional tick-based pre-saves, never a Django shell
- **AND** no experience or combat-result domain verb is implied by that guidance

### Requirement: Complete S6 acceptance and repository contracts

Acceptance SHALL exercise every verb's normal path, every validation failure and injected all-or-nothing failure, and all snapshot cases. Tests SHALL preserve S3 reader immutability and establish web writer dispatch ownership. Fixtures SHALL be deterministic and synthetic, with no live external services.

#### Scenario: Behavioral and static acceptance
- **WHEN** the S6 focused acceptance suites and contracts run
- **THEN** the entire specified behavior matrix is covered, injected failures establish real unchanged state, forbidden writer syntax fails and existing reader contracts remain enforced

#### Scenario: Shard and traceability ownership
- **WHEN** tests are added or main requirements synchronize during implementation/archive
- **THEN** their exact manifests and substantive canonical annotations are updated in the owning change, local contract/traceability checks pass and no skipped, unrelated or placeholder test is offered as coverage

#### Scenario: Acceptance coverage matrix
- **WHEN** the acceptance suite is enumerated
- **THEN** it covers teleport dialogue/party/pins, deletion registrations, full GM clock settlement,
  append-only memory, raw references/atomicity/non-editable typeclass, materialized/key-only/mixed
  item mirrors with late-failure rollback, and all snapshot cases including manual baseline reset,
  snapshot-backed represented-tick provenance, contention refusal and gameplay-thread interleaving
  of a player change with a console operation and with a failed compensation

#### Scenario: Frontend coverage obligations
- **WHEN** the console frontend is tested
- **THEN** Vitest covers entity filtering, warning persistence, confirmation save notice,
  cancellation, result/error display and affected refresh, and every new component has Storybook
  coverage and component-manifest registration

#### Scenario: Shard-owner uniqueness
- **WHEN** new tests are added
- **THEN** every new non-browser Python test module, including those under `web/gm/tests/`, has
  exactly one `.github/evennia-shards.json` owner, and any added browser method/class has exactly
  one `.github/browser-shards.json` owner

#### Scenario: Canonical traceability annotation
- **WHEN** a resulting main requirement gains tests
- **THEN** it has substantive discoverable tests annotated using canonical IDs from the
  traceability tool after spec synchronization, not guessed active-change IDs

#### Scenario: Handoff gate versus CI ownership
- **WHEN** implementation is about to be handed off
- **THEN** focused tests, both lints, local traceability and the contract gate have run, while
  complete managed browser/evidence verification remains CI-owned
