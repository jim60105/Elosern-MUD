## ADDED Requirements

### Requirement: The character concept command runs a guarded generative proposal pipeline
A pending character's command surface SHALL provide `character concept <構想>` (aliases 構想) that
takes a bounded free-form concept string, runs the guarded `character_creation` generative layer
with the injected client (composition-root pattern), and on a validated proposal presents the
proposal summary and interactively collects the display name, actual age, and apparent age
through the existing prompts and the deterministic adult gate, then activates through the ordinary
`CharacterCreationRequest` preflight and all-or-nothing activation path. When the LLM is offline,
retry-exhausted, or the layer degrades, the command SHALL return the stable Traditional Chinese
message (生成不可用，請手動創角) and SHALL NOT modify any character or account state; the
deterministic wizard remains fully usable.

#### Scenario: A concept guides an interactive custom activation
- **WHEN** a pending player runs `character concept` with a bounded concept and the guarded layer
  returns a valid proposal
- **THEN** the command presents the proposal's race, subrace, allocations, suggested skills, and
  persona preview, collects the player-entered name and both ages, and activates through the
  ordinary preflight and all-or-nothing activation with the proposal's values

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

### Requirement: Proposals are validated deterministically against the registries
The `character_creation` layer SHALL emit proposals of exactly
`{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`.
Every proposal SHALL be validated deterministically before any presentation or activation proceeds:
`race_key` and `subrace_key` exist in the lore registries and are compatible; `allocations` fall
within that race's bands; every `suggested_skills` key exists in the skill registry; and `persona`
contains exactly the three text fields with bounded lengths. The proposal SHALL NOT carry numeric
values beyond the allocation dict and SHALL NOT carry an age field: the LLM never chooses
mechanical numbers or ages, and the adult gate remains entirely player-entered and deterministically
validated. Any failure — including an invalid persona shape or over-length text — SHALL be treated
as a whole-proposal validation failure: the proposal SHALL be retried with the error appended and,
on exhaustion, degrade to the stable unavailable message; no partial proposal (for example race
accepted but persona discarded) SHALL ever proceed.

#### Scenario: A valid proposal passes and guides the flow
- **WHEN** the layer returns a proposal whose keys all resolve in the registries and whose
  allocations lie inside the race's bands
- **THEN** the proposal is accepted, its summary is presented, and no registration or activation
  state changes yet

#### Scenario: An unregistered race or skill key is rejected
- **WHEN** the proposal references a race, subrace, or skill key absent from the registries
- **THEN** the proposal is retried with the named validation error and never proceeds

#### Scenario: Out-of-band allocations are rejected
- **WHEN** the proposal's allocations exceed the race's allowed bands
- **THEN** the proposal is rejected with a named error and nothing proceeds

#### Scenario: An invalid persona rejects the whole proposal
- **WHEN** the proposal's persona is missing a field, has an extra field, or exceeds the length
  bounds
- **THEN** the whole proposal is rejected and retried with the named error; the race and
  allocations are never accepted independently of the persona

#### Scenario: An age or mechanical number in the proposal is rejected
- **WHEN** the proposal carries an age field or a numeric field outside the allocation dict
- **THEN** validation rejects the proposal and the adult gate remains the only age authority

### Requirement: The character_creation layer is registered in the guardrail with retry and degrade
`world/ai/` SHALL register a `character_creation` layer in the guardrail with an output jsonschema,
semantic validation, bounded retries that append the error message, and a stable degrade fallback;
malformed or out-of-contract output SHALL leave the database untouched and SHALL never produce a
partial result. The layer SHALL be added to `LAYER_NAMES` so `default_profiles()` constructs its
profile, SHALL be registered idempotently from `server/conf/at_server_startstop.py::at_server_start()`
like every existing layer, SHALL import no state writer, and SHALL consume the client through the
injected protocol like every other generative layer.

#### Scenario: Malformed output never touches the database
- **WHEN** the layer returns non-JSON, schema-invalid, or semantically invalid output for every
  retry
- **THEN** the call degrades to the stable unavailable message and no character, draft, or
  account attribute is written

#### Scenario: Startup registration installs the layer's schema, validators, and degrade
- **WHEN** `at_server_start()` runs with the `character_creation` layer enabled
- **THEN** the layer's output schema, semantic validators, and degrade fallback are registered
  and a prompt-library failure of `character_creation.system` degrades the layer without blocking
  startup

#### Scenario: Retry exhaustion follows the project degradation contract
- **WHEN** the first attempt fails validation and the appended-error retries also fail
- **THEN** the command returns the stable unavailable message without looping indefinitely
