# Spec Delta

## ADDED Requirements

### Requirement: Commander may select only currently controllable allied actors
The authenticated player SHALL remain commander while a chosen eligible party member is the action actor. Authorization SHALL derive from current session and bound party membership and existing ability-to-act rules. Enemy, absent, fled, defeated, knocked-out and action-forbidden members SHALL require no command and SHALL receive no automatic attack.

#### Scenario: Forged actor
- **WHEN** a request names an enemy, another player party member or stale selected actor
- **THEN** the server rejects with a named reason without possession, round advance or state changes

#### Scenario: Actor lifecycle unchanged
- **WHEN** the commander chooses a companion
- **THEN** the account puppet and possession lifecycle remain unchanged

### Requirement: All personal skill choices and costs are actor scoped
Each authorized actor SHALL receive its own complete skill/scale/target/cost choices and disabled reasons through the shared authoritative preview. The server SHALL independently repeat ownership and capability validation. SELF SHALL bind the selected actor, and skill MP/SP SHALL be charged to that actor.

#### Scenario: Companion SELF and capability
- **WHEN** a companion owns a SELF skill the commander lacks
- **THEN** it is offered for that companion, binds that companion and charges only its resources when resolved

#### Scenario: Actor-specific magnitude eligibility
- **WHEN** only one party actor has the required freeform mastery
- **THEN** only that actor receives the eligible scale ladder and forged scale use by another actor rejects

### Requirement: Free inspection and equipment operations do not select round commands
Opening a bag, inspecting choices and existing equipment operations SHALL retain their free cost semantics. Relevant equipment changes SHALL invalidate affected previews and cause draft revalidation. Companion out-of-combat inventory management, item transfer and companion equipment-management UI SHALL remain excluded.

#### Scenario: Free inspection
- **WHEN** a player opens a bag or inspects an actor skill
- **THEN** no round command, dice, resource cost or elapsed combat time is produced

#### Scenario: Equipment invalidation
- **WHEN** equipment changes a selected actor relevant capability
- **THEN** affected previews and draft entries require authoritative revalidation before any complete round executes

