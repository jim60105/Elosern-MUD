# blueprint-portrait-policy Specification

## Purpose

Define optional per-occupant portrait policy and story-driven characterization on quest blueprints:
`BlueprintNpcReq` may declare a `display_name`, paired `age`/`apparent_age`, and a named
`portrait.stable_key`, validated deterministically at the proposal and compile boundaries through
one shared bound helper and preserved through the whole blueprint lifecycle.

## Requirements

### Requirement: Quest blueprint npc_req entries may declare portrait policy and characterization
`BlueprintNpcReq` (the scenario director's `npc_req` entry shape) SHALL require two per-occupant
identity fields: `display_name` (the authored name: bounded non-empty text validated through the
shared NPC name rule) and `title` (the authored NPC title: single-line plain text validated
through the shared NPC title rule). It SHALL additionally accept three optional fields: `age` and
`apparent_age` (paired integers), and `portrait` (an object with exactly one bounded `stable_key`
field). A `portrait` block SHALL mean the occupant carries a named portrait policy with
`mode == "named"` and that `stable_key`; there is no `mode` field in the blueprint. The adult
invariant is a hard floor: every present `age`/`apparent_age` value SHALL satisfy
`type(value) is int` (booleans and `None` reject) with `18 <= v`, and SHALL NOT exceed the race's
`RaceProfile.lifespan` upper bound resolved from the entry's tier through
`NPC_TIER_REGISTRY[tier].race_key` — never a copied constant. `age` and `apparent_age` SHALL be
paired (both present or both absent); a key present with a `None` value is not an absence and
rejects. `portrait` SHALL be a mapping with exactly one `stable_key` field (no extra keys) whose
value is bounded non-empty text without colons or control characters, and not digit-only — the
digit-only region of the character-portrait keyspace is reserved for player characters (whose
stable keys are `str(pk)`), so a blueprint can never claim a player's portrait subject. An entry
missing `display_name` or `title` SHALL be rejected before any compilation.
`BlueprintNpcReq.portrait` SHALL be a frozen value object so the blueprint's immutability-by-
construction guard (`_reject_mutable_containers`) is preserved.

#### Scenario: A named occupant with a story-driven age validates
- **WHEN** a blueprint stage declares `npc_req: [{"role": "librarian", "tier": "civilian", "display_name": "莉絲·晨星", "title": "城鎮圖書館員", "age": 68, "apparent_age": 68, "portrait": {"stable_key": "library_keeper"}}]`
- **THEN** the blueprint validates and carries all fields through the whole lifecycle

#### Scenario: An elf of several centuries validates within the race lifespan band
- **WHEN** an `npc_req` entry with the shipped elven tier (`elven_civilian`) declares `age: 300, apparent_age: 300`
- **THEN** the values validate because 300 does not exceed the elf lifespan upper bound (1200)

#### Scenario: A missing authored name or title is rejected
- **WHEN** an `npc_req` entry omits `display_name` or `title`, or carries either as empty text
- **THEN** the blueprint is rejected before any compilation — the identity fields are required,
  never defaulted

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

#### Scenario: An invalid authored title is rejected
- **WHEN** `title` exceeds its bound or contains whitespace, control characters, or the markup
  separator
- **THEN** the blueprint is rejected by the shared NPC title rule

#### Scenario: Duplicate stable keys must agree on characterization
- **WHEN** one blueprint declares two `npc_req` entries with the same `stable_key` but different
  `display_name`, title, or ages
- **THEN** the blueprint is rejected; identical characterization under the shared key validates

### Requirement: The blueprint lifecycle preserves the characterization fields
The scenario director's output jsonschema SHALL declare the identity fields (`display_name`,
`title`) and the three optional fields; `to_payload()` SHALL serialize all five; `from_payload()`
SHALL reconstruct them into the frozen value object, rejecting a payload that lacks the required
`title` with a named compile error rather than a `KeyError`; and the canonical digest
serialization (the content hash that distinguishes quests) SHALL include them — including the
`title`. A round trip `from_payload(to_payload(blueprint))` SHALL preserve all fields, and two
blueprints that differ only in characterization (including only in `title`) SHALL yield different
digest keys.

#### Scenario: A round trip preserves the characterization
- **WHEN** a blueprint carrying all fields passes through `to_payload()` and back through
  `from_payload()`
- **THEN** the rebuilt blueprint carries identical display name, title, ages, and stable key

#### Scenario: Characterization differences change the content digest
- **WHEN** two blueprints are identical except one declares a different `display_name`, `title`,
  or age
- **THEN** their canonical digest keys differ

#### Scenario: Restoring a payload without the title fails with a named error
- **WHEN** `from_payload()` receives a characterization payload lacking `title`
- **THEN** it raises the named compile error identifying the missing field

### Requirement: The shared bound helper is the single validation rule source for both layers
A pure validation function SHALL exist under `world/quests/` (never under `world/ai/` and never
importing it) that validates every per-occupant field — requiring `display_name` and `title` —
against a resolved race-lifespan upper bound, implementing exactly the rules above — including
`type(value) is int`, missing-key-vs-`None` distinction, and the exactly-one-`stable_key` portrait
rule — and additionally enforcing the authored-name uniqueness rules across the entry set. The
title and name rules SHALL be obtained by delegating to the single shared validators in
`world/rules/npc_identity.py` via a function-local deferred import; neither validation layer SHALL
inline or duplicate the character-set rules itself. The scenario director's blueprint validation
and the deterministic compile boundary SHALL both call this helper (the scenario director imports
it read-only, the same direction it already uses for `world/lore` registries); neither SHALL inline
the age/name/title/key checks itself. The adult floor SHALL be a named constant in the helper.

#### Scenario: Both validation layers call the shared helper
- **WHEN** the blueprint validator and the compiler each validate an entry carrying the fields
- **THEN** both produce identical accept/reject decisions for identical input, and a repository
  test asserts no duplicated inline implementation of the age/name/title/key rules exists

#### Scenario: A race-bound change propagates without Python edits
- **WHEN** a race's `lifespan` upper bound changes in `world/lore/races.py`
- **THEN** both validation layers adopt the new bound on next import with no other code change

#### Scenario: Title rules live in exactly one module
- **WHEN** the title validation behaviour changes in `world/rules/npc_identity.py`
- **THEN** blueprint validation adopts it with no edit under `world/quests/` or `world/ai/`

### Requirement: The compile boundary carries the characterization fields
`StageSpawnRequirement` (the deterministic requirements value the SceneBuilder consumes) SHALL
carry the authored `display_name`, the authored `title`, and the optional paired
`age`/`apparent_age` and named-portrait `stable_key` through from the accepted blueprint, all
validated by the shared helper. The requirements value SHALL preserve the fields in deterministic
order, and the canonical content digest over the compiled requirements SHALL include the
characterization including `title` so identical scenes with different characterization stay
distinguishable.

#### Scenario: A compiled requirement preserves the fields
- **WHEN** an accepted blueprint with all fields is compiled
- **THEN** `StageSpawnRequirement` exposes the display name, title, both ages, and the stable key
  in deterministic order

#### Scenario: A title-only difference stays distinguishable after compile
- **WHEN** two accepted blueprints differ only in an occupant's `title`
- **THEN** their compiled requirements digests differ

### Requirement: The hand-written template pool may carry characterization fields
`world/ai/director_templates.py` SHALL declare the required `display_name` and `title` (and may
declare the optional fields) on its `npc_reqs` entries; template quests go through the same
validation as AI proposals, so a template with a missing or malformed identity fails template
registration rather than producing a broken quest.

#### Scenario: A template with valid identity and characterization registers
- **WHEN** a hand-written template declares a named occupant with a valid title and paired adult
  ages within the race band
- **THEN** the template registers and its quests carry the identity and characterization fields

#### Scenario: A template without an authored title is rejected at registration
- **WHEN** a template `npc_req` entry omits `title`
- **THEN** template registration rejects it before any quest can use it

#### Scenario: A template with an underage entry is rejected at registration
- **WHEN** a template declares `age: 17`
- **THEN** template registration rejects it before any quest can use it
