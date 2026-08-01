## Why

Evennia currently creates and puppets a blank `PlayerCharacter` when an account
registers. Because the project does not then collect identity or initialize
traits, ordinary player commands can reach an incomplete character and fail.

## What Changes

- Add an account-bound, command-driven character creation flow that prevents a
  newly registered account from playing until its character is complete.
- Support two mutually exclusive creation modes: select a shipped preset
  character, or create a new character by supplying a free-form name and
  supported identity fields.
- Require both creation modes to collect and persist adult age and apparent
  age, race, and an optional compatible subrace; reject either age below 18.
- Build new characters' HP, MP, SP, and physical combat stats from a
  registry-backed allocation budget. Players distribute only finite point
  budgets inside their chosen race/subrace's documented ranges, keeping the
  aggregate starting profile out of all-minimum and all-maximum extremes while
  preserving meaningful specializations.
- Give a newly created character a random magic level inside a ±10% band around
  its race's registry-backed average starting magic level, never above its
  race's magic cap.
- Make completed creation atomic, assign the existing account-owned shell's
  traits and persistent player state, then enable gameplay. Creation never
  moves or re-puppets the character. Do not use an LLM or an external service.

## Capabilities

### New Capabilities

- `player-character-creation`: Account registration gating, preset selection,
  interactive custom-character creation, validation, and atomic activation.
- `player-stat-allocation`: Lore-backed starting-stat profiles, bounded point
  allocation, and randomized starting magic level for custom player characters.

### Modified Capabilities

- `entity-trait-scales`: Clarify that generic and race-baseline construction
  stays deterministic; player creation applies its validated starting values as
  a separate, post-baseline step.
- `lore-registries`: Add each race's immutable average starting magic level as
  the source of truth for character-creation rolls.

## Impact

- Affects `typeclasses/accounts.py`, `typeclasses/characters.py`, command
  sets/new player commands, deterministic creation rules, race lore, and tests.
- Changes the first-login experience for newly created accounts only; existing
  blank development characters are not migrated because the game has no
  released users.
- Does not modify import records or the AI layer, and adds no dependencies.
