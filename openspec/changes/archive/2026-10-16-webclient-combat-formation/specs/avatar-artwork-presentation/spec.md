## MODIFIED Requirements

### Requirement: Compact avatar failures remain accessible
Roster, presence and party avatars SHALL consume the common load state and retain reached failures after fallback. Compact indications SHALL have keyboard-usable explanations and assistive text without hover-only or color-only meaning. Combat renders no participant avatar: each combat participant stands on the stage as a figure, and each figure other than the controlled one carries a glance plate that names it in text.

#### Scenario: Fallback initial retains an error
- **WHEN** a real avatar request fails and no other real image succeeds
- **THEN** the initial remains with a persistent keyboard-accessible failure explanation

#### Scenario: Surface parity holds
- **WHEN** the same descriptor is rendered in switcher, rail and party surfaces
- **THEN** source order, generation truth and reached-fault behavior match without local URL caches

#### Scenario: Combat renders no participant avatar
- **WHEN** the committed mode is combat
- **THEN** no avatar renders for a combat participant, and each drawn figure other than the controlled one is named by its glance plate's text and accessible name
