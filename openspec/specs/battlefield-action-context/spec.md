# battlefield-action-context Specification

## Purpose
TBD - created by archiving change dice-combat. Update Purpose after archive.
## Requirements
### Requirement: BattlefieldActionContext conforms to change 8's ActionContext protocol
`world/rules/combat.py` SHALL provide `Battlefield` (holding a two-team roster, `teams: dict[str,
frozenset[str]]`, and live entity references keyed by entity key) and `BattlefieldActionContext`,
implementing change 8's `ActionContext` protocol (`battlefield`, `is_present()`, `relation_to()`,
`is_in_range()`) completely — closing the conformance target change 8 declared and left unbuilt.

#### Scenario: BattlefieldActionContext satisfies the full protocol
- **WHEN** `BattlefieldActionContext` is constructed with a populated `Battlefield` and queried via all
  four protocol members
- **THEN** every member returns a value of the documented type with no `NotImplementedError`

#### Scenario: battlefield is never None for a BattlefieldActionContext
- **WHEN** `BattlefieldActionContext.battlefield` is inspected
- **THEN** it is always a real `Battlefield` instance, never `None` — the opposite of
  `RoomActionContext`, where `battlefield` is always `None`

### Requirement: relation_to is derived from two-team membership, not a stored relation field
`BattlefieldActionContext.relation_to(actor, target)` SHALL return `Relation.SELF` when actor and
target are the same entity, `Relation.ALLY` when they belong to the same team, and `Relation.ENEMY`
when they belong to different teams. `Battlefield` SHALL support exactly two teams.

#### Scenario: Same-team members are allies
- **WHEN** `relation_to(actor, target)` is called for two distinct entities on the same team
- **THEN** it returns `Relation.ALLY`

#### Scenario: Different-team members are enemies
- **WHEN** `relation_to(actor, target)` is called for two entities on different teams
- **THEN** it returns `Relation.ENEMY`

#### Scenario: An entity queried against itself is SELF
- **WHEN** `relation_to(actor, actor)` is called
- **THEN** it returns `Relation.SELF`

### Requirement: is_present checks canonical battlefield roster membership
`BattlefieldActionContext.is_present(actor, target)` SHALL return `True` only if the target's entity
key is a member of `battlefield.roster`. Fled status belongs to the subsequent range check so the
four validations retain distinct, reachable rejection reasons.

#### Scenario: A roster member is present
- **WHEN** `is_present(actor, target)` is called for a target in `battlefield.roster`
- **THEN** it returns `True`

#### Scenario: A non-roster entity is not present
- **WHEN** `is_present(actor, target)` is called for a target whose key is absent from
  `battlefield.roster`
- **THEN** it returns `False`, regardless of `battlefield.fled`

### Requirement: is_in_range checks fled status; melee-versus-ranged is explicitly not built
`BattlefieldActionContext.is_in_range(actor, target, skill)` SHALL return `False` for any target whose
key is in `battlefield.fled`, and `True` for every other roster member, regardless of the skill's own
identity. This is a deliberate, documented scope boundary — a full melee-versus-ranged distinction is
explicitly out of scope because no dependency this change can edit (`SkillDef`, change 5) carries a
range/reach classification, and no coordinate system (change 12) exists yet.

#### Scenario: A fled combatant is out of range for every skill
- **WHEN** `is_in_range(actor, target, skill)` is called for a target whose key is in
  `battlefield.fled`, for any `skill`
- **THEN** it returns `False`

#### Scenario: An active roster member is in range regardless of skill identity
- **WHEN** `is_in_range(actor, target, skill)` is called for a target still active on the battlefield,
  for a melee-flavored skill and separately for a ranged-flavored skill
- **THEN** both calls return `True` — this change does not distinguish them

#### Scenario: The out-of-range rejection path is genuinely wired, not decorative
- **WHEN** a `TargetSpec.SINGLE` skill is resolved via `ActionResolver.resolve()` against a fled
  battlefield combatant
- **THEN** it rejects with `RejectReason.TARGET_OUT_OF_RANGE`, proving `is_in_range()`'s one real rule
  reaches all the way through targeting to a rejection, not merely returning a value nothing consumes

### Requirement: Combat shortcuts read the two-team roster with no separate expansion path
`context.battlefield.teams` SHALL be queryable by change 8's `expand_target_shorthand()` for
`"all-enemies"`, `"all-allies"`, and `"all"` through the narrow mapping-value correction in
`targeting.py`; no separate combat expansion path SHALL exist.

#### Scenario: all-enemies expands to the opposing team's roster
- **WHEN** `expand_target_shorthand(actor, context, "all-enemies")` is called with a
  `BattlefieldActionContext` wrapping a two-team `Battlefield`
- **THEN** the resulting candidate list contains every entity on the team that is not the actor's
  own team

#### Scenario: all-allies expands to the actor's own team, including the actor
- **WHEN** `expand_target_shorthand(actor, context, "all-allies")` is called
- **THEN** the resulting candidate list contains every entity on the actor's own team, including
  the actor itself

