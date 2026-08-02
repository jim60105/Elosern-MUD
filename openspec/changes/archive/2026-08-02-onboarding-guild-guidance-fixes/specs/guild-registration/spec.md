## ADDED Requirements

### Requirement: Guild service hosts teach their service commands through scripted dialogue
The guild master host SHALL carry a `ScriptedDialogue` component whose `dialogue_key` resolves to
the `guild_staff` table. Talking to the host SHALL present the authored guild-command overview and
known-keyword answers, and SHALL cause no state change. Component attachment SHALL remain idempotent
across repeated startup syncs.

#### Scenario: Guild master answers talk with command guidance
- **WHEN** a player talks to the guild master host
- **THEN** the host teaches the available guild commands through its authored dialogue

#### Scenario: Guild master dialogue causes no state change
- **WHEN** a player talks to the guild master with any keyword
- **THEN** no guild, quest, or player state is written

#### Scenario: Repeated sync attaches the dialogue once
- **WHEN** the guild-economy startup sync runs twice
- **THEN** the guild master host carries exactly one `ScriptedDialogue` component
