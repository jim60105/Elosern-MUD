# Spec Delta

## ADDED Requirements

### Requirement: The rite performer is picked on the stage figures
While the rite panel is shown, the panel lists more than one performer and at least one option admits a companion, each listed performer's stage figure SHALL be a hit area: activating it makes it the performer, the picked figure is lit and selected, and the others dim. Otherwise no figure SHALL be a hit area.

#### Scenario: Pick by pointer
- **WHEN** the player activates a listed companion's figure on the rite stage
- **THEN** the panel header names the companion, that figure is the selected one, and the solo-only option is disabled

#### Scenario: Picking not offered
- **WHEN** the panel lists one performer, or no option admits a companion
- **THEN** no figure is selectable and the panel shows no switching hint

#### Scenario: Playback
- **WHEN** a rite scene is playing
- **THEN** only the performer's figure is lit and no figure is selectable

### Requirement: Arrow keys step the performer from the rite panel
While picking is offered, ArrowLeft and ArrowRight in the rite panel SHALL step to the previous and next listed performer, wrapping, and SHALL not move the panel's active row. While picking is not offered the keys SHALL pass through.

#### Scenario: Step and wrap
- **WHEN** the player presses ArrowRight once per listed performer
- **THEN** each press names the next performer and the last press returns to the controlled character, with the active row unchanged

### Requirement: The dispatched rite names the picked performer
The rite action SHALL carry the picked performer's member identifier, null for the controlled character, and SHALL not be sent for a companion with an option that does not admit one.

#### Scenario: Companion rite
- **WHEN** a companion is picked and the player picks an option that admits a companion
- **THEN** one action is sent with that companion's member identifier

#### Scenario: Blocked option
- **WHEN** a companion is picked and the solo-only option is activated
- **THEN** no action is sent

### Requirement: The performer defaults to the controlled character
The performer SHALL be the controlled character on every entry to the rite stage, and SHALL return to the controlled character when the picked performer is no longer listed.

#### Scenario: Re-entry and withdrawal
- **WHEN** the player leaves and re-enters the stage after picking a companion, and when a committed panel no longer lists the picked companion
- **THEN** in both cases the controlled character is the performer
