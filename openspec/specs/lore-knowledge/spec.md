## Purpose

Define the player lore codex: the append-only discovered-knowledge store, its sole writer and
readers, the closed category-to-registry mapping, per-category card rendering, and the `lore`
command surface.

## Requirements

### Requirement: The codex defines a closed category-to-registry mapping

`world/rules/lore_knowledge.py` SHALL define `CODE_CATEGORIES` as a bounded mapping from each
codex category to exactly one immutable lore registry:

| Category | Registry | Card fields |
|---|---|---|
| `race` | `world.lore.races.RACE_REGISTRY` | key, `description` |
| `nation` | `world.lore.nations.NATION_REGISTRY` | `display_name_zh`, `capital_anchor_key` |
| `region` | `world.lore.wilderness_regions.WILDERNESS_REGION_REGISTRY` | `display_name_zh`, `terrain_flavor_zh` |
| `monster` | `world.lore.monsters.MONSTER_TIER_REGISTRY` | `display_name_zh`, `description`, `example_monsters_zh` |
| `element` | `world.lore.elements.ELEMENT_REGISTRY` | `display_name_zh`, `description` |
| `magic` | `world.lore.magic.MAGIC_TIER_REGISTRY` | `display_name_zh`, `description` |
| `anchor` | `world.lore.anchors.ANCHOR_REGISTRY` | `display_name_zh`, `description` |
| `guild` | `world.lore.guild.GUILD_RANK_REGISTRY` | key, `description` |

A category SHALL resolve exactly one registry; a key SHALL be validated against that registry
(`category:key` such as `race:elf`, never a subrace or tier key). Unknown categories and
unresolvable keys SHALL reject with named errors.

#### Scenario: Every declared category resolves to exactly one registry
- **WHEN** the `CODE_CATEGORIES` mapping is inspected
- **THEN** each of the eight categories maps to exactly the registry named above, with no duplicate
  or missing entry

#### Scenario: A key is validated against its category's registry
- **WHEN** `record_lore_reveal(player, "race", "elf")` is called with `elf` present in
  `RACE_REGISTRY`
- **THEN** the reveal is accepted

#### Scenario: A subrace key is not a race entry
- **WHEN** `record_lore_reveal(player, "race", "ciaran")` is called (`ciaran` exists only in
  `SUBRACE_REGISTRY`)
- **THEN** the reveal rejects with a named error and the record is unchanged

### Requirement: The codex stores discovered entries append-only under one sole writer

`record_lore_reveal(player, category, key)` SHALL be the only API that writes
`player.db.lore_discovered`. The record SHALL be an append-only set of namespaced `category:key`
identifiers: a repeat reveal SHALL be a no-op, a category outside the mapping SHALL reject, and no
module other than this writer SHALL mutate the record. Readers (`list_discovered`, `lore_card`)
SHALL be pure.

#### Scenario: A first reveal records the entry
- **WHEN** `record_lore_reveal(player, "race", "elf")` is called for a player with no record
- **THEN** `player.db.lore_discovered` contains exactly the namespaced entry and the reveal
  reports success

#### Scenario: A repeat reveal is a no-op
- **WHEN** the same `(category, key)` is revealed a second time
- **THEN** the record is unchanged and the reveal still reports success

#### Scenario: An unknown category rejects
- **WHEN** `record_lore_reveal(player, "bogus", "x")` is called
- **THEN** it rejects with a named error and the record is unchanged

### Requirement: The codex reader returns a deterministic listing of discovered entries

`list_discovered(player)` SHALL return the discovered `(category, key)` pairs grouped and sorted
deterministically (by category mapping order, then key), and SHALL never include entries that were
not revealed. A malformed record SHALL make the listing unavailable with a diagnostic rather than
silently resetting or fabricating entries.

#### Scenario: The listing is deterministic and discovered-only
- **WHEN** a player has revealed entries in several categories
- **THEN** `list_discovered` returns exactly those pairs in category-mapping-then-key order, and
  nothing else

#### Scenario: A corrupt record degrades without reset
- **WHEN** `player.db.lore_discovered` holds malformed data
- **THEN** `list_discovered` reports an unavailable diagnostic and does not rewrite or fabricate
  the record

### Requirement: Each category renders its own player-facing card

`lore_card(category, key)` SHALL render one registry entry as a player-facing card using exactly
that category's declared card fields from the mapping table, never a raw dataclass dump. A
resolvable key SHALL render deterministically; an unresolvable key SHALL raise a named error.

#### Scenario: A race card renders the canonical fields
- **WHEN** `lore_card("race", "elf")` resolves a known `RACE_REGISTRY` entry
- **THEN** the card contains the entry's key and `description` from the lore registry

#### Scenario: A region card includes terrain flavor
- **WHEN** `lore_card("region", ...)` resolves a known region
- **THEN** the card includes the region's `terrain_flavor_zh` entries

#### Scenario: An unresolvable key raises a named error
- **WHEN** `lore_card("race", "bogus")` is called
- **THEN** it raises a named error rather than fabricating a card

### Requirement: The lore command shows discovered knowledge only

The character cmdset SHALL provide `lore` (no arguments) listing discovered entries grouped by
category, and `lore <category> <key>` rendering the card for one discovered entry. The command
SHALL check discovered-membership before rendering, and unknown categories, unknown keys, and
undiscovered entries SHALL all return the same fixed not-found line (byte-identical, no
variation), so registry existence is never leaked; the command SHALL never display an entry the
player has not revealed.

#### Scenario: Listing shows only discovered groups
- **WHEN** a player with two revealed entries runs `lore`
- **THEN** the output lists exactly those two entries under their categories and no others

#### Scenario: Viewing a discovered entry renders its card
- **WHEN** a player runs `lore race elf` for a revealed entry
- **THEN** the output is that entry's card

#### Scenario: Unknown and undiscovered targets share the same fixed line
- **WHEN** a player runs `lore` for an unknown category, an unknown key, or a known-but-unrevealed
  entry
- **THEN** the command returns the same fixed not-found line in every case and discloses nothing
  about the registry

### Requirement: The codex is discoverable with every generative service offline

At least one reveal source SHALL be reachable through purely deterministic play, so a player who
never speaks to a generative NPC still accumulates codex entries and the codex is never a guaranteed
empty surface. Every deterministic source SHALL write exclusively through `record_lore_reveal`, so
the append-only semantics, the repeat-is-a-no-op rule, and the sole-writer rule are unchanged.

#### Scenario: A codex fills with every generative profile failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and a character is created, travels to a
  registered anchor, and defeats a monster of a registered tier
- **THEN** the codex holds the corresponding origin, anchor, and monster entries and no generative
  service was consulted

#### Scenario: Deterministic sources do not bypass the sole writer
- **WHEN** the deterministic reveal sources are inspected
- **THEN** each writes through `record_lore_reveal` and none assigns `db.lore_discovered` directly

### Requirement: Arrival reveals the anchor and region a room resolves to

Entering a room that resolves to a registered anchor SHALL reveal that `anchor` entry, and entering a
room that resolves to a registered wilderness region SHALL reveal that `region` entry. A room
resolving to neither SHALL reveal nothing. The reveal SHALL occur on arrival, not on quest
acceptance and not on merely knowing a destination exists, so the codex records where the character
has actually been.

#### Scenario: Arriving at an anchor records it
- **WHEN** a character enters a room resolving to a registered anchor for the first time
- **THEN** that anchor entry is present in the character's codex

#### Scenario: Arriving in a region records it
- **WHEN** a character enters a wilderness room resolving to a registered region
- **THEN** that region entry is present in the character's codex

#### Scenario: An unremarkable room reveals nothing
- **WHEN** a character enters a room resolving to no registered anchor and no registered region
- **THEN** the codex is unchanged

#### Scenario: Re-entering reveals nothing new
- **WHEN** a character re-enters a room whose anchor is already discovered
- **THEN** the codex is unchanged and no error is raised

### Requirement: Defeating a monster reveals its tier

A committed defeat of a monster carrying a registered monster tier SHALL reveal that `monster` entry
for the character credited with the defeat. A defeat carrying no tier, or a tier absent from the
registry, SHALL reveal nothing. A simulated defeat SHALL reveal nothing, matching the existing rule
that a simulated battle grants no DEFEAT progress.

#### Scenario: A first kill of a tier records it
- **WHEN** a character commits a defeat of a monster of a registered tier
- **THEN** that monster-tier entry is present in the character's codex

#### Scenario: A simulated defeat records nothing
- **WHEN** a defeat is marked simulated, as in a guild examination
- **THEN** the codex is unchanged

#### Scenario: An untiered defeat records nothing
- **WHEN** a committed defeat carries no monster tier or a tier absent from the registry
- **THEN** the codex is unchanged

### Requirement: Origin reveals seed the codex at creation and registration

Completing character creation SHALL reveal the character's chosen `race` entry and its `nation`
entry, and completing guild registration SHALL reveal the registrant's `guild` rank entry. A chosen
value that resolves to no registry entry — a subrace rather than a race, for instance — SHALL reveal
nothing rather than rejecting the creation or the registration.

#### Scenario: A new character starts with its origin entries
- **WHEN** character creation completes for a character with a registered race and nation
- **THEN** those two entries are present in the character's codex

#### Scenario: Registering reveals the starting rank
- **WHEN** a character completes guild registration
- **THEN** that guild rank entry is present in the character's codex

#### Scenario: An unresolvable origin value reveals nothing and blocks nothing
- **WHEN** a chosen value resolves to no entry in its category's registry
- **THEN** the codex is unchanged and the creation or registration still completes

### Requirement: A reveal never blocks or fails the play that triggered it

A deterministic reveal SHALL be best-effort with respect to the operation that triggered it: a
rejection from the writer, a corrupt codex record, or any other reveal failure SHALL NOT fail or roll
back the arrival, the combat settlement, the character creation, or the guild registration. The
failure SHALL be reported through the observability facade with its exception rather than swallowed
silently. A reveal SHALL emit no player-facing message by default, so it never interrupts movement or
combat.

#### Scenario: A corrupt codex record does not break movement
- **WHEN** a character with a malformed `lore_discovered` record enters a registered anchor
- **THEN** the movement completes normally, the codex record is neither reset nor rewritten, and the
  failure is logged through the facade with its exception

#### Scenario: A reveal failure does not roll back combat settlement
- **WHEN** a reveal raises during the settlement of a committed defeat
- **THEN** the combat settlement commits unchanged and the failure is logged

#### Scenario: A reveal is silent
- **WHEN** any deterministic reveal succeeds
- **THEN** no message is sent to the character
