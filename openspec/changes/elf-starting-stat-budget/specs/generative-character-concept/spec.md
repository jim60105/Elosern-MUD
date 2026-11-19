## MODIFIED Requirements

### Requirement: Proposals are validated deterministically against the registries
The `character_creation` layer SHALL emit proposals shaped
`{race_key, subrace_key, allocations, suggested_skills, persona{personality, life_story, habit}}`
plus five optional transient-fill fields `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`. Every proposal SHALL pass deterministic registry and custom allocation policy
validation before presentation or activation. A structural failure SHALL reject the whole proposal.

#### Scenario: A valid proposal passes and guides the flow
- **WHEN** the layer returns a proposal whose keys all resolve in the registries and whose
  allocations satisfy the selected custom profile
- **THEN** the proposal is accepted, its summary is presented, and no registration or activation
  state changes yet

#### Scenario: A proposal without a subrace is rejected
- **WHEN** the proposal's `subrace_key` is null, missing, or absent
- **THEN** validation rejects the whole proposal with a named error and it never proceeds

#### Scenario: An unregistered race or skill key is rejected
- **WHEN** the proposal references a race, subrace, or skill key absent from the registries
- **THEN** the proposal is retried with the named validation error and never proceeds

#### Scenario: Out-of-band allocations are rejected
- **WHEN** the proposal violates a selected axis point cap or the exact custom budget
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
  failure, since every race has at least one subrace); `allocations` respect the selected custom profile's point caps and exact budget; every `suggested_skills` key exists in the skill registry;
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

#### Scenario: A proposed elf allocation travels unchanged
- **WHEN** a valid custom elf proposal passes the guarded layer
- **THEN** WebClient transient fill and Telnet continuation both use the same seven point values without creating a saved draft

#### Scenario: Retry feedback uses the selected profile
- **WHEN** a proposal with valid identity exceeds a point cap or misses the exact budget
- **THEN** the named validation error reports the applicable cap or budget from the same profile used by activation

## ADDED Requirements

### Requirement: Concept generation receives the custom allocation policy
The bounded race catalog SHALL expose the custom profile's point caps and exact budget for each selectable race and subrace.

#### Scenario: Policy data is rendered from the resolver
- **WHEN** the concept race catalog renders for synthetic race and subrace profiles
- **THEN** each listed profile's caps and budget match the custom resolver without hardcoded values in the prompt
