## ADDED Requirements

### Requirement: The interactive creation wizard collects every unmatched reply
The pending-character creation surface SHALL keep its interactive custom wizard usable end to end through the real command pipeline: while a wizard prompt is open, every player reply that does not match a command the pending-character gate exposes (for example `character`, `說明`, or `登出`, which remain available) SHALL reach the wizard generator, including empty input where the wizard accepts it (for example a blank subrace) and `cancel` at any step, which SHALL exit the wizard with the cancellation message and leave the character pending and unchanged. This SHALL hold for the `character create` wizard and for the interactive name-and-age continuation of `character concept <構想>` when its proposal resolves synchronously. A reply whose text equals a gate-exposed command key is executed as that command and is not delivered to the wizard.

#### Scenario: A name reply advances the custom wizard
- **WHEN** a pending player runs `character create` and replies to the name prompt
- **THEN** the wizard proceeds to the next prompt with that reply, instead of returning the creation-required message

#### Scenario: Cancel exits the custom wizard at the first prompt
- **WHEN** a pending player runs `character create` and replies `cancel` to the name prompt
- **THEN** the player receives the cancellation message, the character remains pending, and no wizard prompt state remains

#### Scenario: Empty input is delivered to the wizard where accepted
- **WHEN** a pending player replies to the subrace prompt of `character create` with an empty line
- **THEN** the wizard treats it as "no subrace" and continues, instead of dropping the reply

#### Scenario: The sync concept continuation collects the same replies
- **WHEN** `character concept <構想>` resolves its proposal synchronously and asks for the character name
- **THEN** the name reply is delivered to the wizard and the flow continues through the existing prompts

#### Scenario: A reply matching a gate-exposed command runs the command
- **WHEN** a pending player replies to an open wizard prompt with the text `character`
- **THEN** the `character` command runs instead of being delivered to the wizard, and no wizard prompt state is corrupted
