## Purpose

Define the concept-to-proposal layer: a guarded generative pipeline that maps a
player's free-form character idea onto real registry keys (race, subrace,
allocations, suggested skills) plus a three-field persona draft, validates the
proposal deterministically against the lore and skill registries before
anything is presented or activated, and degrades to a stable offline message
that never touches character or account state.

## Requirements

### Requirement: The character concept command runs a guarded generative proposal pipeline
A pending character's command surface SHALL provide `character concept <構想>` (aliases 構想): it
takes a bounded free-form concept, runs the guarded `character_creation` layer with the injected
client (composition-root pattern), and on a validated proposal presents the summary, collects the
display name and both ages through the existing prompts, and activates through the ordinary
`CharacterCreationRequest` preflight and all-or-nothing activation path.

#### Scenario: A concept guides an interactive custom activation
- **WHEN** a pending player runs `character concept` with a bounded concept and the guarded layer
  returns a valid proposal
- **THEN** the command presents the proposal's race, subrace, allocations, suggested skills,
  persona preview, name, ages, background, and affinity set, collects the prefilled-or-overridden
  name and both ages, and activates through the ordinary preflight and all-or-nothing activation
  with the proposal's values

#### Scenario: The concept path cannot bypass the age-range check
- **WHEN** a player completes a concept-guided flow whose entered age or apparent age is outside the
  0..10000 range
- **THEN** activation is rejected by the deterministic preflight and the character remains pending

#### Scenario: Offline generation degrades without touching state
- **WHEN** every LLM profile is offline and a pending player runs `character concept`
- **THEN** the player receives the stable unavailable message, no character or account state
  changes, and the deterministic preset/custom wizard still works

#### Scenario: Over-long or empty concept input is rejected
- **WHEN** a pending player runs `character concept` with an empty or over-bound concept
- **THEN** the command rejects with a named error and no generative call is made

#### Scenario: The proposal's normalised values prefill the prompts
- **WHEN** a validated proposal is presented and the player reaches the name and age prompts
- **THEN** the prompt's prefilled default is the proposal's normalised value, an empty reply
  accepts the default, and a non-empty reply overrides it

#### Scenario: An absent proposal field leaves the mandatory prompt
- **WHEN** the proposal carries no value for one of the collected fields
- **THEN** the prompt stays mandatory, and an empty name reply re-prompts until answered or
  cancelled

#### Scenario: Activation is age-checked and carries the full proposal
- **WHEN** a concept-guided flow reaches activation
- **THEN** the deterministic age-range check gates it, and the activation carries the proposal's
  background and affinity elements alongside its other values

#### Scenario: Retry exhaustion or a layer degrade returns the stable message
- **WHEN** the generation is retry-exhausted or the `character_creation` layer degrades for any
  reason
- **THEN** the command SHALL return the stable Traditional Chinese message (生成不可用，請手動創角),
  SHALL NOT modify any character or account state, and the deterministic wizard remains fully
  usable

### Requirement: Proposals are validated deterministically against the registries
The `character_creation` layer SHALL emit proposals shaped
`{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`
plus five optional transient-fill fields `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`. Every proposal SHALL be validated deterministically against the registries
before any presentation or activation proceeds, and every structural failure is a
whole-proposal validation failure.

#### Scenario: A valid proposal passes and guides the flow
- **WHEN** the layer returns a proposal whose keys all resolve in the registries and whose
  allocations lie inside the race's bands
- **THEN** the proposal is accepted, its summary is presented, and no registration or activation
  state changes yet

#### Scenario: A proposal without a subrace is rejected
- **WHEN** the proposal's `subrace_key` is null, missing, or absent
- **THEN** validation rejects the whole proposal with a named error and it never proceeds

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

#### Scenario: An out-of-range proposal age is clamped to the range floor
- **WHEN** the proposal carries `age` or `apparent_age` below 0
- **THEN** the validated proposal carries that field overwritten to 0, no retry was consumed, no
  error was appended to the LLM, and the rest of the proposal is delivered intact

#### Scenario: An over-bound age and text are clamped and truncated, not discarded
- **WHEN** the proposal carries an age above 10000, a display name above 64 code points, or a
  background above 600 characters
- **THEN** each value is respectively clamped to 10000 or truncated to its bound and the proposal
  is delivered

#### Scenario: An over-bound or elf affinity set is trimmed
- **WHEN** the proposal's `affinity_elements` names an unregistered element, repeats a key, exceeds
  the chosen race's input bound, or accompanies an elf proposal
- **THEN** the validated proposal's affinity set drops the unknown and duplicate keys in order and
  is truncated to the race bound, or is empty for an elf, and the proposal is delivered

#### Scenario: An omitted optional field stays absent
- **WHEN** a valid proposal carries none of the five optional fields
- **THEN** the validated proposal exposes them as absent so the browser form and the Telnet prompts
  keep their own defaults

#### Scenario: A wrong-typed optional field is a structural failure
- **WHEN** the proposal carries a boolean age, a non-list `affinity_elements`, or any key outside
  the ten-field contract
- **THEN** validation rejects the whole proposal with a named error and the proposal is retried or
  degraded rather than partially normalised

#### Scenario: An omitted optional field normalises to its absent form
- **WHEN** the proposal omits one of the five optional transient-fill fields
- **THEN** it normalises to its absent form — a null text or age, or a null affinity set — so
  consumers keep their own local default

#### Scenario: The registry checks define proposal validity
- **WHEN** a proposal is validated
- **THEN** the checks are: `race_key` exists in the lore registry; `subrace_key` is a registered
  subrace belonging to that race (a null, missing, or incompatible subrace is a whole-proposal
  failure, since every race has at least one subrace); `allocations` fall within that race's
  bands and sum to the race budget; every `suggested_skills` key exists in the skill registry;
  and `persona` contains exactly the three text fields with bounded lengths

#### Scenario: An out-of-bounds transient fill is normalised in place
- **WHEN** a structurally valid proposal carries an in-range-typed but out-of-bounds
  transient-fill value
- **THEN** it is normalised in place on the validated proposal without any retry: a negative
  `age` or `apparent_age` is overwritten to 0 and above 10000 to 10000; an over-long
  `display_name` is truncated to the 64-code-point display-name bound and an over-long
  `background` to the 600-character persona-field bound, each collapsing to absent when it trims
  to empty; `affinity_elements` drops unknown and duplicate keys in order and truncates to the
  chosen race's input bound, and an elf proposal's affinity set is forced empty

#### Scenario: Normalisation is silent and the age check stays supreme
- **WHEN** any transient-fill normalisation applies
- **THEN** no error is appended to the LLM, no retry is consumed, the proposal is not discarded,
  and the deterministic age-range check remains the final authority on every submission

#### Scenario: The structural-failure set is closed
- **WHEN** the proposal is a non-object, carries a key outside the ten-field contract, a
  wrong-typed optional field, an invalid persona shape, an over-budget or out-of-band allocation,
  or a missing / incompatible subrace
- **THEN** it is treated as a whole-proposal validation failure

#### Scenario: A whole-proposal failure retries then degrades, never half-proceeds
- **WHEN** whole-proposal validation fails
- **THEN** the proposal is retried with the error appended and, on exhaustion, degrades to the
  stable unavailable message; no partial proposal (for example race accepted but persona
  discarded) ever proceeds

### Requirement: The character_creation layer is registered in the guardrail with retry and degrade
`world/ai/` SHALL register a `character_creation` layer in the guardrail with an output jsonschema,
semantic validation, bounded retries that append the error message, and a stable degrade fallback.
The layer SHALL be added to `LAYER_NAMES` so `default_profiles()` constructs its profile, SHALL be
registered idempotently from `server/conf/at_server_startstop.py::at_server_start()` like every
existing layer.

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

#### Scenario: Malformed output is never a partial result
- **WHEN** the layer returns malformed or out-of-contract output
- **THEN** the database is left untouched and no partial result is ever produced

#### Scenario: The layer obeys the generative-module contract
- **WHEN** the `character_creation` layer module is inspected
- **THEN** it imports no state writer and consumes the client through the injected protocol
  like every other generative layer

### Requirement: The concept prompt requests the expanded blueprint and the race-affinity bound
The `character_creation.system` prompt SHALL render a blueprint contract that names all ten
contract fields including `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`, SHALL instruct that `affinity_elements` must not exceed the chosen race's
listed bound and must be empty for an elf, and SHALL bound `background` to 600 characters.

#### Scenario: The blueprint names the expanded fields
- **WHEN** the `character_creation.system` prompt is rendered
- **THEN** its contract JSON names `display_name`, `age`, `apparent_age`, `background`, and
  `affinity_elements` alongside the existing five keys, and contains no sentence forbidding an age
  field

#### Scenario: The prompt template states no age rule
- **WHEN** the authored prompt template (before player-concept interpolation) is inspected
- **THEN** it names no age bound, no range wording, and no instruction to leave the age to the
  player, and retains no blanket prohibition that would contradict the `background` or age fields
  it now requests

#### Scenario: The race catalog names affinity bounds
- **WHEN** `build_race_catalog()` renders
- **THEN** every race entry names its affinity input bound (human 2, beastfolk 1, elf 0) derived
  from the shared bound mapping rather than a duplicated literal, and the catalog respects its
  bounded maximum length

#### Scenario: The race catalog names the element keys
- **WHEN** `build_race_catalog()` renders
- **THEN** the catalog names every registered element key as the only values `affinity_elements`
  may carry, and the element line stays inside the catalog's bounded maximum length

#### Scenario: The catalog lets the model respect the bounds without inventing values
- **WHEN** the registry-derived race catalog is rendered
- **THEN** it names each race's affinity input bound and the registered element keys so the
  model can respect them without inventing values

#### Scenario: The catalog stays inside its bounded length
- **WHEN** the race catalog is assembled at any registry size
- **THEN** it stays within its existing bounded length with the established truncation marker

#### Scenario: Age bounds are enforced server-side, not in the template
- **WHEN** the authored prompt template (before player-concept interpolation) is inspected for
  age guidance
- **THEN** it states no age-range constraint and does not otherwise instruct the model about the
  0..10000 bounds — age enforcement is server-side clamping — and carries no age-related
  instruction beyond naming the field
