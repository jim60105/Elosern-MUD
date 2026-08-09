## Purpose

Present preset previews and explanatory prompts during the pending character's creation so the
player can make an informed choice, without changing activation semantics.

## Requirements

### Requirement: The character creation command presents preset previews
The `character` command, when invoked without arguments, SHALL present a world-view framing line, the
list of shipped presets, and, for each preset, a preview comprising a one-line race description, an
allocation-emphasis description, and a one-line background. The preview content SHALL be derived from
immutable registry data (the player-preset catalog and the race registry) rather than duplicated
string literals in the command.

#### Scenario: Preset previews render from registry data
- **WHEN** a pending player invokes `character` with no arguments
- **THEN** the output lists exactly the registry's presets, each with a race one-liner, an
  allocation-emphasis one-liner, and a background one-liner drawn from registry data

### Requirement: Custom creation mode explains its prompts
When a pending player chooses custom creation, the game SHALL present each prompt with explanatory
text: what the requested race represents and what the allocation axes mean, in addition to the
existing input validation messages.

#### Scenario: Custom prompts carry explanations
- **WHEN** a pending player runs `character create`
- **THEN** the race prompt explains the race options and each allocation prompt explains what that
  axis affects

### Requirement: The character creation restyle does not change activation semantics
The presentational restyle SHALL NOT alter the preset/custom activation logic, the adult identity
gate, subrace compatibility checks, display-name validation, or the all-or-nothing atomic activation
in `world.rules.character_creation`. Existing activation behavior SHALL remain deterministic under the
restyled output.

#### Scenario: The restyled command still enforces the adult gate
- **WHEN** custom creation supplies `age=17` through the restyled prompts
- **THEN** activation is still rejected and the character remains pending

### Requirement: The creation surface offers a concept-driven custom entry
The pending-character creation command surface SHALL provide `character concept <構想>` (aliases
構想) as an additional entry into custom creation: a bounded free-form concept runs the guarded
`character_creation` generative layer, and a validated proposal is presented as a summary while
the display name, actual age, and apparent age are collected through the existing prompts and the
deterministic adult gate; the completed request then flows through the ordinary
`CharacterCreationRequest` preflight and all-or-nothing activation. The concept path SHALL NOT
alter activation semantics, the adult identity gate, subrace compatibility checks, display-name
validation, or the all-or-nothing atomic activation in `world.rules.character_creation`. With the
LLM offline the command SHALL return the stable unavailable message and the ordinary preset/custom
flows SHALL remain fully usable.

#### Scenario: A concept-guided flow reaches the ordinary activation path
- **WHEN** a pending player runs `character concept` and completes the interactive name and age
  prompts
- **THEN** activation runs the unchanged deterministic preflight and all-or-nothing activation,
  including the adult gate, on the proposal's values plus the entered fields

#### Scenario: The concept path cannot bypass the adult gate
- **WHEN** a player attempts to complete a concept-guided flow whose age or apparent age is below
  18
- **THEN** activation is still rejected by the deterministic preflight and the character remains
  pending

#### Scenario: Offline concept input leaves the deterministic surface intact
- **WHEN** every LLM profile is offline and a pending player runs `character concept`
- **THEN** the player receives the stable unavailable message, and the preset and custom creation
  commands behave exactly as before
