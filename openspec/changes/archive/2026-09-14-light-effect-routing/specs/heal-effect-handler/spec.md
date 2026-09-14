## MODIFIED Requirements

### Requirement: heal:area targets every valid target in the action's target set
`heal:area` SHALL apply the same clamped restoration independently to every target selected for that effect from the action
resolution pipeline's validated AREA candidates, with no cross-target interaction
(one target's clamp does not affect another's). Without an explicit per-effect audience this is the complete validated list, including enemies; an explicit audience SHALL only narrow delivery as declared.

#### Scenario: An area heal restores each target independently
- **WHEN** a `heal:area` effect resolves against three targets at different HP percentages
- **THEN** each target's HP increases by the same computed amount, independently clamped to that
  target's own `hp.max`
