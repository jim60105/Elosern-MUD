## MODIFIED Requirements

### Requirement: The character concept command runs a guarded generative proposal pipeline
A pending character's command surface SHALL provide `character concept <構想>` (aliases 構想) that
takes a bounded free-form concept string, runs the guarded `character_creation` generative layer
with the injected client (composition-root pattern), and on a validated proposal presents the
proposal summary and interactively collects the display name, actual age, and apparent age through
the existing prompts with the proposal's normalised values as prefilled defaults — an empty reply
accepts the default, a non-empty reply overrides it, and an absent proposal field leaves the
mandatory prompt, whose empty name reply re-prompts until answered or cancelled — checked by the
deterministic adult gate, then activates through the
ordinary `CharacterCreationRequest` preflight and all-or-nothing activation path carrying the
proposal's background and affinity elements alongside its other values. When the LLM is offline,
retry-exhausted, or the layer degrades, the command SHALL return the stable Traditional Chinese
message (生成不可用，請手動創角) and SHALL NOT modify any character or account state; the
deterministic wizard remains fully usable.

#### Scenario: A concept guides an interactive custom activation
- **WHEN** a pending player runs `character concept` with a bounded concept and the guarded layer
  returns a valid proposal
- **THEN** the command presents the proposal's race, subrace, allocations, suggested skills,
  persona preview, name, ages, background, and affinity set, collects the prefilled-or-overridden
  name and both ages, and activates through the ordinary preflight and all-or-nothing activation
  with the proposal's values

#### Scenario: The concept path cannot bypass the adult gate
- **WHEN** a player completes a concept-guided flow whose entered age or apparent age is below 18
- **THEN** activation is rejected by the deterministic preflight and the character remains pending

#### Scenario: Offline generation degrades without touching state
- **WHEN** every LLM profile is offline and a pending player runs `character concept`
- **THEN** the player receives the stable unavailable message, no character or account state
  changes, and the deterministic preset/custom wizard still works

#### Scenario: Over-long or empty concept input is rejected
- **WHEN** a pending player runs `character concept` with an empty or over-bound concept
- **THEN** the command rejects with a named error and no generative call is made
