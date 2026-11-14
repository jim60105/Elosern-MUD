# Spec Delta

## ADDED Requirements

### Requirement: The rite flow is verified in the live client at two viewports
The managed browser suite SHALL drive the rite flow from a wilderness arrival and from a settlement room, and SHALL verify the stage at 1451x790 and 2560x1440.

#### Scenario: Wilderness journey
- **WHEN** the journey runs arrival, approach, option, scene pages and leave with synthetic committed data, then reopens the stage at the larger viewport
- **THEN** every surface appears in order, exactly one action is sent, no text is below 16px and nothing overflows its anchor at either viewport

#### Scenario: City journey
- **WHEN** the same flow runs from a settlement room
- **THEN** the card opens over the room, the stage plays the scene, and the return entry shows under the place card
