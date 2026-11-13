# Spec Delta

## ADDED Requirements

### Requirement: Departure ends with a server-authored farewell line

When a dream ends by confirmation or awakening, the server SHALL provide one closing line of fixed, non-generated text selected by the departure outcome and by whether the dream track reached climax. The line SHALL be the ended state's ending text, delivered once through ordinary output and printed by the text client. It SHALL require no model call, and departure and sleep continuation SHALL commit whether or not any client presents it.

#### Scenario: Each outcome selects its own line
- **WHEN** equivalent sessions end by confirmation, by awakening with a non-empty proposal and by awakening with an empty proposal
- **THEN** the three ending texts are non-empty and pairwise different

#### Scenario: Climax selects a different line
- **WHEN** two sessions end with the same outcome, one below climax and one at climax
- **THEN** their ending texts differ and the ending phase is still reported

#### Scenario: No model call
- **WHEN** a session ends while every model client constructor is patched to fail
- **THEN** the ending text is produced and the departure succeeds

#### Scenario: Delivered once
- **WHEN** a session ends and its state is read again afterwards
- **THEN** ordinary output received the ending text exactly once and the later read returns the same text without sending it again

#### Scenario: Departure does not wait for presentation
- **WHEN** a session ends with no browser attached
- **THEN** the session is closed, the sleep continuation is authorized as before and nothing remains pending for the farewell

#### Scenario: An open dream has no ending text
- **WHEN** the dream is still open
- **THEN** the ending text is empty
