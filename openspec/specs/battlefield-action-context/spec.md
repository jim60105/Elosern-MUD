# battlefield-action-context Specification

## Purpose
Provides Battlefield and BattlefieldActionContext conforming completely to change 8's ActionContext protocol: relation_to derived from two-team membership, is_present checked against canonical roster membership, and is_in_range reduced to fled status with melee-versus-ranged explicitly unbuilt. Requires combat shortcuts to read the two-team roster directly with no separate expansion path.

## Requirements

### Requirement: BattlefieldActionContext conforms to change 8's ActionContext protocol
`world/rules/combat.py` SHALL provide `Battlefield` (holding a two-team roster, `teams: dict[str,
frozenset[str]]`, and live entity references keyed by entity key) and `BattlefieldActionContext`,
implementing the `ActionContext` protocol (`battlefield`, `is_present()`, `relation_to()`,
`is_in_range()`) completely — closing the conformance target change 8 declared and left unbuilt.
Conformance SHALL be evaluated against the protocol's current two-argument `is_in_range()` signature.

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

### Requirement: is_in_range checks fled status alone; melee-versus-ranged is structurally unreachable
`BattlefieldActionContext.is_in_range(actor, target)` SHALL return `False` for any target whose
key is in `battlefield.fled`, and `True` for every other roster member. The method SHALL NOT receive
the definition being acted on: a full melee-versus-ranged distinction is explicitly out of scope
because no dependency this change can edit carries a range/reach classification and no coordinate
system exists yet, and removing the parameter makes that boundary structural rather than a documented
promise not to read it.

#### Scenario: A fled combatant is out of range for every skill
- **WHEN** `is_in_range(actor, target)` is called for a target whose key is in `battlefield.fled`
- **THEN** it returns `False`

#### Scenario: An active roster member is in range regardless of skill identity
- **WHEN** `is_in_range(actor, target)` is called for a target still active on the battlefield
- **THEN** it returns `True`, and the call site supplies no skill, item, or other definition that
  could distinguish a melee-flavored use from a ranged-flavored one

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
