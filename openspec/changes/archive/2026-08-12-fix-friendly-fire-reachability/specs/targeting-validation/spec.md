## RENAMED Requirements

- FROM: `### Requirement: Combat shortcuts expand to an explicit list and pass the same four validations`
- TO: `### Requirement: Combat shortcuts are convenience UI, not permission boundaries`

## MODIFIED Requirements

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

### Requirement: FactionConstraint is read from SkillDef, not declared by the caller
`world/rules/targeting.py` SHALL validate targets against `SkillDef.faction_constraint` — the
`FactionConstraint` enum (`ANY`/`SELF_ONLY`), a property of the skill definition itself — never against a
value the calling `ActionRequest` supplies independently. The `ANY` value is the default and accepts
every `Relation` value; `SELF_ONLY` accepts only `Relation.SELF`.

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

### Requirement: Combat shortcuts are convenience UI, not permission boundaries
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `all-enemies`, `all-allies`, and
`all` into an explicit deterministic candidate list of live entity values drawn from
`context.battlefield.roster`. Shorthand SHALL be accepted only for a `TargetSpec.AREA` skill. The
expanded candidates SHALL be validated by the identical validation logic used for an explicitly
supplied target list; no validation SHALL be skipped. Shorthand selection is a convenience for the
player and neither widens nor narrows the skill's targeting scope: the same candidates would be valid
if listed explicitly, and an `ANY` skill may still be given explicit ally or enemy targets.

#### Scenario: all-enemies expands and validates like an explicit list
- **WHEN** `all-enemies` is expanded for an `ANY` AREA skill
- **THEN** the expansion produces the enemy candidates, they pass the same validations as an explicit list, and the skill resolves normally

#### Scenario: An ANY skill may target allies explicitly despite all-enemies UI
- **WHEN** a player selects an ally target explicitly for an `ANY` AREA skill while the menu also offers `all-enemies`
- **THEN** the explicit ally target is valid and the skill resolves against it

#### Scenario: Shorthand tokens are meaningless out of combat
- **WHEN** `all-enemies` is supplied to `expand_target_shorthand()` with a context whose
  `battlefield` is `None`
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`

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
