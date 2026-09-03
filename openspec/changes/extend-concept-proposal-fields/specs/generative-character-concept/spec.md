## MODIFIED Requirements

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

### Requirement: The concept prompt requests the expanded blueprint and the race-affinity bound
The `character_creation.system` prompt SHALL render a blueprint contract that names all ten
contract fields including `display_name`, `age`, `apparent_age`, `background`, and
`affinity_elements`, SHALL instruct that `affinity_elements` must not exceed the chosen race's
listed bound and must be empty for an elf, and SHALL bound `background` to 600 characters. The
prompt SHALL NOT state any adult-age constraint or otherwise instruct the model about the 18-year
floor: adult enforcement is server-side clamping, and the prompt carries no age-related
instruction beyond naming the field. The registry-derived race catalog SHALL name each race's
affinity input bound so the model can respect it without inventing numbers, and SHALL stay within
its existing bounded length with the established truncation marker.

#### Scenario: The blueprint names the expanded fields
- **WHEN** the `character_creation.system` prompt is rendered
- **THEN** its contract JSON names `display_name`, `age`, `apparent_age`, `background`, and
  `affinity_elements` alongside the existing five keys, and contains no sentence forbidding an age
  field

#### Scenario: The prompt states no adult-age rule
- **WHEN** the rendered prompt is inspected
- **THEN** it contains no age minimum, no adult wording, and no instruction to leave the age to the
  player

#### Scenario: The race catalog names affinity bounds
- **WHEN** `build_race_catalog()` renders
- **THEN** every race entry names its affinity input bound (human 2, beastfolk 1, elf 0) derived
  from the shared bound mapping rather than a duplicated literal, and the catalog respects its
  bounded maximum length
