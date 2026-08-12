# targeting-validation Specification

## Purpose
TBD - created by archiving change action-resolver. Update Purpose after archive.
## Requirements
### Requirement: Target resolution runs four ordered validations
`world/rules/targeting.py` SHALL validate every candidate target, in order: (1) presence, (2) alive,
(3) range, (4) faction constraint. Each validation SHALL reject with its own named `RejectReason` when
it fails, and no later validation SHALL run for a candidate that already failed an earlier one for
`TargetSpec.SINGLE`. The faction check enforces only the skill's self-only rule: for `ANY` skills every
relation passes; for `SELF_ONLY` skills only the actor passes.

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

#### Scenario: An ANY skill accepts every relation
- **WHEN** target resolution runs against candidates whose `context.relation_to(actor, target)` returns `Relation.SELF`, `Relation.ALLY`, and `Relation.ENEMY` respectively for an `ANY` skill
- **THEN** all three candidates pass the faction check

#### Scenario: A SELF_ONLY skill rejects non-actor targets at the faction check
- **WHEN** target resolution runs against a candidate whose relation is not `Relation.SELF` for a `SELF_ONLY` skill
- **THEN** it rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: A target failing multiple validations reports the earliest one
- **WHEN** target resolution runs against a candidate that is both not present and dead
- **THEN** it rejects with `RejectReason.TARGET_NOT_PRESENT`, not `RejectReason.TARGET_DEAD`

### Requirement: SINGLE and AREA target specs filter candidates differently
Target-shape validation SHALL run before candidate validation. `TargetSpec.NONE` SHALL accept no
candidates. `TargetSpec.SELF` SHALL accept empty input normalized to the actor or exactly one
explicit candidate identical to the actor, preserving trusted direct policy requests while rejecting
every other shape. `TargetSpec.SINGLE` SHALL require exactly one explicit candidate and SHALL reject
shorthand. `TargetSpec.AREA` SHALL require either a nonempty explicit candidate list with no
duplicate object identity or one approved shorthand. A shape violation SHALL reject with
`RejectReason.TARGET_SPEC_MISMATCH` before candidate validation. After shape validation, SELF and
SINGLE candidate failure SHALL reject the entire action with the first of the four ordered
validation reasons. AREA candidates SHALL be validated independently and invalid candidates SHALL be
silently dropped; a valid AREA input whose final target list is empty after filtering SHALL reject with
`RejectReason.NO_VALID_TARGETS_IN_AREA` before effect resolution or resource deduction.

#### Scenario: SINGLE rejects the whole action on one invalid target
- **WHEN** a `TargetSpec.SINGLE` skill is resolved against one dead target
- **THEN** the action rejects with `RejectReason.TARGET_DEAD` and no `PendingEffect` is staged

#### Scenario: AREA silently drops one invalid candidate among several valid ones
- **WHEN** a `TargetSpec.AREA` skill is resolved against three distinct candidates, one of which is dead
- **THEN** the action proceeds to effect resolution against the two surviving candidates, and the dead
  candidate is absent from the final target list with no rejection

#### Scenario: AREA rejects when every candidate is filtered out
- **WHEN** a `TargetSpec.AREA` skill's valid shorthand expands to candidates that are all dead or all absent
- **THEN** the action rejects with `RejectReason.NO_VALID_TARGETS_IN_AREA` before any resource is
  deducted

#### Scenario: NONE rejects supplied targets
- **WHEN** a NONE skill receives any explicit target or shorthand
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH` rather than silently ignoring caller input

#### Scenario: SELF binds only the request actor
- **WHEN** a SELF skill receives no caller target
- **THEN** target resolution binds and validates the actor; a trusted direct request containing exactly that actor behaves identically, while any other explicit candidate rejects as a shape mismatch

#### Scenario: Duplicate AREA input cannot repeat an effect
- **WHEN** an explicit AREA list contains the same object identity more than once
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH` before filtering, effect staging, or resource deduction

### Requirement: FactionConstraint is read from SkillDef, not declared by the caller
`world/rules/targeting.py` SHALL validate targets against `SkillDef.faction_constraint` — the
`FactionConstraint` enum (`ANY`/`SELF_ONLY`; legacy `ALLY`/`ENEMY` values are retained for legacy
test data and restrict nothing), a property of the skill definition itself — never against a value
the calling `ActionRequest` supplies independently. Faction validation SHALL
compare `skill.faction_constraint` against `context.relation_to(actor, target)`, which SHALL return
`Relation.SELF`, `Relation.ALLY`, or `Relation.ENEMY` — never a boolean in-combat flag. The `ANY`
value is the default and accepts every `Relation` value; `SELF_ONLY` accepts only `Relation.SELF`.

#### Scenario: The skill's own constraint governs, regardless of who casts it or how
- **WHEN** two different callers both invoke the same `skill_key` against the same target, once from
  `CmdCast` and once from a stand-in combat caller
- **THEN** both calls validate the target against the identical `SkillDef.faction_constraint` value —
  neither caller can supply a different constraint for the same skill

#### Scenario: SELF_ONLY accepts only the actor itself
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.SELF_ONLY` is validated against a
  target where `relation_to()` returns `Relation.ALLY`
- **THEN** faction validation rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: ANY accepts every relation
- **WHEN** a skill whose `faction_constraint` is `FactionConstraint.ANY` (the default) is validated
  against targets returning `Relation.SELF`, `Relation.ALLY`, and `Relation.ENEMY` respectively
- **THEN** all three checks pass

### Requirement: Out-of-combat targeting has no hostility model
`RoomActionContext.relation_to()` SHALL return `Relation.SELF` for the actor itself and
`Relation.ALLY` for every other present entity — never `Relation.ENEMY` — so that a skill whose
`faction_constraint` is `ANY` may target any present entity out of combat. The faction check
enforces only the self-only rule, so the legacy `ENEMY`/`ALLY` constraint values (retained for
legacy test data, never declared by shipped skills) restrict nothing.

#### Scenario: Support magic, self-buffing, and sexual magic on a companion all validate identically
- **WHEN** a `TargetSpec.SINGLE` skill whose `faction_constraint` is `FactionConstraint.ANY` is
  resolved out of combat against (a) the actor itself, (b) a present companion entity, using
  `RoomActionContext`
- **THEN** both (a) and (b) pass faction validation with no special-cased branch distinguishing the two

#### Scenario: A legacy enemy constraint restricts nothing out of combat
- **WHEN** a skill whose `faction_constraint` is the legacy `FactionConstraint.ENEMY` value is resolved out of combat
  against any present entity via `RoomActionContext`
- **THEN** it passes faction validation, because only the self-only rule is enforced

### Requirement: Combat shortcuts are convenience UI, not permission boundaries
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `all-enemies`,
`all-allies`, and `all` into an explicit deterministic candidate list of live entity values drawn from
`context.battlefield.roster`. Shorthand SHALL be accepted only for a `TargetSpec.AREA` skill. When the
roster is a mapping keyed by entity key, expansion SHALL use
its values rather than its keys. The resulting candidates SHALL be validated by the identical
four-step AREA-filtering logic used for an explicitly supplied target list; no validation SHALL be
skipped.
`all-allies` SHALL include both `Relation.ALLY` entities and the actor's `Relation.SELF` entity.
Shorthand selection is a convenience for the player and neither widens nor narrows the skill's
targeting scope: the same candidates would be valid if listed explicitly, and an `ANY` skill may
still be given explicit ally or enemy targets.

#### Scenario: A dead ally on the roster is filtered out of all-allies, not included
- **WHEN** `all-allies` expands to a roster mapping that includes one dead ally
- **THEN** the final target list, after the four validations run against every expanded entity,
  excludes the dead ally exactly as it would if that entity had been listed explicitly

#### Scenario: all-enemies expands and validates like an explicit list
- **WHEN** `all-enemies` is expanded for an `ANY` AREA skill
- **THEN** the expansion produces the enemy candidates, they pass the same validations as an explicit list, and the skill resolves normally

#### Scenario: An ANY skill may target allies explicitly despite all-enemies UI
- **WHEN** a player selects an ally target explicitly for an `ANY` AREA skill while the menu also offers `all-enemies`
- **THEN** the explicit ally target is valid and the skill resolves against it

#### Scenario: A mapping roster expands to entities rather than keys
- **WHEN** a battlefield roster is a `dict[str, LivingEntity]`
- **THEN** shorthand expansion returns the `LivingEntity` values and never passes string keys to
  `relation_to()` or the four validators

#### Scenario: all-allies includes the actor
- **WHEN** `all-allies` is expanded for an actor with one other same-team member
- **THEN** the candidate list contains both the actor and the other ally

#### Scenario: Shorthand tokens are meaningless out of combat
- **WHEN** `all-enemies` is supplied to `expand_target_shorthand()` with a context whose
  `battlefield` is `None`
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`

#### Scenario: SINGLE cannot use a shorthand that happens to yield one target
- **WHEN** a SINGLE skill receives `all-enemies` in a battlefield containing exactly one enemy
- **THEN** target-shape validation rejects with `RejectReason.TARGET_SPEC_MISMATCH` before expansion can authorize it

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

