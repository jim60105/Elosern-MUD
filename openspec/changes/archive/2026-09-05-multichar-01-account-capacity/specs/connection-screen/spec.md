# Delta spec: connection-screen (multichar-01-account-capacity)

Re-scopes the world introduction from "the account's character" to "the character the session
puppets at login", because an account may now own several characters with independent
creation lifecycles.

## MODIFIED Requirements

### Requirement: A newly registered account receives a world introduction before character creation
When a session logs in and the character it puppets is still pending creation, the game
SHALL show a short world introduction (2–3 lines of prose introducing 伊洛瑟恩大陸 and the journey
ahead) before the character-creation interface. The subject of this decision SHALL be the
character the session actually puppets after the login hook completes, never "any pending
character the account owns": an account owning both an activated character and an abandoned
pending shell SHALL receive neither screen when it logs in as the activated character. A session
that ends the login hook with no puppet SHALL receive neither screen. The introduction SHALL be
shown on every login while the puppeted character remains pending, and SHALL NOT be shown for a
character that has completed creation.

#### Scenario: A pending account sees the introduction
- **WHEN** a newly registered account logs in and the player character it puppets is still pending
  creation
- **THEN** it receives the world introduction followed by the character-creation interface

#### Scenario: An activated account does not see the introduction
- **WHEN** an account whose puppeted player character has completed creation logs in
- **THEN** it receives no world introduction and goes straight to normal gameplay

#### Scenario: An abandoned pending sibling does not re-trigger the introduction
- **WHEN** an account that owns one activated character and one still-pending character logs in
  and auto-puppets the activated character
- **THEN** it receives neither the world introduction nor the creation start screen

#### Scenario: A login that leaves the session unpuppeted shows no introduction
- **WHEN** a session completes login without acquiring a puppet
- **THEN** it receives neither the world introduction nor the creation start screen
