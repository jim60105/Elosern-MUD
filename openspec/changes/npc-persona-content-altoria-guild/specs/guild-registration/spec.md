## MODIFIED Requirements

### Requirement: Guild service hosts teach their service commands through scripted dialogue
The guild master host SHALL carry a `ScriptedDialogue` component whose `dialogue_key` resolves to
the `guild_staff` table. Talking to the host SHALL present the authored, in-character account of
what the guild counter offers and the known-keyword answers, and SHALL cause no state change. The
host teaches the service in the world's own terms and SHALL NOT name a command; the requirement's
title is kept for traceability. Component attachment SHALL remain idempotent
across repeated startup syncs.

#### Scenario: Guild master answers talk with command guidance
- **WHEN** a player talks to the guild master host
- **THEN** the host explains, in character, how registering, taking commissions and reporting back
  work at the counter, and names no command

#### Scenario: Guild master dialogue causes no state change
- **WHEN** a player talks to the guild master with any keyword
- **THEN** no guild, quest, or player state is written

#### Scenario: Repeated sync attaches the dialogue once
- **WHEN** the guild-economy startup sync runs twice
- **THEN** the guild master host carries exactly one `ScriptedDialogue` component
