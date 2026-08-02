## ADDED Requirements

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
