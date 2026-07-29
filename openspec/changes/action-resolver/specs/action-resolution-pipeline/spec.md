## ADDED Requirements

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
`ActionResolver.resolve()` SHALL execute, in order: (1) skill ownership, (2) resource check, (3) target
resolution, (4) action capability, (5) effect resolution, (6) resource deduction, (7) EventLog
construction, (8) time-cost computation. Any step that fails SHALL cause `resolve()` to return an
`ActionResult` with `outcome == "rejected"` and a `reason` drawn from a named `RejectReason` value —
never a bare boolean or an unstructured exception escaping to the caller.

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
- **WHEN** `resolve()` is called for a skill whose `effects` list contains an effect ID whose prefix has
  no registered handler in `_EFFECT_HANDLERS`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.UNKNOWN_EFFECT_ID)` and the
  rejection's `detail` names the exact unresolved effect ID

#### Scenario: A malformed time-cost entry rejects at step 8
- **WHEN** `resolve()` is called for a skill whose `SKILL_TIME_OVERRIDES` entry (fault-injected for the
  test) is a negative integer
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.TIME_COST_LOOKUP_FAILED)`

### Requirement: Resolution is atomic — a failure at any step leaves zero state mutated
`ActionResolver.resolve()` SHALL NOT mutate any entity's `traits`, `sexual`, `buffs`, or
`db.skill_grants` state as a side effect of steps 1 through 8's validation or staging work. All
mutation SHALL occur inside exactly one commit operation, executed only after every one of the eight
steps has succeeded. A failure at any step, including a failure raised by an individual staged effect
during the commit operation itself, SHALL leave every entity referenced by the request in exactly the
state it held before `resolve()` was called.

#### Scenario: A failure injected at any of the eight steps leaves state unchanged
- **WHEN** `resolve()` is called with a fault injected at step 1, 2, 3, 4, 5, 6, 7, or 8 (one scenario
  per step) such that the pipeline rejects
- **THEN** the actor's and every target's `traits`, `sexual`, `buffs`, and `db.skill_grants` values are
  bitwise identical to their values immediately before the call, for every one of the eight
  fault-injection scenarios

#### Scenario: A failure inside the commit operation rolls back every already-applied effect
- **WHEN** a skill stages three `PendingEffect`s and the second one's `apply()` raises during commit
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=RejectReason.COMMIT_FAILED)`,
  and the mutation the first `PendingEffect` already applied before the second one raised is reversed,
  leaving the touched entity in its pre-commit state

#### Scenario: Resource deduction and the skill's own effect commit together or not at all
- **WHEN** a skill with a non-zero `cost` stages both its own effect and its resource-deduction
  `PendingEffect`, and the effect's `apply()` raises during commit
- **THEN** the actor's `mp`/`sp` value is unchanged — the resource was never deducted despite step 6
  having already staged the deduction, because the deduction and the effect commit inside the same
  atomic operation

#### Scenario: A rejected action produces no EventLog
- **WHEN** `resolve()` rejects at any step
- **THEN** the returned `ActionResult` has `event_log is None` and `time_cost_seconds is None`

#### Scenario: An effect handler declaring an unsupported mutation surface is refused, not silently run
- **WHEN** a skill's effect resolves to a `PendingEffect` whose declared `surfaces` includes a value
  outside the exact set `_commit()`'s snapshot/restore mechanism covers
- **THEN** `resolve()` returns `ActionResult(outcome="rejected", reason=
  RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE)` before any entity referenced by the request is touched

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than the single, explicitly marked `usable_out_of_combat` gate.
Combat-vs-non-combat behavior SHALL be expressed entirely through which concrete `ActionContext`
implementation the caller supplies.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

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
