## Why

The first-session experience is blank: Evennia's default connection screen and a bare prompt-based
creation wizard give a new player no sense of place, no premise, and no reason to pick one starting
identity over another. The front door of the game does not yet feel like the game.

## What Changes

- Replace the default Evennia connection screen with a custom one: a title banner (伊洛瑟恩大陸),
  a one-line premise, and CONNECT / CREATE prompts.
- Show a short world introduction (2–3 lines of prose) to a newly registered account after login,
  before character creation.
- Restyle the `character` command's output: a world-view framing line, preset previews (one-line race
  description, allocation emphasis, one-line background), and explanatory prompts in custom mode.
  The internal preset/custom activation logic and validation are unchanged.

## Capabilities

### New Capabilities
- `connection-screen`: the custom connection screen (title banner, premise, CONNECT/CREATE prompts)
  and the world introduction shown to a new player after login/registration
- `character-creation-ux`: the presentational restyle of the `character` command — world-view framing,
  preset previews, and explanatory custom-mode prompts, without changing activation semantics

### Modified Capabilities
- `evennia-project-skeleton`: the "Player can connect" scenario changes from presenting the default
  Evennia login/welcome screen to presenting the project's custom connection screen

## Impact

- `server/conf/settings.py` — register `CONNECTION_SCREEN_MODULE`
- New world prose module (connection text, world introduction) under `world/`
- `commands/character_creation.py` — `CmdCharacter` output restyle (logic unchanged)
- Tests in `commands/tests/` and any connection-screen test; `evennia-project-skeleton` scenario text
  updated alongside
- No dependencies on other active changes; no LLM or image services involved
