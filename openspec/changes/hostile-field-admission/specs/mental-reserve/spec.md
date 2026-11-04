# Spec Delta

## MODIFIED Requirements

### Requirement: Posture and forced-sleep hysteresis are body scoped
Posture SHALL remain body-scoped and distinct from defeat/knockout, zero reserve SHALL latch forced sleep, and natural wake SHALL require72000 units at a terminal/noncombat boundary or an explicitly paid incapacitated-hostile round; admission alone SHALL never release the latch.

#### Scenario: Latch and wake
- **WHEN** a body reaches zero then recovers to 1, 71999 and 72000 outside combat
- **THEN** it remains forced asleep at the first two positive values and wakes at 72000 into moderate fatigue

#### Scenario: Reload
- **WHEN** a forced sleeper at 71999 is reloaded
- **THEN** posture and eligibility remain asleep; knockout/defeat sets are unchanged

#### Scenario: Paid hostile threshold
- **WHEN** actual enemy-only hostile rounds restore a living forced sleeper to the existing threshold
- **THEN** the existing receipt completes/wakes through the physiology owner without refill or revival; below threshold hostile admission leaves it asleep
