## MODIFIED Requirements

### Requirement: Registration validates every runtime-critical objective field
`register_quest_definition()` SHALL treat re-registering equal content under the same key as an
idempotent no-op and SHALL reject conflicting content under an existing key. It SHALL reject empty
stages, non-contiguous stage indices starting anywhere other than zero, non-positive quantities,
invalid destination shapes, unknown static location keys, and invalid objective parameters. DEFEAT
SHALL declare exactly one selector family: a known `monster_tier`, or `requires_bound_targets=True`, or
the complete regional species-hunt selector (a known region key, a known species key, and a non-empty
countable-variant tuple owned by that species); a partial hunt selector, or a hunt combined with the
tier or bound selector, is invalid. REACH SHALL declare
a destination; ESCORT SHALL declare a destination and SHALL be unable to complete until protected
runtime entities are bound. `deadline_hours` SHALL be either `None`, meaning no deadline, or a positive
integer.

#### Scenario: A complete hand-written definition registers
- **WHEN** a definition has contiguous stages and every objective supplies its required typed fields
- **THEN** `QUEST_DEFINITION_REGISTRY[definition.key]` is that immutable definition

#### Scenario: Non-contiguous stages are rejected
- **WHEN** stages carry indices 0 and 2
- **THEN** registration raises `QuestDefinitionError` and leaves the registry unchanged

#### Scenario: Equal registration is idempotent and conflicting registration is rejected
- **WHEN** equal content is registered twice and different content is then registered under the same key
- **THEN** the equal registration is a no-op, the conflicting registration raises
  `QuestDefinitionError`, and the original definition remains registered

#### Scenario: Objective fields are validated before play
- **WHEN** an ESCORT objective has no destination, a DEFEAT objective has no selector, or a quantity is
  zero
- **THEN** registration raises `QuestDefinitionError` rather than deferring failure to event handling

#### Scenario: Deadline None has one meaning
- **WHEN** a definition registers with `deadline_hours=None`
- **THEN** acceptance creates no deadline and no implicit default is applied

#### Scenario: A partial hunt selector is rejected
- **WHEN** a DEFEAT objective supplies a species key without a region key, or a species/variant pair without any countable variant
- **THEN** registration raises `QuestDefinitionError` and the registry is unchanged

## ADDED Requirements

### Requirement: Species-hunt objectives carry a validated region/species/variant selector
`QuestObjective` SHALL support the approved regional species-hunt semantics as a deterministic, deeply
immutable selector: a region key naming a key of `WILDERNESS_REGION_REGISTRY`, a species key naming a
key of `MONSTER_SPECIES_REGISTRY`, a positive quantity, and a non-empty tuple of countable variant keys.
Registration SHALL reject: an unknown region or species key; any countable variant key that is not a
registered variant owned by the declared species; a hunt that declares no ordinary baseline variant of
that species among its countable variants (the guarantee that ordinary-eligible living targets exist at
acceptance must be expressible); and a hunt combined with the tier selector or the bound-target flag
(a hunt declares exactly one selector family). Display names SHALL NOT participate in selector
resolution, and an ordinary hunt SHALL NOT be representable as "count every variant of every species in
a tier".

#### Scenario: A valid hunt registers
- **WHEN** a definition's DEFEAT stage declares region, species, quantity, and countable variant keys all owned by that species including at least one ordinary variant
- **THEN** the definition registers and the selector is preserved unchanged and deeply immutable

#### Scenario: A foreign variant key is rejected
- **WHEN** a hunt's countable variants include a variant owned by a different species
- **THEN** registration raises `QuestDefinitionError` and the registry is unchanged

#### Scenario: Two selectors at once is rejected
- **WHEN** a hunt objective also declares `monster_tier` or `requires_bound_targets=True`
- **THEN** registration raises `QuestDefinitionError`

#### Scenario: Names are never selectors
- **WHEN** a hunt is authored with a species display name instead of a species key
- **THEN** registration rejects it: only the shared stable-key form is a valid selector

### Requirement: Quest records carry grade, rating rationale, and background flavor as three separate authored fields
`QuestDefinition` SHALL keep the authored guild grade (`rank`, existing semantics unchanged) and SHALL
additionally carry two separately authored prose fields: a rating rationale explaining the risk the
authored arrangement, abilities, or terrain create, and a background flavor describing the issuer's
motivation and the local events — both readable offline with no generative service. A variant's
individual danger grade SHALL NOT propagate into or overwrite the definition's grade, and no
completion, failure, or progress rule SHALL read either prose field: completion derives only from the
structured objectives. The prose fields SHALL be bounded, immutable, and Traditional Chinese
player-facing text, and a definition MAY carry the rationale or flavor without any ability reference:
flavor SHALL NOT grant, imply, or require an unregistered ability.

#### Scenario: Three fields, three jobs
- **WHEN** a hunt definition authored with grade, rationale, and flavor is inspected
- **THEN** the grade is the guild-eligibility value, the rationale renders risk reasoning, the flavor renders issuer motivation, and no field is derived from another

#### Scenario: Danger grade does not become the quest grade
- **WHEN** a hunt targets a variant whose registry danger grade (once balance-approved) differs from the definition's authored rank
- **THEN** guild eligibility and rendering use the definition's rank only

#### Scenario: Flavor never completes a quest
- **WHEN** gameplay events that the flavor text narrates occur without satisfying the structured objectives
- **THEN** no progress, completion, or failure occurs
