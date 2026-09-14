## ADDED Requirements

### Requirement: Per-effect potency is validated independently of effect identity
A skill SHALL support an immutable positive finite potency for each damage or healing effect occurrence. Potency SHALL be independently configurable for repeated effects, default to identity when omitted, and be applied before defense subtraction or healing rounding. Invalid potency or mismatched declarations SHALL fail before a cast can be attempted. Caller-supplied context SHALL NOT override authored potency. Other schools SHALL use the same behavior without named-spell branches.

#### Scenario: Repeated effects retain independent potency
- **WHEN** a synthetic skill contains two damage effects with distinct declared potencies
- **THEN** each strike uses its own potency and neither inherits the preceding effect configuration

#### Scenario: Defensive formula order matters
- **WHEN** equal successful rolls use potency 1 and 2 against nonzero defense
- **THEN** the attack component is scaled before subtracting defense, not the final damage

#### Scenario: Invalid and forged values cannot change a cast
- **WHEN** authoring supplies a boolean/nonfinite/nonpositive potency or a caller supplies a conflicting policy
- **THEN** invalid authoring is rejected and caller policy cannot change the authored resulting HP delta

#### Scenario: Healing composes and remains capped
- **WHEN** a synthetic heal combines potency, equipment gain and allowed freeform scaling
- **THEN** the specified stages apply once, independently clamp each HP gap and never revive an HP-zero recipient
