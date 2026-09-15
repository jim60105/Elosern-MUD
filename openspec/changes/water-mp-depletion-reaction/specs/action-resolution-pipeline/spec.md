## MODIFIED Requirements

### Requirement: The pipeline executes design doc §6.1's eight steps in order, each rejecting with a
named reason
`ActionResolver.resolve()` SHALL execute, in order: (1) skill ownership, (2) resource check, (3)
target resolution, (4) action capability, (5) effect resolution, (6) resource deduction, (7)
EventLog construction, (8) time-cost computation. Any step that fails SHALL cause `resolve()` to
return an `ActionResult` with `outcome == "rejected"` and a `reason` drawn from a named
`RejectReason` value — never a bare boolean or an unstructured exception escaping to the caller.
Step 6's `mp` resource deduction SHALL be applied through the canonical MP-change writer as the
staged pending effect's committed behavior, carrying the cast skill as the MP-event source, while
hp and sp deduction behavior and the preflight/recheck amount agreement stay unchanged; an MP
crossing to zero caused by cost payment is an ordinary attributed depletion fact, never a new
rejection reason.
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
