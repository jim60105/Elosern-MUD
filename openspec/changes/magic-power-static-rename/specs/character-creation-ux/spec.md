## MODIFIED Requirements

### Requirement: Custom creation mode explains its prompts
When a pending player chooses custom creation, the game SHALL present each prompt with explanatory
text: what the requested race represents, which subraces exist for the chosen race (with their
display names and specialty descriptions), what the allocation axes mean, the total allocation
budget, the number of allocatable axes, each axis's allowed range, and the rule that the
allocations must sum exactly to the budget — in addition to the existing input validation
messages. The custom flow SHALL also collect an optional bounded background (flavor) text through
a dedicated prompt.

#### Scenario: Custom prompts carry explanations
- **WHEN** a pending player runs `character create`
- **THEN** the race prompt explains the race options and each allocation prompt explains what that
  axis affects

#### Scenario: The subrace prompt lists every available subrace
- **WHEN** a pending player chooses a race in `character create` and reaches the subrace prompt
- **THEN** the prompt lists every registered subrace of that race with its display name (and
  specialty), and no "none"/empty selection is offered

#### Scenario: The allocation briefing precedes the allocation step
- **WHEN** a pending player has chosen race and subrace in `character create` and is about to enter
  the seven allocation values
- **THEN** before the first allocation input the game states the total budget, the seven-axis count,
  each axis's 0–span range, and the rule that the sum must equal the budget

#### Scenario: The custom flow collects an optional background
- **WHEN** a pending player completes race, subrace, and allocations in `character create`
- **THEN** the wizard presents a bounded background (flavor-text) prompt that the player may fill
  or leave blank, and the accepted value is carried into activation
