## Purpose

Replace Evennia's default login screen with the project's custom presentation and show newly
registered accounts a world introduction before character creation.

## Requirements

### Requirement: The connection screen presents the project's custom login presentation
The unlogged-in connection screen SHALL replace Evennia's default login/welcome screen with a
project-authored presentation containing a title banner (伊洛瑟恩大陸), a one-line premise, and
prompts for registering and logging in (CONNECT and CREATE). It SHALL remain a valid Evennia
connection screen through the configured `CONNECTION_SCREEN_MODULE`, so every entry channel
(telnet, webclient) receives the same presentation.

#### Scenario: A connecting client sees the custom screen
- **WHEN** a telnet client or webclient connects to the server
- **THEN** the connection response presents the project title banner, the premise line, and the
  CONNECT / CREATE prompts rather than Evennia's default welcome screen

### Requirement: A newly registered account receives a world introduction before character creation
When an account whose auto-created player character is still pending creation logs in, the game
SHALL show a short world introduction (2–3 lines of prose introducing 伊洛瑟恩大陸 and the journey
ahead) before the character-creation interface. The introduction SHALL be shown on every login while
the account's character remains pending, and SHALL not be shown to an account whose character has
completed creation.

#### Scenario: A pending account sees the introduction
- **WHEN** a newly registered account logs in and its player character is still pending creation
- **THEN** it receives the world introduction followed by the character-creation interface

#### Scenario: An activated account does not see the introduction
- **WHEN** an account whose player character has completed creation logs in
- **THEN** it receives no world introduction and goes straight to normal gameplay
