## ADDED Requirements

### Requirement: Desktop chrome scales once from the reference viewport
At 1920x1080 the client SHALL use its reference chrome dimensions; at 2560x1440 comparable chrome text, controls, spacing and bounded islands SHALL render at four thirds of their reference dimensions within rounding tolerance. Below the reference height chrome SHALL not shrink below its reference readability floor. Viewport-responsive prose, stage art and band geometry SHALL NOT be multiplied a second time.

#### Scenario: Large desktop is proportional
- **WHEN** the same scene renders at 1920x1080 and 2560x1440 with the same reader preference
- **THEN** top navigation, control targets, map island and drawer header dimensions have a 4/3 ratio within 2 CSS pixels while art and prose scale exactly once

#### Scenario: Reader preference is independent
- **WHEN** the player changes only prose scale at fixed viewport size
- **THEN** message/log prose changes but chrome geometry does not

#### Scenario: Resize preserves hit testing
- **WHEN** a user resizes between acceptance dimensions and then selects a map node or command
- **THEN** the visible target receives the intended existing action and no stale geometry or duplicate dispatch occurs
