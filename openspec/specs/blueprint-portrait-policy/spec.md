# blueprint-portrait-policy Specification

## Purpose

Define optional per-occupant portrait policy and story-driven characterization on quest blueprints:
`BlueprintNpcReq` may declare a `display_name`, paired `age`/`apparent_age`, and a named
`portrait.stable_key`, validated deterministically at the proposal and compile boundaries through
one shared bound helper and preserved through the whole blueprint lifecycle.

## Requirements

### Requirement: Quest blueprint npc_req entries may declare portrait policy and characterization
`BlueprintNpcReq` (the scenario director's `npc_req` entry shape) SHALL accept four optional
fields: `display_name` (bounded non-empty text), `age` and `apparent_age` (paired integers), and
`portrait` (an object with exactly one bounded `stable_key` field). A `portrait` block SHALL mean
the occupant carries a named portrait policy with `mode == "named"` and that `stable_key`; there
is no `mode` field in the blueprint. The adult invariant is a hard floor: every present
`age`/`apparent_age` value SHALL satisfy `type(value) is int` (booleans and `None` reject) with
`18 <= v`, and SHALL NOT exceed the race's `RaceProfile.lifespan` upper bound resolved from the
entry's tier through `NPC_TIER_REGISTRY[tier].race_key` — never a copied constant. `age` and
`apparent_age` SHALL be paired (both present or both absent); a key present with a `None` value is
not an absence and rejects. `portrait` SHALL be a mapping with exactly one `stable_key` field (no
extra keys) whose value is bounded non-empty text without colons or control characters, and not
digit-only — the digit-only region of the character-portrait keyspace is reserved for player
characters (whose stable keys are `str(pk)`), so a blueprint can never claim a player's portrait
subject. All four fields SHALL be optional; a blueprint without them SHALL validate and compile
exactly as today.
`BlueprintNpcReq.portrait` SHALL be a frozen value object so the blueprint's immutability-by-
construction guard (`_reject_mutable_containers`) is preserved.

#### Scenario: A named occupant with a story-driven age validates
- **WHEN** a blueprint stage declares `npc_req: [{"role": "librarian", "tier": "civilian", "display_name": "莉絲·晨星", "age": 68, "apparent_age": 68, "portrait": {"stable_key": "library_keeper"}}]`
- **THEN** the blueprint validates and carries all four fields through the whole lifecycle

#### Scenario: An elf of several centuries validates within the race lifespan band
- **WHEN** an `npc_req` entry with the shipped elven tier (`elven_civilian`) declares `age: 300, apparent_age: 300`
- **THEN** the values validate because 300 does not exceed the elf lifespan upper bound (1200)

#### Scenario: An unpaired age is rejected
- **WHEN** an `npc_req` entry declares `age` without `apparent_age`, or vice versa, or declares
  either key with a `None` value
- **THEN** the blueprint is rejected before any compilation

#### Scenario: An underage value is rejected
- **WHEN** an `npc_req` entry declares `age: 17` or `apparent_age: 17`
- **THEN** the blueprint is rejected — the adult floor is a hard invariant, never a warning

#### Scenario: Boolean and non-integer ages are rejected
- **WHEN** an `npc_req` entry declares `age: true`, `apparent_age: 30.5`, or any non-`int` value
- **THEN** the blueprint is rejected because the values do not satisfy `type(value) is int`

#### Scenario: A value beyond the race lifespan is rejected
- **WHEN** a human-tier entry declares `age: 120` (above the human lifespan upper bound) or an
  elven-tier entry declares `age: 1300` (above the elven lifespan upper bound)
- **THEN** the blueprint is rejected

#### Scenario: A malformed portrait object is rejected
- **WHEN** `portrait` is not a mapping, carries any key other than exactly one `stable_key`, or its
  `stable_key` is empty, colon-containing, control-character-containing, or overlong
- **THEN** the blueprint is rejected

#### Scenario: A digit-only portrait stable key is rejected
- **WHEN** an `npc_req` entry declares `portrait: {"stable_key": "7"}` (ASCII digits only)
- **THEN** the blueprint is rejected by the shared characterization helper, because the digit-only
  region of the character-portrait keyspace is reserved for player characters

#### Scenario: An empty or overlong display name is rejected
- **WHEN** `display_name` is empty, non-text, or exceeds its bound
- **THEN** the blueprint is rejected

#### Scenario: Duplicate stable keys must agree on characterization
- **WHEN** one blueprint declares two `npc_req` entries with the same `stable_key` but different
  `display_name` or ages
- **THEN** the blueprint is rejected; identical characterization under the shared key validates

### Requirement: The blueprint lifecycle preserves the characterization fields
The scenario director's output jsonschema SHALL declare the four optional fields; `to_payload()`
SHALL serialize them; `from_payload()` SHALL reconstruct them into the frozen value object; and the
canonical digest serialization (the content hash that distinguishes quests) SHALL include them. A
round trip `from_payload(to_payload(blueprint))` SHALL preserve all four fields, and two blueprints
that differ only in characterization SHALL yield different digest keys.

#### Scenario: A round trip preserves the characterization
- **WHEN** a blueprint carrying all four fields passes through `to_payload()` and back through
  `from_payload()`
- **THEN** the rebuilt blueprint carries identical display name, ages, and stable key

#### Scenario: Characterization differences change the content digest
- **WHEN** two blueprints are identical except one declares a different `display_name` or age
- **THEN** their canonical digest keys differ

#### Scenario: A field-less blueprint round-trips byte-identically
- **WHEN** a blueprint without optional fields passes through the lifecycle
- **THEN** its payload and digest are identical to today's output

### Requirement: The shared bound helper is the single validation rule source for both layers
A pure validation function SHALL exist under `world/quests/` (never under `world/ai/` and never
importing it) that validates the four optional fields against a resolved race-lifespan upper
bound, implementing exactly the rules above — including `type(value) is int`, missing-key-vs-
`None` distinction, and the exactly-one-`stable_key` portrait rule. The scenario director's
blueprint validation and the deterministic compile boundary SHALL both call this helper (the
scenario director imports it read-only, the same direction it already uses for `world/lore`
registries); neither SHALL inline the age/name/key checks itself. The adult floor SHALL be a named
constant in the helper.

#### Scenario: Both validation layers call the shared helper
- **WHEN** the blueprint validator and the compiler each validate an entry carrying the optional
  fields
- **THEN** both produce identical accept/reject decisions for identical input, and a repository
  test asserts no duplicated inline implementation of the age/name/key rules exists

#### Scenario: A race-bound change propagates without Python edits
- **WHEN** a race's `lifespan` upper bound changes in `world/lore/races.py`
- **THEN** both validation layers adopt the new bound on next import with no other code change

### Requirement: The compile boundary carries the characterization fields
`StageSpawnRequirement` (the deterministic requirements value the SceneBuilder consumes) SHALL
carry the optional `display_name`, paired `age`/`apparent_age`, and named-portrait `stable_key`
through from the accepted blueprint, validated by the shared helper. The requirements value SHALL
preserve the fields in deterministic order; a blueprint without them SHALL produce the exact
requirements shape it produces today; and the canonical content digest over the compiled
requirements SHALL include the characterization so identical scenes with different characterization
stay distinguishable.

#### Scenario: A compiled requirement preserves the optional fields
- **WHEN** an accepted blueprint with all four fields is compiled
- **THEN** `StageSpawnRequirement` exposes the display name, both ages, and the stable key in
  deterministic order

#### Scenario: A blueprint without the fields compiles unchanged
- **WHEN** an accepted blueprint declares no optional fields
- **THEN** the compiled requirements and their digest contribution are identical to today's output

### Requirement: The hand-written template pool may carry characterization fields
`world/ai/director_templates.py` SHALL be able to declare the four optional fields on its
`npc_reqs` entries; template quests go through the same validation as AI proposals, so a template
with malformed characterization fails template registration rather than producing a broken quest.

#### Scenario: A template with valid characterization registers
- **WHEN** a hand-written template declares a named occupant with paired adult ages within the
  race band
- **THEN** the template registers and its quests carry the characterization fields

#### Scenario: A template with an underage entry is rejected at registration
- **WHEN** a template declares `age: 17`
- **THEN** template registration rejects it before any quest can use it
