## Purpose

Define the concept-to-proposal layer: a guarded generative pipeline that maps a
player's free-form character idea onto real registry keys (race, subrace,
allocations, suggested skills) plus a three-field persona draft, validates the
proposal deterministically against the lore and skill registries before
anything is presented or activated, and degrades to a stable offline message
that never touches character or account state.

## Requirements

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
The `character_creation` layer SHALL emit proposals shaped
`{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`
plus five optional transient-fill fields `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`; an omitted optional field SHALL normalise to its absent form (a null text or
age, or a null affinity set) so consumers keep their own local default. Every proposal SHALL be
validated deterministically before any presentation or activation proceeds: `race_key` exists in
the lore registry; `subrace_key` is a registered subrace belonging to that race (a null, missing,
or incompatible subrace is a whole-proposal failure, since every race has at least one subrace);
`allocations` fall within that race's bands and sum to the race budget; every `suggested_skills`
key exists in the skill registry; and `persona` contains exactly the three text fields with bounded
lengths. A structural failure — a non-object, a key outside the ten-field contract, a wrong-typed
optional field, an invalid persona shape, an over-budget or out-of-band allocation, or a missing /
incompatible subrace — SHALL be treated as a whole-proposal validation failure: the proposal SHALL
be retried with the error appended and, on exhaustion, degrade to the stable unavailable message;
no partial proposal (for example race accepted but persona discarded) SHALL ever proceed. An
in-range-typed but out-of-bounds transient-fill value SHALL instead be normalised in place on the
validated proposal without any retry: an `age` or `apparent_age` below 18 SHALL be overwritten to
18 and above 10000 to 10000; an over-long `display_name` SHALL be truncated to the 64-code-point
display-name bound and an over-long `background` to the 600-character persona-field bound (each
collapsing to absent when it trims to empty); `affinity_elements` SHALL drop unknown and duplicate
keys in order and truncate to the chosen race's input bound, and an elf proposal's affinity set
SHALL be forced empty. Normalisation SHALL never append an error to the LLM, consume a retry, or
discard the proposal, and the deterministic adult gate SHALL remain the final authority on every
submission.

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

#### Scenario: An underage proposal age is clamped to the adult floor
- **WHEN** the proposal carries `age` or `apparent_age` below 18
- **THEN** the validated proposal carries that field overwritten to 18, no retry was consumed, no
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

### Requirement: The concept prompt requests the expanded blueprint and the race-affinity bound
The `character_creation.system` prompt SHALL render a blueprint contract that names all ten
contract fields including `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`, SHALL instruct that `affinity_elements` must not exceed the chosen race's
listed bound and must be empty for an elf, and SHALL bound `background` to 600 characters. The
authored prompt template (before player-concept interpolation) SHALL NOT state any adult-age
constraint or otherwise instruct the model about the 18-year floor: adult enforcement is
server-side clamping, and the template carries no age-related instruction beyond naming the field.
The registry-derived race catalog SHALL name each race's affinity input bound and the registered
element keys so the model can respect them without inventing values, and SHALL stay within its
existing bounded length with the established truncation marker.

#### Scenario: The blueprint names the expanded fields
- **WHEN** the `character_creation.system` prompt is rendered
- **THEN** its contract JSON names `display_name`, `age`, `apparent_age`, `background`, and
  `affinity_elements` alongside the existing five keys, and contains no sentence forbidding an age
  field

#### Scenario: The prompt template states no adult-age rule
- **WHEN** the authored prompt template (before player-concept interpolation) is inspected
- **THEN** it names no age minimum, no adult wording, and no instruction to leave the age to the
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
