# Spec Delta

## MODIFIED Requirements

### Requirement: BattlefieldActionContext conforms to change 8's ActionContext protocol
The combat context SHALL expose a two-team roster whose keys equal each participant's stable individual identity, reject mismatched keys or duplicate participants, and implement the complete action-context protocol without using display labels as identity.

#### Scenario: BattlefieldActionContext satisfies the full protocol
- **WHEN** `BattlefieldActionContext` is constructed with a populated `Battlefield` and queried via all four protocol members
- **THEN** every member returns a value of the documented type with no `NotImplementedError`

#### Scenario: battlefield is never None for a BattlefieldActionContext
- **WHEN** `BattlefieldActionContext.battlefield` is inspected
- **THEN** it is always a real `Battlefield` instance, never `None`; `RoomActionContext` has no battlefield

#### Scenario: Repeated labels are independent
- **WHEN** two persistent combatants share a label and one is renamed
- **THEN** their distinct roster identities and team membership remain unchanged; explicit nonpersistent fixture identities use the same battlefield path

#### Scenario: Persisted participants retain primary-key identity
- **WHEN** real persisted actors or explicit-positive-pk doubles populate a two-team roster
- **THEN** each roster key and corresponding team member equal `stable_actor_id(entity)` in the `dbref:` domain, even if an actor also supplies `combat_identity`

#### Scenario: Wrong identity domain is rejected
- **WHEN** a positive-pk participant is supplied under a `fixture:` roster key with matching team membership
- **THEN** construction raises `ValueError` before an action or skip-safety registration can use that battlefield

#### Scenario: Explicit pure identities remain distinct
- **WHEN** nonpersistent participants with the same display label supply distinct explicit `combat_identity` values
- **THEN** construction admits them as separate `fixture:` participants on the same battlefield path

#### Scenario: Duplicate participants are rejected
- **WHEN** a participant identity is placed in both teams
- **THEN** construction raises `ValueError` before action resolution
