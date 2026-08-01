## MODIFIED Requirements

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
  `world.rules.buffs.BLOCKING_BUFF_KEYS` such as `paralysis`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.ACTION_FORBIDDEN)`

#### Scenario: An unregistered effect ID rejects at step 5, naming the exact ID
- **WHEN** `resolve()` is called for a skill whose `effects` list contains an effect ID whose prefix
  has no registered handler in `_EFFECT_HANDLERS`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.UNKNOWN_EFFECT_ID)` and
  the rejection detail names the exact unresolved effect ID

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
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.TIME_COST_LOOKUP_FAILED)`

### Requirement: Resolution is atomic — a failure at any step leaves zero state mutated
`ActionResolver.resolve()` SHALL NOT mutate any entity's `traits`, `sexual`, `buffs`,
`db.skill_grants`, `db.quest_log`, or instance `db.pin_reasons` state as a side effect of steps 1 through
8's validation or staging work. All mutation SHALL occur inside exactly one commit operation, executed
only after every one of the eight steps and every event-effect planner has succeeded. A failure at any
step, in a planner, or during the commit operation SHALL leave every touched entity, quest record, and
instance pin in exactly the state held before `resolve()` was called.

#### Scenario: A failure injected at any of the eight steps leaves state unchanged
- **WHEN** `resolve()` is called with a fault injected at step 1, 2, 3, 4, 5, 6, 7, or 8 such that the
  pipeline rejects
- **THEN** actor, target, quest-log, and pin state are bitwise identical to their pre-call values

#### Scenario: A failure inside commit reverses action and quest effects
- **WHEN** damage and quest progress are staged together and a later effect raises during commit
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=RejectReason.COMMIT_FAILED)` and
  HP, resources, progression, quest log, and pins all equal their pre-commit state

#### Scenario: Resource deduction and the skill's own effect commit together or not at all
- **WHEN** a skill with a non-zero cost stages both its own effect and resource deduction and an effect
  raises during commit
- **THEN** the actor's MP/SP is unchanged because the complete commit is rolled back

#### Scenario: A rejected action produces no EventLog
- **WHEN** `resolve()` rejects at any step or planner
- **THEN** the returned `ActionResult` has `event_log is None` and `time_cost_seconds is None`

#### Scenario: An unsupported planner mutation surface is refused
- **WHEN** an event-effect planner returns a `PendingEffect` declaring a surface outside snapshot and
  restore coverage
- **THEN** the action rejects before any action or quest state is touched

## ADDED Requirements

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
