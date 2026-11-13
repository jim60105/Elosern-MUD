# Spec Delta

## ADDED Requirements

### Requirement: A live departure plays a farewell before the stage releases

When the committed dream state of the mounted stage changes from open to closed for the same session and carries an ending text, the browser SHALL keep the stage mounted in a farewell state: the ending text is presented as the goddess's line, every dream control is inert, and activating the band after the line is shown in full releases the stage. A state already closed when first seen, and a reconnect, SHALL NOT play the farewell.

#### Scenario: Farewell replaces the controls
- **WHEN** an open stage with a layer open receives the closed state of the same session with an ending text
- **THEN** the stage stays mounted, the layer is closed, the band presents the ending text, the reply bar is gone, the keepsake rows are inert, digit and Escape keys do nothing, and the live region announces the line

#### Scenario: Activation completes, then releases
- **WHEN** the player activates the band while the line is typing, and activates it again
- **THEN** the first activation shows the line in full and the second starts the release; at reduced or off motion the stage is released at once, and at full motion it is released when the fade ends or on a further activation

#### Scenario: Key hint names waking
- **WHEN** the farewell line is shown in full
- **THEN** the band's key hint differs from the hint shown during the dream

#### Scenario: Reduced motion shows the line at once
- **WHEN** the farewell begins at reduced or off motion
- **THEN** the line is shown in full immediately and no fade element is rendered

#### Scenario: Already closed is not replayed
- **WHEN** the client's first dream state for a session is already closed, or the connection drops during a farewell
- **THEN** no dream stage is mounted and the waking surface is shown

#### Scenario: A new open dream ends a held farewell
- **WHEN** an open dream state is committed while a farewell is held
- **THEN** the stage shows the open dream and the farewell is discarded

#### Scenario: Waking surfaces wait for the farewell
- **WHEN** a farewell is held
- **THEN** the surfaces that yield to an open dream (the sleep-handoff cards, the landmark arrival card and the wilderness travel layout) stay yielded until the stage is released

#### Scenario: Departure without ending text closes at once
- **WHEN** the state closes with an empty ending text
- **THEN** the stage unmounts immediately as before
