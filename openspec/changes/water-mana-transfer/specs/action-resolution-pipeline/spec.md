## MODIFIED Requirements

### Requirement: Audience planning agrees between preflight and final resolution
Audience planning SHALL be side-effect-free and use authoritative current relationships. A nonempty selected pool with an empty component audience SHALL skip only that component without rolling. If all effect audiences are empty, the cast SHALL reject before resource, time or practice changes. Final resolution SHALL repeat audience validation after initiative changes. When a component declares an audience condition, planning SHALL additionally filter that component's recipients by the validated target-state gate evaluated from stored state (no handler materialization, no rolls), skipping only the gated component for non-matching targets; preflight and final resolution SHALL evaluate the identical gate against current state. Delivery SHALL retain existing transaction and event attribution guarantees.

#### Scenario: One audience is empty
- **WHEN** an authored mixed spell has allies in its selection but no enemies
- **THEN** ally recovery resolves, damage does not roll and the cast pays once

#### Scenario: All audiences are empty
- **WHEN** every configured component has no valid recipient
- **THEN** the action is rejected without consuming MP, time or practice

#### Scenario: Final relationships change
- **WHEN** preflight succeeds but relationship state changes before execution
- **THEN** final delivery uses the current authoritative relationship, not the preview

#### Scenario: Late error restores recipients
- **WHEN** a mixed effect cast fails after effects have started applying
- **THEN** all actual recipients including an explicitly bound actor are restored

#### Scenario: A gated component filters without affecting siblings
- **WHEN** preflight plans one ungated component and one gauge-state-gated component over a mixed
  target pool, and a gated target's stored state changes before execution
- **THEN** the ungated component's recipients are unchanged by the gate, the gated component follows
  the current stored state in final planning, and an all-empty gated audience still leaves the cast
  payable via its ungated components
