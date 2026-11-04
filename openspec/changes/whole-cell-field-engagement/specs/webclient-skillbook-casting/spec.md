# Spec Delta

## MODIFIED Requirements

### Requirement: Field submissions revalidate and preserve deterministic routing

After existing dispatcher stale/duplicate checks, `explore.cast` SHALL reject current non-exploration mode or an active combat session, re-resolve referenced identities only from the actor's current accessible co-located candidates, and repeat current domain checks immediately before mutation. It SHALL NOT trust preview labels or globally accept remote/hidden entities.

#### Scenario: Current revision does not protect a vanished target
- **WHEN** a matching-revision SINGLE request arrives after its target moved away or died
- **THEN** current re-resolution/validation rejects it with a safe stable reason and no resource, roll, clock or combat change

#### Scenario: Field mode cannot bypass an active session
- **WHEN** combat began after the field preview and a modified client submits `explore.cast`
- **THEN** the field action rejects without submitting a combat round or settling a field cast

#### Scenario: Damage aimed elsewhere spends nothing
- **WHEN** a damaging field skill is submitted with no target, the actor or a non-monster target
- **THEN** the action rejects with the existing damage-requires-monster-target reason before spending resources or accessing/advancing the world clock

#### Scenario: Healing a monster still starts combat
- **WHEN** an enabled field-permitted healing skill targets a living co-located monster anchor
- **THEN** combat starts with that healing cast as the opening action under the existing rules

#### Scenario: AREA opening rechecks room occupants
- **WHEN** a living room monster set changes between preview and an admitted AREA opening whose anchor remains valid
- **THEN** the server revalidates and engages the current deterministic living monster set, and the committed view reports that actual set without using a stale client-expanded list

#### Scenario: Current ownership and context override a prior enabled row
- **WHEN** a formerly enabled skill loses ownership, field permission, scale entitlement, resources or required effect context before submission
- **THEN** current domain validation rejects before mutation with the corresponding stable reason

#### Scenario: Ordinary lists cannot smuggle a monster
- **WHEN** an ordinary browser target list contains a living co-located monster
- **THEN** it rejects before field settlement, because monster use requires the explicit anchor

#### Scenario: Any permitted effect on a monster anchor starts combat
- **WHEN** a living co-located monster anchor receives any permitted skill effect, including healing or support
- **THEN** combat initiates

#### Scenario: Anchor engagement follows the skill shape
- **WHEN** an admitted monster opening resolves
- **THEN** every current living room monster enters the encounter in deterministic order, while SINGLE resolves its effect only against the anchor and AREA against all current living room monsters

#### Scenario: Damage without an opening never touches state
- **WHEN** a damaging cast arrives without a valid monster opening
- **THEN** it rejects before resource, roll, session or clock access

#### Scenario: Non-damaging ordinary casts settle in the field
- **WHEN** a non-damaging ordinary NONE/SELF/SINGLE/AREA cast is admitted
- **THEN** it uses existing field settlement

#### Scenario: AREA filtering keeps its shipped semantics
- **WHEN** safely re-resolved AREA candidates are filtered
- **THEN** existing AREA candidate filtering remains unchanged, including rejection when none survive, and an identity that cannot be safely re-resolved rejects

#### Scenario: Nothing is broadened
- **WHEN** field submissions are validated
- **THEN** no field permission, effect-context or target rule is broadened
