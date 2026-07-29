## ADDED Requirements

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
  not satisfy the request's declared `Faction` constraint
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

### Requirement: Faction is a caller-declared request constraint, validated via a Relation query
`ActionRequest` SHALL carry a `faction: Faction` field (`ANY`/`ALLY`/`ENEMY`/`SELF_ONLY`), independent
of `SkillDef`. Faction validation SHALL compare the constraint against `context.relation_to(actor,
target)`, which SHALL return `Relation.SELF`, `Relation.ALLY`, or `Relation.ENEMY` — never a boolean
in-combat flag.

#### Scenario: SELF_ONLY accepts only the actor itself
- **WHEN** `Faction.SELF_ONLY` is checked against a target where `relation_to()` returns
  `Relation.ALLY`
- **THEN** faction validation rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: ALLY accepts both SELF and ALLY relations
- **WHEN** `Faction.ALLY` is checked against a target where `relation_to()` returns `Relation.SELF`,
  and separately against a target where it returns `Relation.ALLY`
- **THEN** both checks pass

#### Scenario: ANY accepts every relation
- **WHEN** `Faction.ANY` is checked against targets returning `Relation.SELF`, `Relation.ALLY`, and
  `Relation.ENEMY` respectively
- **THEN** all three checks pass

### Requirement: Out-of-combat targeting has no hostility model
`RoomActionContext.relation_to()` SHALL return `Relation.SELF` for the actor itself and
`Relation.ALLY` for every other present entity — never `Relation.ENEMY` — so that `TargetSpec.SINGLE`
may target any present entity out of combat.

#### Scenario: Support magic, self-buffing, and sexual magic on a companion all validate identically
- **WHEN** a `TargetSpec.SINGLE`, `Faction.ALLY` skill is resolved out of combat against (a) the actor
  itself, (b) a present companion entity, using `RoomActionContext`
- **THEN** both (a) and (b) pass faction validation with no special-cased branch distinguishing the two

#### Scenario: An ENEMY-constrained skill has no valid target out of combat
- **WHEN** a `Faction.ENEMY` skill is resolved out of combat against any present entity via
  `RoomActionContext`
- **THEN** it rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`, because `RoomActionContext` never
  reports `Relation.ENEMY`

### Requirement: Combat shortcuts expand to an explicit list and pass the same four validations
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `"all-enemies"`, `"all-allies"`, and
`"all"` into an explicit candidate list drawn from `context.battlefield`'s roster. The resulting
candidates SHALL be validated by the identical four-step, `AREA`-filtering logic used for an explicitly
named target list — no validation SHALL be skipped for shorthand-expanded candidates.

#### Scenario: A dead ally on the roster is filtered out of all-allies, not included
- **WHEN** `"all-allies"` expands to a roster that includes one dead ally
- **THEN** the final target list, after the four validations run against every expanded candidate,
  excludes the dead ally exactly as it would if that entity's key had been listed explicitly

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

#### Scenario: is_in_range() is a named, tested no-op today
- **WHEN** `RoomActionContext.is_in_range()` is called for any actor/target/skill combination
- **THEN** it returns `True` unconditionally, and a separate test using a stubbed context whose
  `is_in_range()` returns `False` confirms the rejection path itself is wired correctly
