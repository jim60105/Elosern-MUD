# quest-blueprint Specification

## Purpose
The deterministic runtime's quest definition vocabulary — immutable, validated, registry-backed content
that change 20's AI `QuestBlueprint` must translate into. Hand-written offline quests consume this type
directly; no AI proposal dict ever enters the runtime registry.

## Requirements

### Requirement: QuestDefinition is the immutable deterministic input to quest runtime
`world/quests/definitions.py` SHALL define frozen, deeply immutable `QuestDefinition`, `QuestStage`,
`QuestObjective`, and `RoomLocator` dataclasses. `QuestDefinition.stages` SHALL be a tuple of
`QuestStage` values carrying explicit integer indices. No runtime definition field SHALL contain a
mutable dict or list. `QuestDefinition` SHALL be distinct from the future AI `QuestBlueprint` proposal
owned by change 20; raw mappings SHALL NOT be accepted by the runtime registry.

#### Scenario: Explicit stage indices are representable and preserved
- **WHEN** a definition is constructed with stages carrying indices 0 and 2
- **THEN** both explicit indices remain inspectable so registration can reject the gap

#### Scenario: Definition content cannot be mutated after validation
- **WHEN** a registered definition's stages, objective, or destination is accessed
- **THEN** no nested mutable collection is available through which validated content can be changed

#### Scenario: Raw AI-shaped data is not runtime input
- **WHEN** a plain dict shaped like design document §7.1's AI proposal is passed to
  `register_quest_definition()`
- **THEN** registration rejects it without modifying `QUEST_DEFINITION_REGISTRY`

### Requirement: Quest classifications and objective mechanics are separate closed vocabularies
`QuestType` SHALL contain exactly 採集, 討伐, 護衛, 探索, and 緊急. `ObjectiveKind` SHALL contain exactly
`DEFEAT`, `REACH`, and `ESCORT`. A quest type SHALL classify the complete definition and SHALL NOT
restrict which objective kinds its stages may use. ACQUIRE SHALL remain absent until change 16 can add it
at the inventory-owning transaction boundary.

#### Scenario: An emergency quest uses an ordinary completion mechanic
- **WHEN** a `QuestType.EMERGENCY` definition contains a `ObjectiveKind.DEFEAT` stage
- **THEN** it registers and resolves by the same DEFEAT rules as any other quest type

### Requirement: Destinations distinguish permanent locations from future bound instances
`DestinationKind` SHALL contain `ANCHOR`, `GRID`, and `BOUND_INSTANCE`. An ANCHOR locator SHALL carry
exactly one `anchor_key` present in `ANCHOR_PLACEMENT_REGISTRY`; a lore-known anchor without a placement
SHALL be rejected because it has no reachable room. A GRID locator SHALL carry exactly one `(x, y, z)`
tuple whose map key is known to the xyzgrid; a BOUND_INSTANCE locator SHALL carry neither and SHALL
resolve only through the accepted record's `stage_room_id`. Wilderness coordinates SHALL NOT be
representable by this change.

#### Scenario: An anchor destination is structurally valid
- **WHEN** a REACH objective names a key present in `ANCHOR_PLACEMENT_REGISTRY` through an ANCHOR locator
- **THEN** its definition registers without requiring a room dbref at module-import time

#### Scenario: Lore-known but unplaced anchor is rejected
- **WHEN** an ANCHOR locator names a lore anchor absent from `ANCHOR_PLACEMENT_REGISTRY`
- **THEN** registration raises `QuestDefinitionError` because no reachable `AnchorRoom` exists

#### Scenario: A malformed locator is rejected
- **WHEN** an ANCHOR locator also supplies XYZ coordinates, or a BOUND_INSTANCE locator supplies either
  static location field
- **THEN** registration raises `QuestDefinitionError` before mutating the registry

#### Scenario: Wilderness destination cannot be declared
- **WHEN** content attempts to declare a wilderness-coordinate destination
- **THEN** no `DestinationKind` value can represent it in this change

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

### Requirement: The hand-written catalog is idempotent and provides an offline quest
`world/quests/catalog.py` SHALL declare at least one deterministic introductory hunt using only
permanent world content and a DEFEAT objective. `world/quests/bootstrap.py::sync_quest_runtime()` SHALL
register that catalog idempotently on every server start. Repeating synchronization SHALL preserve one
registry entry per definition key and SHALL NOT create persistent quest records.

#### Scenario: Catalog synchronization is repeatable
- **WHEN** `sync_quest_runtime()` is called twice
- **THEN** the introductory quest is registered exactly once and no player's quest log changes

#### Scenario: Catalog works without generative services
- **WHEN** every AI service is unavailable
- **THEN** the introductory definition remains registered and can be accepted through the deterministic
  lifecycle API

### Requirement: REACH and ESCORT objectives accept only quantity one

Proposal validation and the quest compiler SHALL reject REACH and ESCORT objectives whose quantity is not exactly 1, because arrival observation cannot meaningfully accumulate repeated visits in the current model. ESCORT is additionally subject to the binding-path rule below.

#### Scenario: Quantity-two REACH proposal is rejected

- **WHEN** a generated or authored quest proposal declares a REACH objective with `quantity: 2`
- **THEN** the proposal is rejected at validation and no quest is registered

#### Scenario: Quantity-one REACH remains accepted

- **WHEN** a quest proposal declares a REACH objective with `quantity: 1`
- **THEN** the proposal compiles and registers normally

### Requirement: ESCORT quests require a bound protected entity path

The system SHALL refuse to publish an ESCORT quest unless its stage can actually bind at least one protected entity at runtime; an ESCORT stage whose scene constraints make binding impossible SHALL be rejected at proposal/compile time with a clear error instead of being registered uncompletable.

#### Scenario: Unbindable ESCORT proposal is rejected

- **WHEN** a proposal's ESCORT stage has no production path to bind a protected entity (e.g. a permanent location with no NPC requirement)
- **THEN** the proposal is rejected and never reaches the guild board

#### Scenario: Quantity-one ESCORT is still rejected without a binding path

- **WHEN** a proposal declares an ESCORT objective with `quantity: 1` but no protected-entity binding path
- **THEN** the proposal is rejected at validation and no quest is registered

#### Scenario: Currently, ESCORT requests are refused with a clear message

- **WHEN** a player requests an escort-generated quest while no binding flow exists
- **THEN** the request is refused with a clear player-facing message and no quest is registered

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

### Requirement: Published regional species hunts are legally provisionable in their authored region
A published regional species hunt SHALL be provisionable by the region's own authored placement: the hunt's
region SHALL have an ambient placement rule, at least one of the hunt's ordinary countable variants SHALL
be in that rule's eligible variant set (otherwise the acceptance-time guarantee could only ever refuse),
and the hunt's required quantity SHALL NOT exceed the region's authored per-coordinate legal supply —
`min(quantity, capacity)` of that rule. A region with no authored ambient placement SHALL carry no
regional hunt, because such a hunt could never be satisfied and the board is not an inventory of
impossible work. The shipped catalog SHALL carry exactly one regional hunt per species that a
placement-covered region actually places. This is a property of published content, not a promise that
every acceptance succeeds: the acceptance-time guarantee still refuses with its named reason when the
world is not provisioned or the region's authored capacity is momentarily exhausted.

#### Scenario: Every published hunt can be provisioned by its region
- **WHEN** each published regional hunt is compared against its region's authored ambient placement rule
- **THEN** the rule exists, at least one ordinary countable variant is eligible in it, and the hunt's quantity is at or below `min(quantity, capacity)`

#### Scenario: A region without authored placement carries no regional hunt
- **WHEN** the shipped catalog is inspected for a hunt naming a region that has no ambient placement rule
- **THEN** none exists, and the region's species presence is expressed only through its authored site content

#### Scenario: A hunt beyond the region's legal supply is not published
- **WHEN** a hunt's quantity exceeds its region's authored per-coordinate legal supply
- **THEN** the content contract reports it rather than letting the board offer work whose guarantee must refuse

#### Scenario: One hunt per placed species in a covered region
- **WHEN** a placement-covered region's ambient rule names variants of two species
- **THEN** the shipped catalog carries one hunt for each of them, each naming its own species and the countable variants that species owns

### Requirement: Every shipped hunt carries authored rank, rating rationale, background flavor, and a rank-banded reward
Every published hunt SHALL carry an authored guild rank, an authored rating rationale describing the risk
the arrangement, numbers, or terrain create, an authored background flavor describing the issuer's
motivation and local events, and a hand-written reward whose copper lies inside the rank's own reward band
in the guild-economy rulebook. The rank SHALL be authored for the arrangement and SHALL NOT be derived
from a targeted variant's individual danger grade: a run of hunts whose strongest countable or bound
individual is graded above the hunt's rank SHALL remain lawful and unchanged. The prose fields SHALL
describe effects and risks that actually exist in play and SHALL NOT assert an effect of a special ability
that has no mechanics.

#### Scenario: A hunt offers a reward inside its rank band
- **WHEN** each published hunt's registered guild offer is checked against its definition's rank
- **THEN** the reward copper lies inside that rank's reward band and the offer registers at the branch as an ordinary guild commission

#### Scenario: The rank is authored, not inherited from a danger grade
- **WHEN** a published hunt's countable or bound individuals carry a danger grade above the hunt's own rank
- **THEN** the hunt keeps its authored rank for board eligibility, reward band, and rendering

#### Scenario: Shipped prose asserts no unimplemented ability
- **WHEN** the published hunts' rating rationales and background flavors are inspected
- **THEN** they cite composition, numbers, and terrain, and none of them claims a special ability effect that has no executable mechanics

#### Scenario: The prose stays inside the rendered-detail budget
- **WHEN** every published hunt's rationale and flavor are validated at registration
- **THEN** each is bounded Traditional Chinese prose and the pair fits the shared rendered-detail budget
