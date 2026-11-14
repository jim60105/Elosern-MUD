# Spec Delta

## ADDED Requirements

### Requirement: A rite landmark arrival opens the rite arrival card
When the committed `rite` panel becomes available for a district during a session, the client SHALL open the rite arrival card in the choices anchor instead of the generic landmark card, in the wilderness and in a settlement room alike, after any dream or sleep-handoff card.

#### Scenario: Arrival
- **WHEN** a committed snapshot makes the panel available for a new district while a landmark arrival notice is held
- **THEN** the rite arrival card opens and the generic landmark card does not open for that arrival, then or later

#### Scenario: Priority
- **WHEN** a sleep-handoff card owns the choices anchor when the rite card would open
- **THEN** the rite card waits and opens when the sleep-handoff card closes

### Requirement: Approaching presents the rite stage without sending anything
Approaching from the card SHALL present the rite stage as local presentation: the dialogue stage layout, the party in the left actor anchor, the rite backdrop in place of the map, the guardian's form in the message window and the rite panel in the choices anchor. Approaching and leaving SHALL send no request.

#### Scenario: Enter the stage
- **WHEN** the player approaches from the card in the travel layout
- **THEN** the frame takes the dialogue presentation, the party line-up, the rite backdrop and the rite panel are mounted, the travel map and the action dock are not, and no action was sent

#### Scenario: Leave
- **WHEN** the player leaves from the card or from the panel
- **THEN** the map or the room returns with focus on it and no action was sent

### Requirement: Picking an option dispatches one rite and plays its delivery
Picking an option on the rite panel SHALL dispatch the rite action exactly once with that option, SHALL hide the panel while the request is pending, SHALL play the returned delivery through the shared authored-scene player, and SHALL return the panel when the scene finishes. A refused request SHALL return the panel without playing anything.

#### Scenario: Success
- **WHEN** the player picks the first option and the action succeeds with a three-line delivery
- **THEN** one action carrying that option was sent, the panel leaves, the three lines advance by explicit activation, and the panel returns with focus after the last acknowledgement

#### Scenario: Double activation and refusal
- **WHEN** the option is activated twice before the result, and the result is a refusal
- **THEN** one action was sent, no scene plays and the panel is shown again

### Requirement: A return entry reopens the rite card while the panel is available
While the `rite` panel is available, the mode is exploration and neither the card nor the stage is open, the place column SHALL show one entry naming the guardian, activated by click or the R key, that reopens the arrival card as a revisit.

#### Scenario: Entry and key
- **WHEN** the card was dismissed on a landmark and the player presses R with focus outside any text entry
- **THEN** the entry was shown and the card reopens marked as a revisit

#### Scenario: Entry hidden
- **WHEN** the card or the stage is open, or the panel is unavailable
- **THEN** no entry is shown and R does nothing

### Requirement: Leaving the landmark drops every rite surface
When the `rite` panel becomes unavailable or the committed mode leaves exploration, the client SHALL close the card and the stage, stop any playing rite scene and remove the return entry.

#### Scenario: Panel withdrawn
- **WHEN** a committed snapshot makes the panel unavailable while the stage is open
- **THEN** the stage, the panel, the backdrop and the entry are gone and the ordinary layout is shown
