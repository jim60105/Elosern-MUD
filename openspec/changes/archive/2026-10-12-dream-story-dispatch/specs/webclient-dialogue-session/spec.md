# Spec Delta

## ADDED Requirements

### Requirement: Encounter updates expose only committed visible interaction targets

Activation SHALL refresh existing room occupant/affordance and conversation projections after commit through upstream phase-aware session helpers. Presence, visibility/access and current phase gates SHALL remain authoritative. Arrangement notices SHALL NOT expose unmaterialized roles as occupants. The existing read-only version-2 conversation window SHALL consume actual authorized commission references; client prose SHALL never authorize acceptance.

#### Scenario: Publication and real activation are distinct
- **WHEN** a package is arranged but one future role has not activated
- **THEN** the occupant/conversation projection excludes that role and activation later exposes it only when actually visible/access-eligible

#### Scenario: Real window completes the requested story
- **WHEN** either distinct escort offer is accepted through its actual current conversation window and real movement/possession produces rendezvous
- **THEN** upstream accept_escort_commission and evaluate_escort_event produce the bound record and exclusive result, the alternative becomes invalid, one reward commits and reopening everyday dialogue preserves the same NPC identity and earlier memory

#### Scenario: Rollback sends no false projection
- **WHEN** activation or outcome writes fail and compensate session/cache state
- **THEN** no post-commit new-occupant or success update appears and projections reflect authoritative prior state

#### Scenario: Scripted story works after models are disabled
- **WHEN** profiles are disabled after package publication
- **THEN** real scripted conversation, authorized acceptance, escort, combat/possession and exactly-once settlement remain usable without a model call
