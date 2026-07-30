# targeting-validation Specification

## Purpose
TBD - created by archiving change action-resolver. Update Purpose after archive.
## Requirements
### Requirement: Target resolution runs four ordered validations
`world/rules/targeting.py` SHALL validate every candidate target, in order: (1) presence, (2) alive,
(3) range, (4) faction constraint. Each validation SHALL reject with its own named `RejectReason` when
it fails, and no later validation SHALL run for a candidate that already failed an earlier one for
`TargetSpec.SINGLE`.

#### Scenario: A target not present in the room or battlefield rejects at presence
- **WHEN** target resolution runs against a candidate `context.is_present()` reports `False` for
- **THEN** it rejects with `RejectReason.TARGET_NOT_PRESENT`

#### Scenario: A dead target rejects at the alive check
- **WHEN** target resolution runs against a candidate whose `entity.traits.hp.value` is `0`
- **THEN** it rejects with `RejectReason.TARGET_DEAD`

#### Scenario: An out-of-range target rejects at the range check
- **WHEN** target resolution runs against a candidate for which the supplied `ActionContext`'s
  `is_in_range()` is stubbed to return `False`
- **THEN** it rejects with `RejectReason.TARGET_OUT_OF_RANGE`

#### Scenario: A faction-forbidden target rejects at the faction check
- **WHEN** target resolution runs against a candidate whose `context.relation_to(actor, target)` does
  not satisfy the skill's own `SkillDef.faction_constraint`
- **THEN** it rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: A target failing multiple validations reports the earliest one
- **WHEN** target resolution runs against a candidate that is both not present and dead
- **THEN** it rejects with `RejectReason.TARGET_NOT_PRESENT`, not `RejectReason.TARGET_DEAD`

### Requirement: SINGLE and AREA target specs filter candidates differently
For `TargetSpec.SINGLE`, a candidate failing any of the four validations SHALL reject the entire
action with that validation's reason. For `TargetSpec.AREA`, each candidate SHALL be validated
independently; a candidate failing any validation SHALL be silently dropped from the final target
list, except that an `AREA` action whose final target list is empty after filtering SHALL reject with
`RejectReason.NO_VALID_TARGETS_IN_AREA` before effect resolution or resource deduction runs.

#### Scenario: SINGLE rejects the whole action on one invalid target
- **WHEN** a `TargetSpec.SINGLE` skill is resolved against one dead target
- **THEN** the action rejects with `RejectReason.TARGET_DEAD` and no `PendingEffect` is staged

#### Scenario: AREA silently drops one invalid candidate among several valid ones
- **WHEN** a `TargetSpec.AREA` skill is resolved against three candidates, one of which is dead
- **THEN** the action proceeds to effect resolution against the two surviving candidates, and the dead
  candidate is absent from the final target list with no rejection

#### Scenario: AREA rejects when every candidate is filtered out
- **WHEN** a `TargetSpec.AREA` skill's shorthand expands to candidates that are all dead or all absent
- **THEN** the action rejects with `RejectReason.NO_VALID_TARGETS_IN_AREA` before any resource is
  deducted

### Requirement: FactionConstraint is read from SkillDef, not declared by the caller
`world/rules/targeting.py` SHALL validate targets against `SkillDef.faction_constraint` — change 5's
`FactionConstraint` enum (`ANY`/`ALLY`/`ENEMY`/`SELF_ONLY`), a property of the skill definition itself
— never against a value the calling `ActionRequest` supplies independently. Faction validation SHALL
compare `skill.faction_constraint` against `context.relation_to(actor, target)`, which SHALL return
`Relation.SELF`, `Relation.ALLY`, or `Relation.ENEMY` — never a boolean in-combat flag.

#### Scenario: The skill's own constraint governs, regardless of who casts it or how
- **WHEN** two different callers both invoke the same `skill_key` against the same target, once from
  `CmdCast` and once from a stand-in combat caller
- **THEN** both calls validate the target against the identical `SkillDef.faction_constraint` value —
  neither caller can supply a different constraint for the same skill

#### Scenario: SELF_ONLY accepts only the actor itself
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.SELF_ONLY` is validated against a
  target where `relation_to()` returns `Relation.ALLY`
- **THEN** faction validation rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: ALLY accepts both SELF and ALLY relations
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.ALLY` is validated against a target
  where `relation_to()` returns `Relation.SELF`, and separately against a target where it returns
  `Relation.ALLY`
- **THEN** both checks pass

#### Scenario: ANY accepts every relation
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.ANY` (the default) is validated
  against targets returning `Relation.SELF`, `Relation.ALLY`, and `Relation.ENEMY` respectively
- **THEN** all three checks pass

### Requirement: Out-of-combat targeting has no hostility model
`RoomActionContext.relation_to()` SHALL return `Relation.SELF` for the actor itself and
`Relation.ALLY` for every other present entity — never `Relation.ENEMY` — so that a skill whose
`faction_constraint` is `ANY` or `ALLY` (`SINGLE`-targeted) may target any present entity out of
combat.

#### Scenario: Support magic, self-buffing, and sexual magic on a companion all validate identically
- **WHEN** a `TargetSpec.SINGLE` skill whose `faction_constraint` is `FactionConstraint.ALLY` is
  resolved out of combat against (a) the actor itself, (b) a present companion entity, using
  `RoomActionContext`
- **THEN** both (a) and (b) pass faction validation with no special-cased branch distinguishing the two

#### Scenario: An ENEMY-constrained skill has no valid target out of combat
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.ENEMY` is resolved out of combat
  against any present entity via `RoomActionContext`
- **THEN** it rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`, because `RoomActionContext` never
  reports `Relation.ENEMY`

### Requirement: Combat shortcuts expand to an explicit list and pass the same four validations
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `"all-enemies"`,
`"all-allies"`, and `"all"` into an explicit candidate list of live entity values drawn from
`context.battlefield.roster`. When the roster is a mapping keyed by entity key, expansion SHALL use
its values rather than its keys. The resulting candidates SHALL be validated by the identical
four-step, `AREA`-filtering logic used for an explicitly named target list — no validation SHALL be
skipped for shorthand-expanded candidates.
`"all-allies"` SHALL include both `Relation.ALLY` entities and the actor's `Relation.SELF` entity.

#### Scenario: A dead ally on the roster is filtered out of all-allies, not included
- **WHEN** `"all-allies"` expands to a roster mapping that includes one dead ally
- **THEN** the final target list, after the four validations run against every expanded entity,
  excludes the dead ally exactly as it would if that entity had been listed explicitly

#### Scenario: A mapping roster expands to entities rather than keys
- **WHEN** a battlefield roster is a `dict[str, LivingEntity]`
- **THEN** shorthand expansion returns the `LivingEntity` values and never passes string keys to
  `relation_to()` or the four validators

#### Scenario: all-allies includes the actor
- **WHEN** `"all-allies"` is expanded for an actor with one other same-team member
- **THEN** the candidate list contains both the actor and the other ally

#### Scenario: Shorthand tokens are meaningless out of combat
- **WHEN** `"all-enemies"` is supplied to `expand_target_shorthand()` with a context whose
  `battlefield` is `None`
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`

### Requirement: ActionContext is a shared protocol implemented differently by combat and non-combat
callers
`world/rules/targeting.py` SHALL define `ActionContext` as a protocol (`battlefield`, `is_present()`,
`relation_to()`, `is_in_range()`) consumed identically regardless of implementation.
`RoomActionContext` SHALL be a complete, built implementation for out-of-combat use.
`BattlefieldActionContext` SHALL be declared as the conformance target for change 9, not implemented by
this change.

#### Scenario: RoomActionContext satisfies the full protocol
- **WHEN** `RoomActionContext` is constructed with a room and queried via all four protocol members
- **THEN** every member returns a value of the documented type with no `NotImplementedError`

#### Scenario: is_in_range() is a named, tested no-op today, owned by change 9 going forward
- **WHEN** `RoomActionContext.is_in_range()` is called for any actor/target/skill combination
- **THEN** it returns `True` unconditionally, and a separate test using a stubbed context whose
  `is_in_range()` returns `False` confirms the rejection path itself is wired correctly; this change's
  design records change 9 (`dice-combat`, once change 12 supplies positional data) as the owner of
  replacing this constant with a real, coordinate-based implementation

