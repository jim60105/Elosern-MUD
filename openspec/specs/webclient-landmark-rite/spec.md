# webclient-landmark-rite Specification

## Purpose
Defines the webclient's landmark rite surfaces: the rite arrival card, the rite panel, the rite stage and its backdrop, and how they present the committed `rite` panel and dispatch a rite.

## Requirements

### Requirement: The rite arrival card presents the landmark and offers approach or leave
The rite arrival card SHALL show the landmark, the district's lit state, the guardian's name and form, and how many options were experienced, SHALL show no scene prose, and SHALL emit approach on Enter or its primary button and leave on Escape or its secondary button while keeping focus inside the card.

#### Scenario: Content
- **WHEN** the card renders a synthetic panel for an unlit district with one of two options experienced, and then for a lit district
- **THEN** it shows the unlit and then the lit district line, the guardian, and the count one of two, and no line of the panel's delivery

#### Scenario: Keys and focus
- **WHEN** the card mounts and the player presses Tab, Enter, a held Enter repeat and Escape
- **THEN** the primary button has focus on mount, Tab moves only between the two buttons, Enter emits approach once, the repeat emits nothing and Escape emits leave

#### Scenario: Revisit and missing art
- **WHEN** the card is opened as a revisit, and when the panel carries no artwork
- **THEN** the kicker reads as a landmark rite instead of an arrival, and the art band collapses to the quiet ink header with no image

### Requirement: The rite panel lists the options as one choice card
The rite panel SHALL render one digit-activated row per option in order followed by a leave row, SHALL mark options not yet experienced with a text alternative, SHALL name the performer in the card's header, and SHALL emit the picked option key or leave.

#### Scenario: Rows and activation
- **WHEN** the panel renders two options, one experienced, and the player presses 1, then Escape
- **THEN** two option rows and a leave row render, only the unexperienced row carries the not-yet-experienced mark and text, the digit emits that option's key and Escape emits leave

#### Scenario: Performer header
- **WHEN** the panel is given a performer
- **THEN** the header inside the card frame names that performer

### Requirement: A companion performer cannot pick a solo-only option
While the performer is a companion, the rite panel SHALL disable every option that does not admit a companion, show its reason, and emit nothing when it is activated.

#### Scenario: Disabled row
- **WHEN** a companion is the performer and the player activates the solo-only row by digit, Enter and click
- **THEN** the row is disabled with its reason and no pick is emitted, while the other option still emits its key

### Requirement: The rite backdrop names the landmark and guardian over the art
The rite backdrop SHALL fill the stage with the panel's artwork under an ink wash and a plate naming the landmark and the guardian, and SHALL show quiet ink with the same plate when the panel carries no artwork.

#### Scenario: With and without art
- **WHEN** the backdrop renders a panel with artwork and one without
- **THEN** both show the plate, the first shows the artwork and the second shows no image

### Requirement: The rite card opens on arrival and never on a session's first snapshot
The rite presentation state SHALL open the card when the committed `rite` panel becomes available for a district it has not seen available in the session, and SHALL stay closed on the first snapshot of a session.

#### Scenario: Arrival, repeat and return
- **WHEN** a later snapshot makes the panel available, the card is dismissed, the same district is committed again, and then the panel becomes unavailable and available again
- **THEN** the card opens, stays closed for the repeated snapshot, and opens again after the return

#### Scenario: First snapshot
- **WHEN** a session's first snapshot already carries an available panel
- **THEN** the state is closed

### Requirement: Rite transitions are local and performing dispatches once
Opening, approaching and leaving SHALL change only local state and send nothing. Performing SHALL send the rite action exactly once for a listed option while the stage is open, connected and unlocked, and SHALL send nothing otherwise.

#### Scenario: Local transitions
- **WHEN** the card is approached, left and reopened
- **THEN** the phase follows card, stage, closed, card with the revisit mark, and no action was sent

#### Scenario: Perform guards
- **WHEN** performing is requested twice in a row, for an unknown option, while disconnected, and while mutations are locked
- **THEN** exactly one action was sent, carrying the option and a null member identifier

### Requirement: The rite state adopts its own result and resets off the landmark
A success result for the pending request SHALL become the playing delivery; any other outcome SHALL clear the pending request and play nothing. The state SHALL reset to closed when the panel becomes unavailable, the mode leaves exploration or the session changes, and leaving SHALL be refused while a delivery plays.

#### Scenario: Result adoption
- **WHEN** the pending request succeeds with a delivery, another request's result arrives, and a second request is refused
- **THEN** the first delivery plays, the foreign result changes nothing, and the refusal leaves no delivery

#### Scenario: Reset
- **WHEN** the panel becomes unavailable while the stage is open
- **THEN** the phase is closed with no pending request and no delivery

### Requirement: An open rite card or stage is a centred card
While the rite card or stage is open the store's centred-card predicate SHALL be true, so walking and the compass stop as they do for every centred card.

#### Scenario: Predicate
- **WHEN** the phase is card, stage and closed in turn
- **THEN** the predicate is true, true and false

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

### Requirement: The rite flow is verified in the live client at two viewports
The managed browser suite SHALL drive the rite flow from a wilderness arrival and from a settlement room, and SHALL verify the stage at 1451x790 and 2560x1440.

#### Scenario: Wilderness journey
- **WHEN** the journey runs arrival, approach, option, scene pages and leave with synthetic committed data, then reopens the stage at the larger viewport
- **THEN** every surface appears in order, exactly one action is sent, no text is below 16px and nothing overflows its anchor at either viewport

#### Scenario: City journey
- **WHEN** the same flow runs from a settlement room
- **THEN** the card opens over the room, the stage plays the scene, and the return entry shows under the place card
