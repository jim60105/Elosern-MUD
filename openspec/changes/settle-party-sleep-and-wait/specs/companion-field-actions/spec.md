# Spec Delta

## ADDED Requirements

### Requirement: Indivisible field actions complete before collapse
An initially eligible indivisible field action SHALL commit its full effects, costs and elapsed time once. Each present member SHALL settle its sampled interval posture/activity for that full duration, then enter forced sleep if depleted. No remainder SHALL become retrospective sleep recovery; prompts SHALL follow durable commit.

#### Scenario: Caster collapse
- **WHEN** an awake caster has 12 reserve units and completes a six-second field action
- **THEN** all effects and costs commit with six seconds; reserve clamps to zero and forced sleep begins afterwards with no recovered remainder

#### Scenario: Unselected companion collapse
- **WHEN** only an unselected awake companion has 12 units when another member casts the same action
- **THEN** the full caster result and six seconds commit; only the depleted companion collapses and sends a status notice without stealing control

#### Scenario: Already sleeping actor
- **WHEN** a sleeping actor attempts the action
- **THEN** preflight rejects with zero effects, costs and time

