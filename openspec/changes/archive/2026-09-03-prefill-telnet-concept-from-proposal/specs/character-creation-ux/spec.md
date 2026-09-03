## MODIFIED Requirements

### Requirement: The creation surface offers a concept-driven custom entry
The pending-character creation command surface SHALL provide `character concept <構想>` (aliases
構想) as an additional entry into custom creation: a bounded free-form concept runs the guarded
`character_creation` generative layer, and a validated proposal is presented as a summary —
including the generated personality, life story, and habit prose and the proposal's display name,
both ages, background, and affinity elements — while the display name, actual age, and apparent age
are collected through the existing prompts as proposal-prefilled defaults: each prompt names the
proposal's value for its field, an empty reply accepts that default, and any non-empty reply
overrides it; a prompt whose proposal field is absent keeps the mandatory-input behaviour with
no default, and an empty or whitespace-only name reply there re-prompts the same prompt (until a
non-empty name or `cancel`) instead of proceeding to an activation doomed to be rejected. The completed request then flows through the ordinary `CharacterCreationRequest`
preflight and all-or-nothing activation carrying the proposal's race, subrace, allocations, persona
block, background, and affinity elements together with the accepted-or-entered name and ages. The
concept path SHALL persist no wizard draft and SHALL NOT alter activation semantics, the adult
identity gate, subrace compatibility checks, display-name validation, or the all-or-nothing atomic
activation in `world/rules.character_creation`. With the LLM offline the command SHALL return the
stable unavailable message and the ordinary preset/custom flows SHALL remain fully usable.

#### Scenario: A concept-guided flow reaches the ordinary activation path
- **WHEN** a pending player runs `character concept` and accepts the prefilled name and age
  defaults with empty replies
- **THEN** activation runs the unchanged deterministic preflight and all-or-nothing activation on
  the proposal's values, persona block, background, and affinity elements plus the accepted name
  and ages, and no draft was persisted at any step

#### Scenario: A typed reply overrides the prefilled default
- **WHEN** the player types a different name at the name prompt after a proposal supplied one
- **THEN** activation uses the typed name while the other proposal values still flow through
  unchanged

#### Scenario: An absent proposal field stays a mandatory prompt
- **WHEN** the proposal carried no display name and the player answers the name prompt with an
  empty or whitespace-only reply
- **THEN** the name prompt shows no default and re-prompts the same prompt until a non-empty name
  is typed, while `cancel` still aborts the flow

#### Scenario: The concept path cannot bypass the adult gate
- **WHEN** a player completes a concept-guided flow after typing an age below 18 over the prefilled
  default
- **THEN** activation is still rejected by the deterministic preflight and the character remains
  pending

#### Scenario: A clamped proposal age is accepted by Enter
- **WHEN** the proposal's age was normalised to the adult floor of 18 and the player accepts the
  prefilled default
- **THEN** activation passes the adult gate with the clamped value

#### Scenario: Offline concept input leaves the deterministic surface intact
- **WHEN** every LLM profile is offline and a pending player runs `character concept`
- **THEN** the player receives the stable unavailable message, and the preset and custom creation
  commands behave exactly as before
