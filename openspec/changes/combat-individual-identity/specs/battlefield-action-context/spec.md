# Spec Delta

## MODIFIED Requirements

### Requirement: BattlefieldActionContext conforms to change 8's ActionContext protocol
The combat context SHALL expose a two-team roster keyed by stable individual identities and implement the complete action-context protocol without using display labels as identity.

#### Scenario: BattlefieldActionContext satisfies the full protocol
- **WHEN** `BattlefieldActionContext` is constructed with a populated `Battlefield` and queried via all
  four protocol members
- **THEN** every member returns a value of the documented type with no `NotImplementedError`

#### Scenario: battlefield is never None for a BattlefieldActionContext
- **WHEN** `BattlefieldActionContext.battlefield` is inspected
- **THEN** it is always a real `Battlefield` instance, never `None` — the opposite of
  `RoomActionContext`, where `battlefield` is always `None`

#### Scenario: Repeated labels are independent
- **WHEN** two persistent combatants share a label and one is renamed
- **THEN** their distinct roster identities and team membership remain unchanged; explicit nonpersistent fixture identities use the same battlefield path

### Requirement: is_present checks canonical battlefield roster membership
`BattlefieldActionContext.is_present(actor, target)` SHALL return `True` only if the target's stable individual identity is a member of `battlefield.roster`. Fled status belongs to the subsequent range check so the
four validations retain distinct, reachable rejection reasons.

#### Scenario: A roster member is present
- **WHEN** `is_present(actor, target)` is called for a target in `battlefield.roster`
- **THEN** it returns `True`

#### Scenario: A non-roster entity is not present
- **WHEN** `is_present(actor, target)` is called for a target whose stable individual identity is absent from
  `battlefield.roster`
- **THEN** it returns `False`, regardless of `battlefield.fled`

#### Scenario: Same label grants no presence
- **WHEN** a non-roster entity shares a label with a member
- **THEN** presence is false and an action against it is rejected without effects

### Requirement: is_in_range checks fled status alone; melee-versus-ranged is structurally unreachable
`BattlefieldActionContext.is_in_range(actor, target)` SHALL return `False` for any target whose
stable individual identity is in `battlefield.fled`, and `True` for every other roster member. The method SHALL NOT receive
the definition being acted on: a full melee-versus-ranged distinction is explicitly out of scope.

#### Scenario: A fled combatant is out of range for every skill
- **WHEN** `is_in_range(actor, target)` is called for a target whose stable individual identity is in `battlefield.fled`
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

#### Scenario: The absent definition parameter makes the scope boundary structural
- **WHEN** the melee-versus-ranged exclusion's justification is examined
- **THEN** no dependency this change can edit carries a range/reach classification and no coordinate system exists yet, so removing the parameter makes that boundary structural rather than a documented promise not to read it

