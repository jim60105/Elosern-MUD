# action-resolution-pipeline Specification

## Purpose
Defines ActionResolver as the sole entry point for every skill invocation, running the design doc's eight resolution steps in fixed order with atomic commit semantics so a failure at any step leaves zero state mutated. Covers the side-effect-free preflight and preview surfaces, the nonlethal policy applied before event-effect planning, the open prefix-keyed effect-handler registry, and the boundary event emitted on successful commits.

## Requirements

### Requirement: ActionResolver exposes side-effect-free preflight for player combat input
`ActionResolver.preflight(request)` SHALL validate skill ownership/kind, current resources, targets,
action capability, declared actor/target state and contact conditions, nonempty effect audiences, effect-handler availability, and time-cost metadata without randomness, effect
staging, EventLog emission, state mutation, or world-time advance. It SHALL return the same named
rejection categories as `resolve()` for those checks.

#### Scenario: Preflight rejection has no side effects
- **WHEN** preflight rejects an unknown skill, insufficient resource, invalid target, blocking buff,
  unmet state/contact condition, empty delivery audiences, unknown effect handler, or malformed time metadata
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

#### Scenario: Successful preflight does not guarantee later validity
- **WHEN** a preflight succeeds and the world state evolves before the actor acts
- **THEN** a successful preflight does not guarantee that state remains valid after earlier
  initiative actions
- **AND** final resolution still runs all eight steps

### Requirement: Nonlethal policy transforms lethal projection before EventLog planners
A validated BattlefieldActionContext MAY carry a deterministic `nonlethal` policy as a
session-wide flag and/or per-entity `nonlethal_keys`. Under the
policy, a positive-to-non-positive damage crossing SHALL stage HP at 1 and mark the exact target
knocked out; step 7 SHALL emit `target_knocked_out` and SHALL NOT emit `target_defeated`. This
transformation SHALL occur before event-effect planners. Contexts without the policy SHALL
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

#### Scenario: Policy keys protect entities, companions in hostile sessions
- **WHEN** a nonlethal policy declares per-entity `nonlethal_keys`
- **THEN** those entity keys are the entities protected by the policy, and in a hostile session they
  are the allied companions

#### Scenario: Key set and session-wide flag scopes of application
- **WHEN** damage is projected under a nonlethal policy
- **THEN** the per-entity key set applies to the damaged target's key and the session-wide flag
  applies to every target
- **AND** the flag is unchanged in its existing exam semantics

#### Scenario: Defeat consumers receive no defeat entry
- **WHEN** the transformation occurs before event-effect planners
- **THEN** DEFEAT progress, protected-entity failure, and loot consumers receive no defeat entry

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

#### Scenario: MP cost payment to zero is a routed attributed deduction, not a rejection
- **WHEN** `resolve()` completes a cast whose adjusted MP cost equals the caster's entire remaining MP
- **THEN** the staged deduction applied the change through the canonical MP writer with the cast skill
  as the event source, the commit succeeded, and a rule qualified to that source observes the crossing

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

#### Scenario: Step 6 pays mp through the canonical MP-change writer
- **WHEN** step 6 deducts an `mp` resource cost
- **THEN** the deduction is applied through the canonical MP-change writer as the staged pending
  effect's committed behavior, carrying the cast skill as the MP-event source
- **AND** hp and sp deduction behavior and the preflight/recheck amount agreement stay unchanged

#### Scenario: MP cost payment to zero is a depletion fact, not a rejection
- **WHEN** an MP crossing to zero is caused by cost payment
- **THEN** it is an ordinary attributed depletion fact, never a new rejection reason

#### Scenario: Step 7 converts damage descriptions without combat math
- **WHEN** step 7 processes a structured damage pending-effect description
- **THEN** it converts it into a `"roll"` `EventEntry` and, when the attack hit, a `"damage"`
  `EventEntry`, performing no combat math and no randomness

#### Scenario: Defeat-entry display keys are rendering-only
- **WHEN** a `target_defeated` entry is constructed
- **THEN** display keys remain rendering fields only

#### Scenario: Planners derive effects from the immutable log before step 8
- **WHEN** step 7 constructs the immutable log
- **THEN** registered event-effect planners derive additional `PendingEffect` values from that log
  and the request before step 8

#### Scenario: Planner failure rejects before commit
- **WHEN** an event-effect planner fails
- **THEN** the action rejects as `EVENT_LOG_CONSTRUCTION_FAILED` before commit

### Requirement: Resolution is atomic — a failure at any step leaves zero state mutated
`ActionResolver.resolve()` SHALL NOT mutate any entity's `traits`, `sexual`, `buffs`, or
`db.skill_grants` state as a side effect of steps 1 through 8's validation or staging work. All
mutation SHALL occur inside exactly one commit operation, executed only after every one of the eight
steps and every event-effect planner has succeeded.

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

#### Scenario: Any failure leaves every referenced object at its pre-call state
- **WHEN** `resolve()` fails at any step, in an event-effect planner, or during the commit operation
- **THEN** every entity referenced by the request, every quest record, and every instance pin is left
  in exactly the state it held before `resolve()` was called

### Requirement: A damaging action never resolves without a battlefield
`world/rules/action.py` SHALL declare `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, and
`world/rules/player_messages.py` SHALL supply its Traditional Chinese player-facing line.
`ActionResolver`'s capability step SHALL reject a request with that reason when the resolved
`SkillDef`'s parsed `effects` carry at least one `world.skills.effects.DamageEffect` **and**
`request.context.battlefield is None`.

#### Scenario: A damaging skill permitted outside combat is still refused without a battlefield
- **WHEN** `ActionResolver.resolve()` is called for a skill declaring `usable_out_of_combat=True`
  whose effects include `damage:<element>:<school>`, with a `RoomActionContext`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)`,
  no resource is deducted, no roll is made, no effect is staged, and no clock is read

#### Scenario: The same skill resolves normally with a battlefield
- **WHEN** the identical request is resolved with a `BattlefieldActionContext` instead
- **THEN** the gate does not fire and resolution proceeds through the ordinary pipeline

#### Scenario: A non-damaging skill outside combat is unaffected
- **WHEN** a skill declaring `usable_out_of_combat=True` with no `DamageEffect` among its effects is
  resolved with a `RoomActionContext`
- **THEN** the gate does not fire and resolution proceeds exactly as before this change

#### Scenario: Indirect hp movement is not damage for this gate
- **WHEN** a skill declaring `usable_out_of_combat=True` whose effects include a drain that moves a
  target's pleasure into the caster's own hp, mp, and sp, but no `DamageEffect`, is resolved with a
  `RoomActionContext`
- **THEN** the gate does not fire

#### Scenario: The shared preview reports the same stable reason
- **WHEN** the shared preview query is asked about a damaging, out-of-combat-permitted skill with a
  `RoomActionContext`
- **THEN** it reports disabled with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, agreeing with
  `ActionResolver.preflight()` for the identical request

#### Scenario: The gate is evaluated per request, never from a catalog snapshot
- **WHEN** the gate's implementation is inspected
- **THEN** its condition is computed from the resolved `SkillDef`'s own effects and the request's own
  context, with no enumeration of registry keys and no dependence on how many skills currently
  declare `usable_out_of_combat=True`

#### Scenario: Preview, revalidation, and resolution cannot disagree
- **WHEN** the shared predicate is consumed by `ActionResolver` and `world/rules/action_preview.py`
- **THEN** preview, combat-session submission revalidation, and authoritative resolution cannot
  disagree
- **AND** the condition is expressed as one shared predicate over the skill definition and the
  context, consumed by both `ActionResolver` and `world/rules/action_preview.py`

#### Scenario: The reason name coincides with the tested condition
- **WHEN** the reason's name is read against the condition it tests
- **THEN** the name states the player-facing rule while the condition tests for the battlefield's
  absence: from exploration the only way to obtain a battlefield is to open combat on a co-located
  monster, so the two coincide, and the resolver stays free of any typeclass dependency

#### Scenario: Indirect hp movement never satisfies the condition
- **WHEN** a skill carries a `SexualDrainEffect` but no `DamageEffect`
- **THEN** indirect hp movement does not satisfy the condition — it is not a damaging action for this
  gate, matching `overwhelm-threshold`'s `commanded_damage_reaches_enemy()` so both damage-shaped
  questions in the codebase read the same definition

#### Scenario: The rejection precedes every surface touch
- **WHEN** the gate rejects a request
- **THEN** the rejection occurs before any resource is spent, before `roll_d100()` is called, before
  any `PendingEffect` is staged, and before any world-clock access, so a refused request touches no
  surface and persists nothing

### Requirement: The out-of-combat gates fire in a fixed, specified order
`ActionResolver`'s capability step SHALL evaluate the `usable_out_of_combat` gate **before** the
damaging-action gate. A skill that does not declare `usable_out_of_combat` SHALL therefore continue
to reject with `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT` outside combat, whether or not it
carries a `DamageEffect`; `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` SHALL be reachable only for
skills the registry does permit outside combat.

#### Scenario: An unflagged damage skill still reports the flag rejection
- **WHEN** a skill carrying a `DamageEffect` and declaring `usable_out_of_combat=False` is resolved
  with a `RoomActionContext`
- **THEN** the reason is `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, not
  `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`

#### Scenario: Preview agrees with resolve on which of the two reasons applies
- **WHEN** the shared preview and `ActionResolver.preflight()` are both asked about an unflagged
  damage skill, and then about a flagged one, each with a `RoomActionContext`
- **THEN** both report `SKILL_NOT_USABLE_OUT_OF_COMBAT` for the first and
  `DAMAGE_REQUIRES_MONSTER_TARGET` for the second

#### Scenario: Preview evaluates the two conditions in the same order
- **WHEN** `world/rules/action_preview.py` evaluates the `usable_out_of_combat` and damaging-action
  conditions
- **THEN** it evaluates the two conditions in the same order as `ActionResolver`

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than exactly two explicitly marked gates: the
`usable_out_of_combat` gate, and the damaging-action gate that rejects a `DamageEffect`-carrying
skill when `request.context.battlefield is None`. Both SHALL be marked as such at their sites, and
both SHALL read the context's battlefield rather than any combat-state token.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

#### Scenario: Exactly the two sanctioned gates exist
- **WHEN** `world/rules/action.py` and `world/rules/targeting.py` are inspected for conditionals
  reading `context.battlefield`
- **THEN** the only such conditionals distinguishing combat from non-combat behavior are the
  `usable_out_of_combat` gate and the damaging-action gate, each marked at its site

#### Scenario: A battlefield defeat stages events and planners only
- **WHEN** a battlefield-backed action reduces a resolved `Monster` with a known `threat_tier` from
  positive HP to zero
- **THEN** the action stages the defeat EventLog entry (carrying `monster_tier`) and the
  event-effect planners derived from it, and no progression effect of any kind

#### Scenario: No public callable takes a combat-shaped parameter
- **WHEN** every public callable in `action.py`, `targeting.py`, and `event_log.py` has its signature
  inspected
- **THEN** no parameter is named `in_combat`, `combat_state`, `turn`, or `is_combat`

#### Scenario: Identical code, different ActionContext, different faction outcome
- **WHEN** `ActionResolver.resolve()` is called twice with byte-identical `ActionRequest`s (same actor,
  same `skill_key` whose `SkillDef.faction_constraint` is `FactionConstraint.SELF_ONLY`) differing only in
  which `ActionContext` is supplied — once with `RoomActionContext`, once with a test double whose
  `relation_to()` reports `Relation.SELF` for the same target
- **THEN** the `RoomActionContext` call rejects with `RejectReason.TARGET_FACTION_FORBIDDEN` and the
  test-double call succeeds, with no difference in `action.py`'s or `targeting.py`'s executed source
  between the two calls

#### Scenario: Remaining behavior comes from the supplied ActionContext
- **WHEN** any other combat-vs-non-combat behavior is needed
- **THEN** it is expressed entirely through which concrete `ActionContext` implementation the caller
  supplies

### Requirement: The effect-resolution registry is open, prefix-keyed, and every handler declares its
mutation surfaces
`world/rules/action.py` SHALL expose `register_effect_handler(prefix, handler, surfaces)` as the only
sanctioned way to add an effect-ID handler, where `surfaces` is the exact set of entity-state surfaces
that handler's staged effects mutate. Step 5 SHALL dispatch purely by looking up an effect ID's prefix
(the substring before its first `:`) in the registry, with no other conditional distinguishing one
effect kind from another.

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

- **WHEN** `resolve()` is called for 統御術 (`dominion_art`) targeting a single ally, with an
  `event_context` carrying no conferral keys, by a caster who directly owns conferrable passives
  declared at the node's coefficient
- **THEN** the target's `entity.db.skill_grants` gains one `ConferredSkillGrant` per derived skill at
  the node's declared scale, and the actor's declared `cost` resources are deducted, in the same
  successful `resolve()` call

#### Scenario: A sexual-magic effect ID rejects cleanly before change 7b exists, and self-arms after

- **WHEN** `resolve()` is called for a skill whose `effects` include a `sexual_event:`-prefixed ID,
  while `world.rules.sexual_transitions` is not importable
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.EFFECT_RESOLUTION_FAILED)`
  with no exception escaping and no state mutated

#### Scenario: A sexual-magic effect ID resolves once change 7b's module exists (self-arming)

- **WHEN** `resolve()` is called for the same skill, guarded by
  `pytest.importorskip("world.rules.sexual_transitions")`, once that module is importable
- **THEN** `resolve()` succeeds and the target's `entity.sexual` reflects `apply_event()`'s effect

#### Scenario: Registration rejects surfaces beyond snapshot coverage
- **WHEN** `register_effect_handler()` is called with `surfaces` that is not a subset of the surfaces
  `_commit()`'s snapshot/restore mechanism covers
- **THEN** registration SHALL fail immediately

#### Scenario: Commit independently refuses uncovered surfaces
- **WHEN** `_commit()` would run an action whose staged effects declare a surface outside the
  snapshot/restore-covered set
- **THEN** `_commit()` independently refuses to run that action

### Requirement: Event-effect planners are registered, deterministic, and idempotent by name
`world/rules/action.py` SHALL expose `register_event_effect_planner(name, planner)`. Registration SHALL
replace an existing planner with the same name rather than append a duplicate, supporting repeated
server-start synchronization. Planners SHALL receive the `ActionRequest` and completed `EventLog`,
SHALL perform no writes while planning, and SHALL return only `PendingEffect` values with declared
mutation surfaces.

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

#### Scenario: Surface ownership and snapshot scope
- **WHEN** a planner returns effects on the `quest_log` or `instance_pin` surface
- **THEN** a `quest_log` surface is owned by a `PlayerCharacter` and snapshots only its quest-log
  attribute, and an `instance_pin` surface is owned by an `InstanceRoom` and snapshots only its
  pin-reasons attribute

#### Scenario: Commit aggregates surfaces per PendingEffect entity
- **WHEN** commit runs over staged effects
- **THEN** it aggregates surfaces per every `PendingEffect.entity`, including objects outside the
  original request, and dispatches snapshot/restore by surface rather than assuming every touched
  object is a `LivingEntity`

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
The deterministic rules layer SHALL expose a frozen preview query factored from the same pure checks used by `ActionResolver.preflight()`. Given an actor, skill, context, and optional candidate, it SHALL report enabled state, the exact stable rejection reason and resource detail when disabled, and valid targets or applicable AREA shorthands.

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

#### Scenario: A prerequisite-unsatisfied owned skill is disabled in preview
- **WHEN** an actor owns `firestorm` but its `scorching_wave` practice level is below the edge threshold
- **THEN** preview reports disabled with `RejectReason.UNKNOWN_SKILL` naming the skill key, submission revalidation agrees, and the shared combat view renders the descriptor unavailable

#### Scenario: Meeting the edge exactly enables the preview
- **WHEN** the same actor's `scorching_wave` level reaches exactly the edge threshold
- **THEN** preview, revalidation, and preflight all report the skill enabled (when other checks pass)

#### Scenario: Target previews use ordinary ordered validation
- **WHEN** candidate previews are requested for a SINGLE or AREA skill
- **THEN** candidate acceptance and rejection use the same presence, alive, range, and faction functions and ordering as final target resolution

#### Scenario: The shared combat view marks an unaffordable spell disabled
- **WHEN** the combat view (`build_combat_view`) is built for an actor who owns a spell whose MP cost exceeds their current MP
- **THEN** the spell's descriptor carries `enabled == False` and the MP resource reason code, so both the Telnet `combat actions` command and the WebClient combat panel render it unavailable

#### Scenario: Preview covers the full check set
- **WHEN** a preview is evaluated
- **THEN** it covers ownership and active kind, current resources, exact target shape, presence,
  alive state, range, faction, action-blocking buffs, `actions_per_turn == 0`, registered effect
  prefixes, time metadata, and lineage eligibility

#### Scenario: Lineage eligibility rides the single shared predicate
- **WHEN** preview checks lineage eligibility
- **THEN** it uses the single shared side-effect-free predicate `can_use_skill` — the same predicate
  consumed by `ActionResolver`, the skill menus, and the deterministic AI policy — so preview,
  submission revalidation, and authoritative preflight agree on the same eligibility
- **AND** a prerequisite-unsatisfied skill reports `RejectReason.UNKNOWN_SKILL` with the skill key

#### Scenario: Submission revalidation applies the same checks
- **WHEN** the combat-session submission revalidation path runs
- **THEN** the same checks apply, so a rejected submission stops before initiative

#### Scenario: Modifier evaluation reads a no-create context
- **WHEN** preview evaluates modifiers
- **THEN** it reads a no-create context from existing stored buff and sexual-state data and does not
  materialize a lazy handler or default

#### Scenario: Preview performs no side-effecting work
- **WHEN** a preview is built
- **THEN** it does not roll randomness, stage or apply effects, construct EventLogs, invoke
  event-effect planners, mutate any persistent or nonpersistent game state, or advance world time

#### Scenario: Preflight and resolve stay authoritative
- **WHEN** preview has reported a result
- **THEN** `preflight()` and final `resolve()` remain authoritative and rerun their required checks

### Requirement: Preflight rejects missing handler context before any round cost

`ActionResolver.preflight()` and the combat-session revalidation SHALL verify that every effect handler's declared context keys are present in the submitted `event_context`; a missing key SHALL reject the action before initiative, round count, upkeep, or world time changes.

#### Scenario: Missing disguise context rejects before initiative

- **WHEN** a player submits `status_disguise` in combat without `event_context.disguise`
- **THEN** the action is rejected at preflight, no round is consumed, and the enemy does not act

#### Scenario: Missing dominion context rejects before initiative

- **WHEN** a player submits `dominion_art` in combat while owning no skill that passes the
  conferrability shape validation, with an `event_context` carrying no conferral keys (the scale and
  the conferred set are now derived from the caster's own ownership and the node's policy, so the
  old required-context keys no longer exist)
- **THEN** the action is rejected at preflight with `EFFECT_RESOLUTION_FAILED`, no round is consumed,
  and the enemy does not act

#### Scenario: Out-of-combat casts with supplied context still work

- **WHEN** a player casts `status_disguise` out of combat with the disguise context supplied by the command
- **THEN** the cast resolves normally

### Requirement: ActionRequest carries an optional scale modifier and a new rejection category
The frozen `ActionRequest` dataclass SHALL gain a `scale: float = 1.0` field. `1.0` SHALL remain the
behavior-preserving default for every existing construction site (the field is never required, and a
request with `scale == 1.0` behaves exactly as before this change). `RejectReason` SHALL gain the
member `SCALED_CAST_FORBIDDEN` for the freeform-casting gate.

#### Scenario: Existing requests default to scale one
- **WHEN** an `ActionRequest` is constructed without a `scale` argument, and a pre-existing request
  construction is replayed
- **THEN** its `scale` equals `1.0` and resolution behaves identically to the pre-change behavior

#### Scenario: Scale reaches the resource steps and the handlers
- **WHEN** a request carries `scale == 2.0` and resolves successfully
- **THEN** step 2 and step 6 both read `_adjusted_costs(actor, skill, scale)` and compare and deduct
  the scaled MP cost, the registered effect handlers receive the request's scale, and the pipeline
  still commits exactly one atomic operation

#### Scenario: The rejection category is available
- **WHEN** the freeform gate rejects a request
- **THEN** the `ActionResult` carries `reason == RejectReason.SCALED_CAST_FORBIDDEN` and the ordinary
  rejected result shape (no event log, no time cost)

#### Scenario: Every handler accepts the scale argument
- **WHEN** the single step-5 call site invokes a registered effect handler
- **THEN** every registered effect handler accepts a `scale: float` argument (last position), and
  handlers that do not scale magnitudes ignore it

#### Scenario: Resource costs read the request's scale
- **WHEN** step 2 and step 6 read resource costs
- **THEN** the resource-cost read is `_adjusted_costs(actor, skill, scale=1.0)` and both steps pass
  the request's scale to it, so preflight and deduction always compare and deduct the same scaled
  amount

#### Scenario: Pipeline shape properties are unchanged
- **WHEN** the scale field and rejection category are added
- **THEN** no step count, ordering, or atomicity property of the pipeline changes

### Requirement: Successful commits emit an action_commit boundary event

Every deterministic action commit path in `world/rules/action.py` SHALL emit
one `action_commit` info event through the `world.observability` facade after
the durable commit, with `char`, `action`, and `ms` context. Failed or
rolled-back resolutions MUST NOT emit the event. Boundary events MUST NOT
change the all-or-nothing resolution semantics.

#### Scenario: A resolved action leaves one commit event

- **WHEN** an action resolution commits successfully
- **THEN** exactly one `action_commit` event is logged with the actor, the
  action identity, and elapsed milliseconds

#### Scenario: A rolled-back resolution emits no commit event

- **WHEN** resolution fails after staging and the transaction rolls back
- **THEN** no `action_commit` event is logged for that attempt

### Requirement: Audience planning agrees between preflight and final resolution
Audience planning SHALL be side-effect-free and use authoritative current relationships. A nonempty selected pool with an empty component audience SHALL skip only that component without rolling. If all effect audiences are empty, the cast SHALL reject before resource, time or practice changes. Final resolution SHALL repeat audience validation after initiative changes.

#### Scenario: One audience is empty
- **WHEN** an authored mixed spell has allies in its selection but no enemies
- **THEN** ally recovery resolves, damage does not roll and the cast pays once

#### Scenario: All audiences are empty
- **WHEN** every configured component has no valid recipient
- **THEN** the action is rejected without consuming MP, time or practice

#### Scenario: Final relationships change
- **WHEN** preflight succeeds but relationship state changes before execution
- **THEN** final delivery uses the current authoritative relationship, not the preview

#### Scenario: Late error restores recipients
- **WHEN** a mixed effect cast fails after effects have started applying
- **THEN** all actual recipients including an explicitly bound actor are restored

#### Scenario: A gated component filters without affecting siblings
- **WHEN** preflight plans one ungated component and one gauge-state-gated component over a mixed
  target pool, and a gated target's stored state changes before execution
- **THEN** the ungated component's recipients are unchanged by the gate, the gated component follows
  the current stored state in final planning, and an all-empty gated audience still leaves the cast
  payable via its ungated components

#### Scenario: An audience condition filters through the target-state gate
- **WHEN** a component declares an audience condition
- **THEN** planning additionally filters that component's recipients by the validated target-state
  gate evaluated from stored state, with no handler materialization and no rolls, skipping only the
  gated component for non-matching targets
- **AND** preflight and final resolution evaluate the identical gate against current state

#### Scenario: Delivery keeps its transaction and attribution guarantees
- **WHEN** audience planning completes and delivery proceeds
- **THEN** delivery retains the existing transaction and event attribution guarantees

### Requirement: The church-rite effect handlers reject with four named stable reasons
`world/rules/action.py`'s `RejectReason` SHALL declare `RITE_NOT_ENROLLED`, `RITE_COOLDOWN_ACTIVE`,
`RITE_OUTSIDE_VENUE`, and `RITE_ALREADY_SHELTERED`, and `world/rules/player_messages.py` SHALL
supply each one's Traditional Chinese player-facing line.
The two holy-rite effect handlers SHALL raise `RejectedAction` with these reasons during step-5
staging, before any `PendingEffect` is staged.

#### Scenario: An unenrolled caster is refused with the named reason and zero writes
- **WHEN** an entity with no `db.church` ledger casts `rite_martial_blessing` out of combat
- **THEN** `resolve()` returns `outcome == "rejected"` with
  `reason == RejectReason.RITE_NOT_ENROLLED`, and traits, buffs, and the clock are byte-identical

#### Scenario: A cooled-down blessing is refused before staging
- **WHEN** an enrolled holder casts `rite_martial_blessing` while her ledger cooldown stamp is inside
  the `church.yaml` cooldown window
- **THEN** the result carries `RejectReason.RITE_COOLDOWN_ACTIVE` and stages nothing — no buff, no
  re-stamped ledger, no clock access

#### Scenario: Shelter outside a sanctuary venue is refused
- **WHEN** an enrolled holder casts `rite_shelter` in a place without the `church` flag
- **THEN** the result carries `RejectReason.RITE_OUTSIDE_VENUE` and no trait or ledger state moves

#### Scenario: The second same-day shelter is refused
- **WHEN** an enrolled holder already marked this day's shelter block and casts `rite_shelter` again
  inside the venue
- **THEN** the result carries `RejectReason.RITE_ALREADY_SHELTERED` and hp, sp, and the ledger are
  byte-identical

#### Scenario: Every rite rejection renders a fixed zh-TW line
- **WHEN** each of the four reasons is rendered through the player-message surface
- **THEN** each maps to its configured Traditional Chinese line, with no raw enum or exception text
  reaching the player

#### Scenario: Unenrolled casting raises RITE_NOT_ENROLLED
- **WHEN** the actor's `db.church` ledger is absent
- **THEN** the holy-rite handler raises `RejectedAction` with `RITE_NOT_ENROLLED` during step-5
  staging, before any `PendingEffect` is staged

#### Scenario: Cooldown-window casting raises RITE_COOLDOWN_ACTIVE
- **WHEN** `rite_martial_blessing`'s ledger cooldown stamp is inside its rulebook cooldown window
- **THEN** the handler raises `RejectedAction` with `RITE_COOLDOWN_ACTIVE` during step-5 staging,
  before any `PendingEffect` is staged

#### Scenario: Casting shelter outside a venue raises RITE_OUTSIDE_VENUE
- **WHEN** `rite_shelter` resolves outside a church-flagged place
- **THEN** the handler raises `RejectedAction` with `RITE_OUTSIDE_VENUE` during step-5 staging,
  before any `PendingEffect` is staged

#### Scenario: Already-sheltered day raises RITE_ALREADY_SHELTERED
- **WHEN** `rite_shelter` resolves with the current day-block already marked
- **THEN** the handler raises `RejectedAction` with `RITE_ALREADY_SHELTERED` during step-5 staging,
  before any `PendingEffect` is staged

#### Scenario: Rite rejections keep the zero-write promise
- **WHEN** any of the four rite rejections fires
- **THEN** it leaves every surface byte-identical and advances no clock, matching the pipeline's
  existing zero-write rejection promise

#### Scenario: The rite gates live in the handlers, not the preview
- **WHEN** the placement of the rite gates is inspected
- **THEN** they live in the handlers (step 5), not the shared preview: `world/rules/action_preview.py`
  keeps mirroring only the pre-staging steps, exactly as it does for every other handler-raised gate

### Requirement: The defeat entry carries species and variant identity for species-backed monsters
Step 7's `target_defeated` entry SHALL additionally carry the defeated monster's registered
`species_key` and `variant_key` when the target is a species-backed individual, and SHALL omit both
fields (or carry `None`) for a tier-only individual. Consumers SHALL resolve species or variant identity
only from these fields, never by matching the target's display key or threat tier against registry text.

#### Scenario: A species-backed defeat carries its registered identity
- **WHEN** pending damage lethally crosses a species-backed monster
- **THEN** the `target_defeated` entry carries `target_id`, the tier, and the individual's registered species and variant keys

#### Scenario: A tier-only defeat carries no species fields
- **WHEN** a tier-only monster (no species identity) is defeated
- **THEN** the entry carries `target_id` and its tier exactly as before, with no species or variant value, and consumers treat it as identityless

#### Scenario: No consumer name-matches the registry
- **WHEN** a defeat consumer needs to know the defeated species
- **THEN** it reads the entry's species key, and no consumer resolves species identity by comparing a display name or tier against registry display text

#### Scenario: Existing carriage stays unchanged, non-Monsters unaffected
- **WHEN** species and variant identity is added to the entry
- **THEN** the existing carriage — integer `target_id` dbref and monster tier or `None` — stays
  unchanged, and non-Monster targets are unaffected
