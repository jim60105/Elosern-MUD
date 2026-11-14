# Spec Delta

## Purpose

Defines the webclient's landmark rite surfaces: the rite arrival card, the rite panel, the rite stage and its backdrop, and how they present the committed `rite` panel and dispatch a rite.

## ADDED Requirements

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
