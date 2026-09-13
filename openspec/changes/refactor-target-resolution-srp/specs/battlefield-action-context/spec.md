## RENAMED Requirements

- FROM: `### Requirement: is_in_range checks fled status; melee-versus-ranged is explicitly not built`
- TO: `### Requirement: is_in_range checks fled status alone; melee-versus-ranged is structurally unreachable`

## MODIFIED Requirements

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
