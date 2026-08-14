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
  the six allocation values
- **THEN** before the first allocation input the game states the total budget, the six-axis count,
  each axis's 0–span range, and the rule that the sum must equal the budget

#### Scenario: The custom flow collects an optional background
- **WHEN** a pending player completes race, subrace, and allocations in `character create`
- **THEN** the wizard presents a bounded background (flavor-text) prompt that the player may fill
  or leave blank, and the accepted value is carried into activation

### Requirement: The interactive creation wizard collects every unmatched reply
The pending-character creation surface SHALL keep its interactive custom wizard usable end to end through the real command pipeline: while a wizard prompt is open, every player reply that does not match a command the pending-character gate exposes (for example `character`, `說明`, or `登出`, which remain available) SHALL reach the wizard generator, including empty input where the wizard accepts it (for example a blank background) and `cancel` at any step, which SHALL exit the wizard with the cancellation message and leave the character pending and unchanged. This SHALL hold for the `character create` wizard and for the interactive name-and-age continuation of `character concept <構想>` when its proposal resolves synchronously. A reply whose text equals a gate-exposed command key is executed as that command and is not delivered to the wizard.

#### Scenario: A name reply advances the custom wizard
- **WHEN** a pending player runs `character create` and replies to the name prompt
- **THEN** the wizard proceeds to the next prompt with that reply, instead of returning the creation-required message

#### Scenario: Cancel exits the custom wizard at the first prompt
- **WHEN** a pending player runs `character create` and replies `cancel` to the name prompt
- **THEN** the player receives the cancellation message, the character remains pending, and no wizard prompt state remains

#### Scenario: Empty input is delivered to the wizard where accepted
- **WHEN** a pending player replies to the background prompt of `character create` with an empty line
- **THEN** the wizard treats it as an empty background and continues, instead of dropping the reply

#### Scenario: An empty subrace is rejected as invalid input
- **WHEN** a pending player replies to the subrace prompt of `character create` with an empty line or `none`
- **THEN** the wizard reports the invalid subrace input and requires a registered subrace of the chosen race, instead of silently accepting a missing subrace

#### Scenario: The sync concept continuation collects the same replies
- **WHEN** `character concept <構想>` resolves its proposal synchronously and asks for the character name
- **THEN** the name reply is delivered to the wizard and the flow continues through the existing prompts

#### Scenario: A reply matching a gate-exposed command runs the command
- **WHEN** a pending player replies to an open wizard prompt with the text `character`
- **THEN** the `character` command runs instead of being delivered to the wizard, and no wizard prompt state is corrupted
