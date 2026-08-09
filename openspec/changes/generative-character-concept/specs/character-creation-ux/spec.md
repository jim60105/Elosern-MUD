## ADDED Requirements

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
