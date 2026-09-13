## RENAMED Requirements

- FROM: `### Requirement: FactionConstraint is read from SkillDef, not declared by the caller`
- TO: `### Requirement: Targeting rules are supplied by a definition-owned TargetRequirement`

## MODIFIED Requirements

### Requirement: Target resolution runs four ordered validations
`world/rules/targeting.py` SHALL validate every candidate target, in order: (1) presence, (2) alive,
(3) range, (4) faction constraint. Each validation SHALL reject with its own named `RejectReason` when
it fails, and no later validation SHALL run for a candidate that already failed an earlier one for
`TargetSpec.SINGLE`. The faction check enforces only the self-only rule carried by the supplied
`TargetRequirement`: for `ANY` requirements every relation passes; for `SELF_ONLY` requirements only
the actor passes. A requirement whose `forbid_self` flag is set SHALL additionally reject the actor as
a `SINGLE` target with `RejectReason.TARGET_SPEC_MISMATCH`. The resolver SHALL NOT inspect the
identity, category, or effect list of whatever definition produced the requirement.

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
- **WHEN** target resolution runs against candidates whose `context.relation_to(actor, target)` returns `Relation.SELF`, `Relation.ALLY`, and `Relation.ENEMY` respectively for a requirement whose faction constraint is `ANY`
- **THEN** all three candidates pass the faction check

#### Scenario: A SELF_ONLY skill rejects non-actor targets at the faction check
- **WHEN** target resolution runs against a candidate whose relation is not `Relation.SELF` for a requirement whose faction constraint is `SELF_ONLY`
- **THEN** it rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: A target failing multiple validations reports the earliest one
- **WHEN** target resolution runs against a candidate that is both not present and dead
- **THEN** it rejects with `RejectReason.TARGET_NOT_PRESENT`, not `RejectReason.TARGET_DEAD`

#### Scenario: A forbid_self requirement rejects the actor as a SINGLE target
- **WHEN** a `SINGLE` requirement whose `forbid_self` flag is set is resolved with the actor as its
  only candidate
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`

#### Scenario: The resolver never inspects the definition that produced the requirement
- **WHEN** the same `TargetRequirement` value is resolved twice, once produced by a skill definition
  and once constructed directly with no definition behind it
- **THEN** both resolutions accept and reject exactly the same candidates for the same reasons

### Requirement: Targeting rules are supplied by a definition-owned TargetRequirement
`world/rules/targeting.py` SHALL resolve targets against a `TargetRequirement` value — carrying the
target shape (`TargetSpec`), the `FactionConstraint` (`ANY`/`SELF_ONLY`; legacy `ALLY`/`ENEMY` values
are retained for legacy test data and restrict nothing), and a `forbid_self` flag — produced by the
definition being acted on, never assembled by the calling request. A skill definition SHALL expose its
own requirement; any other kind of definition that can describe these three rules SHALL be able to use
the identical resolver without owning or fabricating a skill. Faction validation SHALL compare the
requirement's constraint against `context.relation_to(actor, target)`, which SHALL return
`Relation.SELF`, `Relation.ALLY`, or `Relation.ENEMY` — never a boolean in-combat flag. The `ANY`
value is the default and accepts every `Relation` value; `SELF_ONLY` accepts only `Relation.SELF`.

#### Scenario: The skill's own constraint governs, regardless of who casts it or how
- **WHEN** two different callers both invoke the same `skill_key` against the same target, once from
  `CmdCast` and once from a stand-in combat caller
- **THEN** both calls validate the target against the identical requirement produced by that skill
  definition — neither caller can supply a different constraint for the same skill

#### Scenario: SELF_ONLY accepts only the actor itself
- **WHEN** a requirement whose faction constraint is `FactionConstraint.SELF_ONLY` is validated against a
  target where `relation_to()` returns `Relation.ALLY`
- **THEN** faction validation rejects with `RejectReason.TARGET_FACTION_FORBIDDEN`

#### Scenario: ANY accepts every relation
- **WHEN** a requirement whose faction constraint is `FactionConstraint.ANY` (the default) is validated
  against targets returning `Relation.SELF`, `Relation.ALLY`, and `Relation.ENEMY` respectively
- **THEN** all three checks pass

#### Scenario: A non-skill caller resolves targets without a skill definition
- **WHEN** a caller that owns no skill definition constructs a `TargetRequirement` directly and resolves
  candidates through the shared resolver
- **THEN** resolution succeeds and applies the identical four ordered validations, with no skill
  definition supplied at any point

### Requirement: Out-of-combat targeting has no hostility model
`RoomActionContext.relation_to()` SHALL return `Relation.SELF` for the actor itself and
`Relation.ALLY` for every other present entity — never `Relation.ENEMY` — so that a definition whose
faction constraint is `ANY` may target any present entity out of combat. The faction check
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

### Requirement: ActionContext is a shared protocol implemented differently by combat and non-combat
callers
`world/rules/targeting.py` SHALL define `ActionContext` as a protocol (`battlefield`, `is_present()`,
`relation_to()`, `is_in_range()`) consumed identically regardless of implementation.
`is_in_range()` SHALL take exactly `(actor, target)`: range is a property of the two entities and the
world, never of the definition being acted on, so no implementation can branch on what is being used.
`RoomActionContext` SHALL be a complete, built implementation for out-of-combat use.
`BattlefieldActionContext` SHALL be declared as the conformance target for change 9, not implemented by
this change.

#### Scenario: RoomActionContext satisfies the full protocol
- **WHEN** `RoomActionContext` is constructed with a room and queried via all four protocol members
- **THEN** every member returns a value of the documented type with no `NotImplementedError`

#### Scenario: is_in_range() is a named, tested no-op today, owned by change 9 going forward
- **WHEN** `RoomActionContext.is_in_range()` is called for any actor/target pair
- **THEN** it returns `True` unconditionally, and a separate test using a stubbed context whose
  `is_in_range()` returns `False` confirms the rejection path itself is wired correctly; this change's
  design records change 9 (`dice-combat`, once change 12 supplies positional data) as the owner of
  replacing this constant with a real, coordinate-based implementation

#### Scenario: No implementation can observe what is being used
- **WHEN** `is_in_range()` is inspected on every shipped implementation
- **THEN** its parameter list is exactly `(actor, target)` and no implementation receives a skill,
  item, or other definition
