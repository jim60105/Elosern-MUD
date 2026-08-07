## MODIFIED Requirements

### Requirement: The arrival scene plays as the first guided beat
When an onboarding character first arrives at the South Gate, the game SHALL play the authored
arrival scene: prose describing the city and the guard's opening line prompting the localized look
command 「看」(alias `look`). The beat SHALL complete when the player successfully looks while at
the South Gate (detected through the character's look hook); a look anywhere else, or a look that
fails, SHALL NOT advance the beat. Until completion the scene SHALL replay on each arrival
(including reconnect while still at the gate); after completion it SHALL never replay.

#### Scenario: First arrival plays the arrival scene
- **WHEN** a newly activated character first arrives at the South Gate
- **THEN** the arrival prose and the guard's prompt to use 「看」(alias `look`) are presented

#### Scenario: look completes the arrival beat
- **WHEN** the player successfully looks (via the localized 「看」 command) while at the South Gate
  during the arrival scene
- **THEN** the beat advances to the guard-guidance beat and the scene does not replay on later
  arrivals

#### Scenario: A look elsewhere does not advance the beat
- **WHEN** an onboarding character looks while not at the South Gate (or a look fails)
- **THEN** the arrival beat does not advance

#### Scenario: Reconnect before look replays the scene
- **WHEN** the player disconnects before completing the arrival scene and later logs in again while
  still at the South Gate
- **THEN** the arrival scene is presented again
