# blueprint-portrait-policy Specification

## Purpose

Define optional per-occupant portrait policy and story-driven characterization on quest blueprints:
`BlueprintNpcReq` may declare a `display_name`, paired `age`/`apparent_age`, and a named
`portrait.stable_key`, validated deterministically at the proposal and compile boundaries through
one shared bound helper and preserved through the whole blueprint lifecycle.

## Requirements

### Requirement: Quest blueprint npc_req entries may declare portrait policy and characterization
`BlueprintNpcReq` (the scenario director's `npc_req` entry shape) SHALL require the per-occupant
identity fields `display_name` (authored name: bounded non-empty text validated through the
shared NPC name rule), and SHALL accept the optional paired integers `age`/`apparent_age`
and a `portrait` object with exactly one bounded `stable_key` field.

#### Scenario: A named occupant with a story-driven age validates
- **WHEN** a blueprint stage declares `npc_req: [{"role": "librarian", "tier": "civilian", "display_name": "莉絲‧晨星", "age": 68, "apparent_age": 68, "portrait": {"stable_key": "library_keeper"}}]`
- **THEN** the blueprint validates and carries all fields through the whole lifecycle

#### Scenario: An elf of several centuries validates within the race lifespan band
- **WHEN** an `npc_req` entry with the shipped elven tier (`elven_civilian`) declares `age: 300, apparent_age: 300`
- **THEN** the values validate because 300 does not exceed the elf lifespan upper bound (1200)

#### Scenario: A missing authored name or title is rejected
- **WHEN** a current `npc_req` entry carries the removed title field or omits `display_name`/`persona`
- **THEN** the shared characterization validation rejects it before compile or template registration, while the title-free form retains all name/age/portrait/persona checks

#### Scenario: An unpaired age is rejected
- **WHEN** an `npc_req` entry declares `age` without `apparent_age`, or vice versa, or declares
  either key with a `None` value
- **THEN** the blueprint is rejected before any compilation

#### Scenario: A negative age value is rejected
- **WHEN** an `npc_req` entry declares `age: -1` or `apparent_age: -1`
- **THEN** the blueprint is rejected — the age floor of 0 is a hard bound, never a warning

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

#### Scenario: An invalid authored title is rejected
- **WHEN** a current `npc_req` entry carries the removed title field with any value
- **THEN** the shared characterization validation rejects it as a shape violation before compile or template registration, never converting it into identity text

#### Scenario: Duplicate stable keys must agree on characterization
- **WHEN** one blueprint declares two `npc_req` entries with the same `stable_key` but different
  `display_name` or ages
- **THEN** the blueprint is rejected; identical characterization under the shared key validates

#### Scenario: A portrait block means the named policy
- **WHEN** an `npc_req` entry carries a `portrait` block with a `stable_key`
- **THEN** the occupant carries a named portrait policy with `mode == "named"` and that
  `stable_key`, and there is no `mode` field in the blueprint

#### Scenario: The age ceiling resolves from the race lifespan
- **WHEN** an `npc_req` entry declares an `age` or `apparent_age`
- **THEN** the value SHALL NOT exceed the race's `RaceProfile.lifespan` upper bound resolved from
  the entry's tier through `NPC_TIER_REGISTRY[tier].race_key` — never a copied constant

#### Scenario: The age integer type check rejects booleans and None
- **WHEN** any present `age`/`apparent_age` value is checked
- **THEN** it SHALL satisfy `type(value) is int` (booleans and `None` reject) with `0 <= v`, the
  age floor being a hard bound

#### Scenario: A None-valued age key is not an absence
- **WHEN** an `npc_req` entry declares the `age` or `apparent_age` key with a `None` value
- **THEN** the blueprint is rejected, because a key present with a `None` value is not an absence

#### Scenario: Portrait stable keys exclude colons, control characters, and digits
- **WHEN** a `portrait` mapping's `stable_key` value is validated
- **THEN** it must be bounded non-empty text without colons or control characters, and not
  digit-only — the digit-only region of the character-portrait keyspace is reserved for player
  characters (whose stable keys are `str(pk)`), so a blueprint can never claim a player's
  portrait subject

#### Scenario: The portrait value object keeps the blueprint immutable
- **WHEN** `BlueprintNpcReq.portrait` is constructed
- **THEN** it is a frozen value object so the blueprint's immutability-by-construction guard
  (`_reject_mutable_containers`) is preserved

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written


### Requirement: The blueprint lifecycle preserves the characterization fields
The scenario director's output jsonschema SHALL declare the identity fields (`display_name`) and the three optional fields; `to_payload()` SHALL serialize all title-free characterization fields; `from_payload()`
SHALL reconstruct them into the frozen value object, rejecting removed title fields and missing required names with a named compile error; and the canonical digest serialization SHALL include all remaining characterization fields.

#### Scenario: A round trip preserves the characterization
- **WHEN** a blueprint carrying all fields passes through `to_payload()` and back through
  `from_payload()`
- **THEN** the rebuilt blueprint carries identical display name, ages, and stable key

#### Scenario: Characterization differences change the content digest
- **WHEN** two blueprints are identical except one declares a different `display_name` or age
- **THEN** their canonical digest keys differ

#### Scenario: Restoring a payload without the title fails with a named error
- **WHEN** a stored characterization payload carries the removed title field
- **THEN** `from_payload()` raises the named compile error instead of dropping the field, while a title-free payload restores unchanged

#### Scenario: Characterization-only differences yield different digest keys
- **WHEN** two blueprints differ only in characterization (including only in display_name)
- **THEN** they yield different digest keys

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written


### Requirement: The shared bound helper is the single validation rule source for both layers
A pure validation function SHALL exist under `world/quests/` (never under `world/ai/` and never
importing it) that validates every per-occupant field — requiring `display_name` —
against a resolved race-lifespan upper bound, implementing exactly the rules above. The scenario
director's blueprint validation and the deterministic compile boundary SHALL both call this
helper; neither SHALL inline the age/name/key checks itself.

#### Scenario: Both validation layers call the shared helper
- **WHEN** the blueprint validator and the compiler each validate an entry carrying the fields
- **THEN** both produce identical accept/reject decisions for identical input, and a repository
  test asserts no duplicated inline implementation of the age/name/key rules exists

#### Scenario: A race-bound change propagates without Python edits
- **WHEN** a race's `lifespan` upper bound changes in `world/lore/races.py`
- **THEN** both validation layers adopt the new bound on next import with no other code change

#### Scenario: Title rules live in exactly one module
- **WHEN** a current characterization carries the removed title field
- **THEN** the shared characterization helper is the one place that rejects it, on every path that validates an occupant

#### Scenario: The helper carries the full rule set
- **WHEN** the shared helper validates entries
- **THEN** it implements the rules including `type(value) is int`, the missing-key-vs-`None`
  distinction, and the exactly-one-`stable_key` portrait rule, and additionally enforces the
  authored-name uniqueness rules across the entry set

#### Scenario: Name and title rules come from the shared validators
- **WHEN** a current characterization input carries the removed title field
- **THEN** the shared characterization helper rejects it, and the surviving name rule still comes only from `world.rules.npc_identity`

#### Scenario: The scenario director imports the helper read-only
- **WHEN** the scenario director calls the shared helper
- **THEN** it imports it read-only from `world/quests/`, the same direction it already uses for
  `world/lore` registries

#### Scenario: The age floor is a named constant
- **WHEN** the shared helper enforces the age floor
- **THEN** the bound is a named constant in the helper

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written


### Requirement: The compile boundary carries the characterization fields
`StageSpawnRequirement` (the deterministic requirements value the SceneBuilder consumes) SHALL
carry the authored `display_name`, the optional paired
`age`/`apparent_age` and named-portrait `stable_key` through from the accepted blueprint, all
validated by the shared helper. The requirements value SHALL preserve the fields in deterministic
order.

#### Scenario: A compiled requirement preserves the fields
- **WHEN** an accepted blueprint with all fields is compiled
- **THEN** `StageSpawnRequirement` exposes the display name, both ages, and the stable key
  in deterministic order

#### Scenario: A title-only difference stays distinguishable after compile
- **WHEN** two inputs differ only by the removed title field
- **THEN** the title-bearing input is rejected before compile, so no removed field can influence the compiled digest

#### Scenario: The compiled digest includes the characterization
- **WHEN** the canonical content digest is computed over the compiled requirements
- **THEN** it includes the characterization excluding title, so identical scenes with different
  characterization stay distinguishable

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written


### Requirement: The hand-written template pool may carry characterization fields
`world/ai/director_templates.py` SHALL declare the required `display_name` (and may
declare the optional fields) on its `npc_reqs` entries; template quests go through the same
validation as AI proposals, so a template with a missing or malformed identity fails template
registration rather than producing a broken quest.

#### Scenario: A template with valid identity and characterization registers
- **WHEN** a hand-written template declares a named occupant with a validated authored name and paired
  canonical ages within the race band
- **THEN** the template registers and its quests carry the identity and characterization fields

#### Scenario: A template without an authored title is rejected at registration
- **WHEN** a hand-written template occupant carries the removed title field
- **THEN** template registration rejects it before any quest can use it

#### Scenario: A template with a negative-age entry is rejected at registration
- **WHEN** a template declares `age: -1`
- **THEN** template registration rejects it before any quest can use it

#### Scenario: Title-free contract is complete
- **WHEN** this source emits or validates an NPC characterization
- **THEN** display_name/persona and applicable role/tier, age-pair/race-lifespan, portrait-key, uniqueness and immutable-digest rules remain; no title field is accepted, required, serialized, prompted or written

