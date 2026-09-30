## MODIFIED Requirements

### Requirement: The codex defines a closed category-to-registry mapping

`world/rules/lore_knowledge.py` SHALL define `CODE_CATEGORIES` as a bounded mapping from each
codex category to exactly one immutable lore registry:

| Category | Registry | Card fields |
|---|---|---|
| `race` | `world.lore.races.RACE_REGISTRY` | `display_name_zh`, `description` |
| `nation` | `world.lore.nations.NATION_REGISTRY` | `display_name_zh`, `capital_name_zh` |
| `region` | `world.lore.wilderness_regions.WILDERNESS_REGION_REGISTRY` | `display_name_zh`, `terrain_flavor_zh` |
| `monster` | `world.lore.monsters.MONSTER_TIER_REGISTRY` | `display_name_zh`, `description`, `example_monsters_zh` |
| `element` | `world.lore.elements.ELEMENT_REGISTRY` | `display_name_zh`, `description` |
| `magic` | `world.lore.magic.MAGIC_TIER_REGISTRY` | `display_name_zh`, `description` |
| `anchor` | `world.lore.anchors.ANCHOR_REGISTRY` | `display_name_zh`, `description` |
| `guild` | `world.lore.guild.GUILD_RANK_REGISTRY` | `display_name_zh`, `description` |

A category SHALL resolve exactly one registry; a key SHALL be validated against that registry
(`category:key` such as `race:elf`, never a subrace or tier key). Unknown categories and
unresolvable keys SHALL reject with named errors.

Every category's first card field SHALL be the entry's player-facing name, so a card never carries an
opaque registry key as its title or as a field value: a race's `display_name_zh` is a registry field
(人類 / 獸人 / 精靈), a guild rank's `display_name_zh` is its rank letter followed by 級 (`F 級`),
and a nation's `capital_name_zh` is the display name of the anchor its `capital_anchor_key` names.
The opaque keys stay the record and command identifiers (`race:elf`, `lore race elf`), so the `lore`
listing names each entry with its key in brackets (`精靈（elf）`).

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

### Requirement: Each category renders its own player-facing card

`lore_card(category, key)` SHALL render one registry entry as a player-facing card using exactly
that category's declared card fields from the mapping table, never a raw dataclass dump. A
resolvable key SHALL render deterministically; an unresolvable key SHALL raise a named error.

#### Scenario: A race card renders the canonical fields
- **WHEN** `lore_card("race", "elf")` resolves a known `RACE_REGISTRY` entry
- **THEN** the card contains the entry's `display_name_zh` and `description` from the lore registry, and no
  opaque key

#### Scenario: A region card includes terrain flavor
- **WHEN** `lore_card("region", ...)` resolves a known region
- **THEN** the card includes the region's `terrain_flavor_zh` entries

#### Scenario: An unresolvable key raises a named error
- **WHEN** `lore_card("race", "bogus")` is called
- **THEN** it raises a named error rather than fabricating a card
