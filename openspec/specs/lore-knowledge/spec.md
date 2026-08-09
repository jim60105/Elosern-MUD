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
