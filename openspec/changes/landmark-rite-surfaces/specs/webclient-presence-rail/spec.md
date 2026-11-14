# Spec Delta

## ADDED Requirements

### Requirement: ChoiceCard offers a header inside its frame
`ChoiceCard` SHALL render a consumer-supplied header inside the card frame above its rows, and SHALL render exactly as before when no header is supplied. The header SHALL not change the card's keyboard composite.

#### Scenario: Header supplied
- **WHEN** a card is rendered with a header and the player presses ArrowDown
- **THEN** the header precedes the rows inside the frame and the active row moves as it does without a header

#### Scenario: No header
- **WHEN** a card is rendered without a header
- **THEN** no header element exists
