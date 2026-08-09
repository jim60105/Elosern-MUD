# action-resolution-pipeline Specification

## Purpose
TBD - created by archiving change action-resolver. Update Purpose after archive.
## Requirements

### Requirement: ActionResolver exposes side-effect-free preflight for player combat input
`ActionResolver.preflight(request)` SHALL validate skill ownership/kind, current resources, targets,
action capability, effect-handler availability, and time-cost metadata without randomness, effect
staging, EventLog emission, state mutation, or world-time advance. It SHALL return the same named
rejection categories as `resolve()` for those checks. A successful preflight SHALL not guarantee that
state remains valid after earlier initiative actions; final resolution SHALL still run all eight steps.

#### Scenario: Preflight rejection has no side effects
- **WHEN** preflight rejects an unknown skill, insufficient resource, invalid target, blocking buff,
  unknown effect handler, or malformed time metadata
- **THEN** entity, battlefield, quest, session, random-generator, EventLog, and world-clock state are
  unchanged

#### Scenario: Successful preflight does not roll or stage
- **WHEN** a valid damage request passes preflight
- **THEN** no d100 roll occurs, no PendingEffect or EventLog is created, and later `resolve()` performs
  the ordinary complete pipeline once

#### Scenario: Final resolution may reject after initiative state changes
- **WHEN** preflight succeeds and an earlier combatant makes the target invalid before the actor's turn
- **THEN** final resolution returns its ordinary named rejection without claiming that the started round
  is rollback-safe

### Requirement: Nonlethal policy transforms lethal projection before EventLog planners
A validated BattlefieldActionContext MAY carry a deterministic `nonlethal` policy as a
session-wide flag and/or per-entity `nonlethal_keys` (entity keys protected by the policy; in a
hostile session these are the allied companions). During damage
projection, a positive-to-non-positive crossing under the policy SHALL stage HP at 1 and mark the exact
target knocked out; the per-entity key set SHALL apply to the damaged target's key and the
session-wide flag SHALL apply to every target, with the flag unchanged in its existing exam
semantics. Step 7 SHALL emit `target_knocked_out` and SHALL NOT emit `target_defeated`. This
transformation SHALL occur before event-effect planners, so ordinary kill XP, DEFEAT progress,
protected-entity failure, and loot consumers receive no defeat entry. Contexts without the policy SHALL
retain existing lethal behavior.

#### Scenario: Nonlethal projection emits knockout only
- **WHEN** exam damage would cross a target from positive HP to zero or lower
- **THEN** projected and committed HP is 1, knockout identity is staged, `target_knocked_out` is emitted,
  and no `target_defeated` entry exists

#### Scenario: A companion key under the per-entity policy is knocked out
- **WHEN** hostile-session damage would cross a companion from positive HP to zero or lower
- **THEN** the companion's projected and committed HP is 1, `target_knocked_out` is emitted, and no
  `target_defeated` entry exists for the companion

#### Scenario: Hostile targets outside the key set stay lethal
- **WHEN** identical damage in the same hostile session would cross a monster from positive HP to
  zero or lower
- **THEN** the ordinary lethal crossing and `target_defeated` behavior apply to the monster

#### Scenario: Quest and XP planners cannot observe exam defeat
- **WHEN** event-effect planners inspect the completed nonlethal EventLog
- **THEN** none can match ordinary defeat because the log contains only knockout identity

#### Scenario: Ordinary hostile damage is unchanged
- **WHEN** identical damage resolves without a nonlethal policy
- **THEN** the existing lethal HP crossing and target-defeated planner behavior apply
### Requirement: ActionResolver is the sole entry point for every skill invocation
`world/rules/action.py` SHALL provide `ActionResolver.resolve(request: ActionRequest) -> ActionResult`
as the only function through which any skill — active or passive-gated, combat or non-combat — is
invoked. No module under `world/rules/` or `world/skills/` SHALL apply a skill's effects, deduct its
resource cost, or emit an `EventLog` for it through any other code path.

#### Scenario: The out-of-combat command and a combat caller both route through the same function
- **WHEN** `commands/action.py::CmdCast` resolves a skill cast, and a stand-in combat caller (a test
  double satisfying `ActionContext`) resolves a different skill cast
- **THEN** both calls invoke `ActionResolver.resolve()` with an `ActionRequest`, and no other function
  in `world/rules/` or `world/skills/` performs skill-effect application, resource deduction, or
  `EventLog` emission

### Requirement: The pipeline executes design doc §6.1's eight steps in order, each rejecting with a
named reason
`ActionResolver.resolve()` SHALL execute, in order: (1) skill ownership, (2) resource check, (3)
target resolution, (4) action capability, (5) effect resolution, (6) resource deduction, (7)
EventLog construction, (8) time-cost computation. Any step that fails SHALL cause `resolve()` to
return an `ActionResult` with `outcome == "rejected"` and a `reason` drawn from a named
`RejectReason` value — never a bare boolean or an unstructured exception escaping to the caller.
Step 7 SHALL convert a structured damage pending-effect description into a `"roll"` `EventEntry`
and, when the attack hit, a `"damage"` `EventEntry`; it SHALL NOT perform combat math or randomness.
Step 7 SHALL track projected HP in pending-effect order and emit exactly one `"target_defeated"` entry
when damage crosses a living target from positive HP to zero-or-lower. That entry SHALL carry the
target's integer dbref and monster tier or `None`; display keys SHALL remain rendering fields only.
After step 7 constructs the immutable log, registered event-effect planners SHALL derive additional
`PendingEffect` values from that log and request before step 8. Planner failure SHALL reject as
`EVENT_LOG_CONSTRUCTION_FAILED` before commit.

#### Scenario: An unknown skill key rejects at step 1 with a named reason
- **WHEN** `resolve()` is called with a `skill_key` the actor does not own
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.UNKNOWN_SKILL)`

#### Scenario: A PASSIVE skill cannot be cast
- **WHEN** `resolve()` is called with a `skill_key` whose `SkillDef.kind` is `PASSIVE`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.SKILL_NOT_ACTIVE)`

#### Scenario: Insufficient resources reject at step 2
- **WHEN** `resolve()` is called for a skill whose `cost` exceeds the actor's current
  `entity.traits.mp.value` or `entity.traits.sp.value`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.INSUFFICIENT_RESOURCE)`

#### Scenario: A buff that blocks action rejects at step 4
- **WHEN** `resolve()` is called for an actor with an active buff key inside
  `world.rules.buffs.BLOCKING_BUFF_KEYS` (e.g. `paralysis`)
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.ACTION_FORBIDDEN)`

#### Scenario: An unregistered effect ID rejects at step 5, naming the exact ID
- **WHEN** `resolve()` is called for a skill whose `effects` list contains an effect ID whose prefix
  has no registered handler in `_EFFECT_HANDLERS`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.UNKNOWN_EFFECT_ID)` and
  the rejection's `detail` names the exact unresolved effect ID

#### Scenario: A damage effect produces structured roll and damage entries
- **WHEN** a registered damage handler stages `damage|target|73|1|12`
- **THEN** step 7 emits a `"roll"` entry recording raw roll 73 and a `"damage"` entry recording 12
  damage, without rolling or recomputing the hit

#### Scenario: Lethal damage emits stable target identity
- **WHEN** pending damage crosses a target with dbref 42 from positive HP to zero
- **THEN** step 7 emits exactly one `target_defeated` entry containing `target_id=42` and the target's
  threat tier or `None`

#### Scenario: Multiple damage effects use projected HP without duplicate defeat
- **WHEN** one action stages two damage effects against the same initially living target and their
  cumulative projected damage is lethal
- **THEN** step 7 applies both amounts in pending order and emits `target_defeated` only on the first
  positive-to-non-positive crossing

#### Scenario: Miss and nonlethal damage emit no defeat
- **WHEN** an attack misses or leaves projected target HP positive
- **THEN** no `target_defeated` entry is emitted

#### Scenario: A malformed time-cost entry rejects at step 8
- **WHEN** `resolve()` is called for a skill whose `SKILL_TIME_OVERRIDES` entry is a negative integer
- **THEN** it returns
  `ActionResult(outcome="rejected", reason=RejectReason.TIME_COST_LOOKUP_FAILED)`

### Requirement: Resolution is atomic — a failure at any step leaves zero state mutated
`ActionResolver.resolve()` SHALL NOT mutate any entity's `traits`, `sexual`, `buffs`, or
`db.skill_grants` state as a side effect of steps 1 through 8's validation or staging work. All
mutation SHALL occur inside exactly one commit operation, executed only after every one of the eight
steps and every event-effect planner has succeeded. A failure at any step, in a planner, or during the
commit operation SHALL leave every entity referenced by the request, every quest record, and every
instance pin in exactly the state they held before `resolve()` was called.

#### Scenario: A failure injected at any of the eight steps leaves state unchanged
- **WHEN** `resolve()` is called with a fault injected at step 1, 2, 3, 4, 5, 6, 7, or 8 (one scenario
  per step) such that the pipeline rejects
- **THEN** the actor's and every target's `traits`, `sexual`, `buffs`, `db.skill_grants`,
  `db.quest_log`, and instance `db.pin_reasons` values are bitwise identical to their values
  immediately before the call, for every one of the eight fault-injection scenarios

#### Scenario: A failure inside the commit operation rolls back every already-applied effect
- **WHEN** a skill stages three `PendingEffect`s and the second one's `apply()` raises during commit
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=RejectReason.COMMIT_FAILED)`,
  and the mutation the first `PendingEffect` already applied before the second one raised is reversed,
  leaving the touched entity in its pre-commit state

#### Scenario: A failure inside commit reverses action and quest effects
- **WHEN** damage and quest progress are staged together and a later effect raises during commit
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=RejectReason.COMMIT_FAILED)`
  and HP, resources, progression, quest log, and pins all equal their pre-commit state

#### Scenario: Resource deduction and the skill's own effect commit together or not at all
- **WHEN** a skill with a non-zero `cost` stages both its own effect and its resource-deduction
  `PendingEffect`, and the effect's `apply()` raises during commit
- **THEN** the actor's `mp`/`sp` value is unchanged — the resource was never deducted despite step 6
  having already staged the deduction, because the deduction and the effect commit inside the same
  atomic operation

#### Scenario: A rejected action produces no EventLog
- **WHEN** `resolve()` rejects at any step or event-effect planner
- **THEN** the returned `ActionResult` has `event_log is None` and `time_cost_seconds is None`

#### Scenario: An effect handler declaring an unsupported mutation surface is refused, not silently run
- **WHEN** a skill's effect resolves to a `PendingEffect` whose declared `surfaces` includes a value
  outside the exact set `_commit()`'s snapshot/restore mechanism covers
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=
  RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE)` before any entity referenced by the request is touched

#### Scenario: An unsupported planner mutation surface is refused
- **WHEN** an event-effect planner returns a `PendingEffect` declaring a surface outside snapshot and
  restore coverage
- **THEN** the action rejects before any action or quest state is touched

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than the single, explicitly marked `usable_out_of_combat` gate and
the deferred tiered-monster kill-XP staging check. That check MAY inspect whether the caller supplied a
battlefield-backed context solely to stage `grant_combat_kill_xp()` for each unique, resolved `Monster`
target that was initially alive and is reduced to zero HP during the action's atomic commit. All other
combat-vs-non-combat behavior SHALL be expressed entirely through which concrete `ActionContext`
implementation the caller supplies.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

#### Scenario: A battlefield action stages tiered Monster kill XP only
- **WHEN** a battlefield-backed action reduces a resolved `Monster` with a known `threat_tier` from
  positive HP to zero
- **THEN** the action stages exactly one deferred combat-kill XP effect for that target, while a
  non-Monster target with the same `threat_tier` receives no kill-XP effect

#### Scenario: No public callable takes a combat-shaped parameter
- **WHEN** every public callable in `action.py`, `targeting.py`, and `event_log.py` has its signature
  inspected
- **THEN** no parameter is named `in_combat`, `combat_state`, `turn`, or `is_combat`

#### Scenario: Identical code, different ActionContext, different faction outcome
- **WHEN** `ActionResolver.resolve()` is called twice with byte-identical `ActionRequest`s (same actor,
  same `skill_key` whose `SkillDef.faction_constraint` is `FactionConstraint.ENEMY`) differing only in
  which `ActionContext` is supplied — once with `RoomActionContext`, once with a test double whose
  `relation_to()` reports `Relation.ENEMY` for the same target
- **THEN** the `RoomActionContext` call rejects with `RejectReason.TARGET_FACTION_FORBIDDEN` and the
  test-double call succeeds, with no difference in `action.py`'s or `targeting.py`'s executed source
  between the two calls

### Requirement: The effect-resolution registry is open, prefix-keyed, and every handler declares its
mutation surfaces
`world/rules/action.py` SHALL expose `register_effect_handler(prefix, handler, surfaces)` as the only
sanctioned way to add an effect-ID handler, where `surfaces` is the exact set of entity-state surfaces
that handler's staged effects mutate. Step 5 SHALL dispatch purely by looking up an effect ID's prefix
(the substring before its first `:`) in the registry, with no other conditional distinguishing one
effect kind from another. Registration SHALL fail immediately if `surfaces` is not a subset of the
surfaces `_commit()`'s snapshot/restore mechanism covers, and `_commit()` SHALL independently refuse to
run any action whose staged effects declare a surface outside that same set.

#### Scenario: A newly registered handler resolves a previously-unknown prefix
- **WHEN** a test registers a handler for a synthetic prefix not built into this change, declaring
  `surfaces=frozenset({"traits"})`, then resolves a skill whose `effects` list contains an ID with that
  prefix
- **THEN** `resolve()` succeeds and the registered handler's staged effect is committed

#### Scenario: Registering a handler with an unsupported surface fails immediately
- **WHEN** `register_effect_handler()` is called with a `surfaces` value containing a surface outside
  `_commit()`'s snapshot/restore coverage (e.g. `"inventory"`)
- **THEN** it raises `UnsnapshottedSurfaceError` immediately, naming the unsupported surface, before any
  skill can ever reference that prefix

#### Scenario: A handler bypassing registration is still caught at commit time
- **WHEN** a test injects an entry directly into the internal handler-surface mapping (bypassing
  `register_effect_handler()`'s own check) declaring an unsupported surface, then resolves a skill using
  that prefix
- **THEN** `_commit()`'s own independent assertion rejects the action with
  `RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE` before touching any entity, proving the commit-time check
  is not merely decorative alongside the registration-time one

#### Scenario: 統御術's cast-time conferral commits atomically with its own resource cost
- **WHEN** `resolve()` is called for 統御術 (`dominion_art`) targeting a single ally, with
  `event_context` supplying `confer_skill_key`, `confer_scale`, and `confer_trait_keys`
- **THEN** the target's `entity.db.skill_grants` gains exactly one new `ConferredSkillGrant` matching
  those values, and the actor's declared `cost` resources are deducted, in the same successful
  `resolve()` call

#### Scenario: A sexual-magic effect ID rejects cleanly before change 7b exists, and self-arms after
- **WHEN** `resolve()` is called for a skill whose `effects` include a `sexual_event:`-prefixed ID,
  while `world.rules.sexual_transitions` is not importable
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.EFFECT_RESOLUTION_FAILED)`
  with no exception escaping and no state mutated

#### Scenario: A sexual-magic effect ID resolves once change 7b's module exists (self-arming)
- **WHEN** `resolve()` is called for the same skill, guarded by
  `pytest.importorskip("world.rules.sexual_transitions")`, once that module is importable
- **THEN** `resolve()` succeeds and the target's `entity.sexual` reflects `apply_event()`'s effect

### Requirement: Event-effect planners are registered, deterministic, and idempotent by name
`world/rules/action.py` SHALL expose `register_event_effect_planner(name, planner)`. Registration SHALL
replace an existing planner with the same name rather than append a duplicate, supporting repeated
server-start synchronization. Planners SHALL receive the `ActionRequest` and completed `EventLog`,
SHALL perform no writes while planning, and SHALL return only `PendingEffect` values with declared
mutation surfaces. A `quest_log` surface SHALL be owned by a `PlayerCharacter` and snapshot only its
quest-log attribute; an `instance_pin` surface SHALL be owned by an `InstanceRoom` and snapshot only its
pin-reasons attribute. Commit SHALL aggregate surfaces per every `PendingEffect.entity`, including
objects outside the original request, and dispatch snapshot/restore by surface rather than assuming
every touched object is a `LivingEntity`.

#### Scenario: Repeated quest planner registration does not duplicate progress
- **WHEN** startup registers the quest planner twice and one matching lethal action succeeds
- **THEN** the objective advances once

#### Scenario: Quest planner stages without mutating
- **WHEN** the quest planner returns progress effects but step 8 subsequently rejects a malformed time
  cost
- **THEN** the quest log and pins remain unchanged, proving the planner only staged its result

#### Scenario: Cross-request player and room effects restore by surface
- **WHEN** protected-entity death stages quest-log and pin effects for two quest owners outside the
  original request and the second owner's write fails
- **THEN** both players' quest logs, both rooms' pin lists, target HP, and actor state are restored

### Requirement: Every production skill path receives registered event-effect planning automatically
Because out-of-combat casting and combat turns both call `ActionResolver.resolve()`, a successful action
SHALL execute all registered planners regardless of caller. `CmdCast`, `run_round`, and overwhelm combat
SHALL NOT need a separate quest observer call, and SHALL NOT bypass planner execution.

#### Scenario: Out-of-combat cast runs the planner
- **WHEN** `CmdCast` successfully resolves a quest-relevant action
- **THEN** its registered quest effects commit before the command renders the returned EventLog

#### Scenario: Combat round runs the planner
- **WHEN** `run_round()` resolves a lethal player action
- **THEN** matching quest progress commits before that EventLog is appended to the round result

#### Scenario: Direct resolver use has identical behavior
- **WHEN** a deterministic test or future subsystem calls `ActionResolver.resolve()` directly
- **THEN** registered planners run exactly as they do for command and combat callers

### Requirement: ActionResolver exposes shared side-effect-free action preview
The deterministic rules layer SHALL expose a frozen preview query factored from the same pure checks used by `ActionResolver.preflight()`. Given an actor, skill, context, and optional candidate, it SHALL report enabled state, the exact stable rejection reason and resource detail when disabled, and valid targets or applicable AREA shorthands. It SHALL cover ownership and active kind, current resources, exact target shape, presence, alive state, range, faction, action-blocking buffs, `actions_per_turn == 0`, registered effect prefixes, and time metadata. Modifier evaluation SHALL read a no-create context from existing stored buff and sexual-state data and SHALL NOT materialize a lazy handler or default. Preview SHALL NOT roll randomness, stage or apply effects, construct EventLogs, invoke event-effect planners, mutate any persistent or nonpersistent game state, or advance world time. `preflight()` and final `resolve()` SHALL remain authoritative and SHALL rerun their required checks.

#### Scenario: Preview has no side effects
- **WHEN** previews are built for every owned active skill and every current combat participant
- **THEN** traits, resources, buffs, sexual state, battlefield state, session record, quest state, random source, EventLogs, and world clock are unchanged

#### Scenario: Preview reuses a named resolver rejection
- **WHEN** an active skill costs more MP than the actor currently has
- **THEN** preview reports disabled with `RejectReason.INSUFFICIENT_RESOURCE` and MP detail, matching preflight without executing an effect

#### Scenario: Zero-action state is authoritative before initiative
- **WHEN** deterministic combat modifiers set the player actor's `actions_per_turn` to zero
- **THEN** preview and player-session submission report `RejectReason.ACTION_FORBIDDEN` before initiative while `run_round()` retains its existing skip behavior for an NPC or a post-preflight state change

#### Scenario: Preview does not materialize sexual state
- **WHEN** an actor has a stored sexual baseline but no materialized sexual trait handler and combat preview is built
- **THEN** modifier matching is interpreted in memory and no sexual trait Attribute or default handler state is created

#### Scenario: Target previews use ordinary ordered validation
- **WHEN** candidate previews are requested for a SINGLE or AREA skill
- **THEN** candidate acceptance and rejection use the same presence, alive, range, and faction functions and ordering as final target resolution
