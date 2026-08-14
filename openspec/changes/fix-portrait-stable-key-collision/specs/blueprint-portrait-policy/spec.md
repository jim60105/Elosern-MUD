## MODIFIED Requirements

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
exactly as today. `BlueprintNpcReq.portrait` SHALL be a frozen value object so the blueprint's
immutability-by-construction guard (`_reject_mutable_containers`) is preserved.

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
