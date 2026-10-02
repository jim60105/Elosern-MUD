## MODIFIED Requirements

### Requirement: Quest blueprint npc_req entries may declare portrait policy and characterization
`BlueprintNpcReq` (the scenario director's `npc_req` entry shape) SHALL require two per-occupant
identity fields: `display_name` (the authored name: bounded non-empty text validated through the
shared NPC name rule) and `title` (the authored NPC title: single-line plain text validated
through the shared NPC title rule). It SHALL additionally accept three optional fields: `age` and
`apparent_age` (paired integers), and `portrait` (an object with exactly one bounded `stable_key`
field). A `portrait` block SHALL mean the occupant carries a named portrait policy with
`mode == "named"` and that `stable_key`; there is no `mode` field in the blueprint. The age floor is
a hard bound: every present `age`/`apparent_age` value SHALL satisfy
`type(value) is int` (booleans and `None` reject) with `0 <= v`, and SHALL NOT exceed the race's
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
- **WHEN** a blueprint stage declares `npc_req: [{"role": "librarian", "tier": "civilian", "display_name": "莉絲‧晨星", "title": "城鎮圖書館員", "age": 68, "apparent_age": 68, "portrait": {"stable_key": "library_keeper"}}]`
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
- **WHEN** `title` exceeds its bound or contains whitespace, control characters, or the markup
  separator
- **THEN** the blueprint is rejected by the shared NPC title rule

#### Scenario: Duplicate stable keys must agree on characterization
- **WHEN** one blueprint declares two `npc_req` entries with the same `stable_key` but different
  `display_name`, title, or ages
- **THEN** the blueprint is rejected; identical characterization under the shared key validates
