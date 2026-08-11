## ADDED Requirements

### Requirement: REACH and ESCORT objectives accept only quantity one

Proposal validation and the quest compiler SHALL reject REACH and ESCORT objectives whose quantity is not exactly 1, because arrival observation cannot meaningfully accumulate repeated visits in the current model. ESCORT is additionally subject to the binding-path rule below.

#### Scenario: Quantity-two REACH proposal is rejected

- **WHEN** a generated or authored quest proposal declares a REACH objective with `quantity: 2`
- **THEN** the proposal is rejected at validation and no quest is registered

#### Scenario: Quantity-one REACH remains accepted

- **WHEN** a quest proposal declares a REACH objective with `quantity: 1`
- **THEN** the proposal compiles and registers normally

### Requirement: ESCORT quests require a bound protected entity path

The system SHALL refuse to publish an ESCORT quest unless its stage can actually bind at least one protected entity at runtime; an ESCORT stage whose scene constraints make binding impossible SHALL be rejected at proposal/compile time with a clear error instead of being registered uncompletable.

#### Scenario: Unbindable ESCORT proposal is rejected

- **WHEN** a proposal's ESCORT stage has no production path to bind a protected entity (e.g. a permanent location with no NPC requirement)
- **THEN** the proposal is rejected and never reaches the guild board

#### Scenario: Quantity-one ESCORT is still rejected without a binding path

- **WHEN** a proposal declares an ESCORT objective with `quantity: 1` but no protected-entity binding path
- **THEN** the proposal is rejected at validation and no quest is registered

#### Scenario: Currently, ESCORT requests are refused with a clear message

- **WHEN** a player requests an escort-generated quest while no binding flow exists
- **THEN** the request is refused with a clear player-facing message and no quest is registered
