# Spec Delta

## MODIFIED Requirements

### Requirement: The codex defines a closed category-to-registry mapping

`world/rules/lore_knowledge.py` SHALL define `CODE_CATEGORIES` as a bounded mapping from each
codex category to exactly one immutable lore registry loader. Map-owned categories read the
published geography views at call time; the other categories read their static lore modules:

```
| Category | Registry | Card fields |
|---|---|---|
| `race` | `world.lore.races.RACE_REGISTRY` | `display_name_zh`, `description` |
| `nation` | `world.lore.nations.NATION_REGISTRY` | `display_name_zh`, `capital_name_zh` |
| `region` | the published geography's composed region views | `display_name_zh`, `terrain_flavor_zh` |
| `monster` | `world.lore.monsters.MONSTER_TIER_REGISTRY` | `display_name_zh`, `description`, `example_monsters_zh` |
| `element` | `world.lore.elements.ELEMENT_REGISTRY` | `display_name_zh`, `description` |
| `magic` | `world.lore.magic.MAGIC_TIER_REGISTRY` | `display_name_zh`, `description` |
| `anchor` | the published geography's composed location views | `display_name_zh`, `description` |
| `guild` | `world.lore.guild.GUILD_RANK_REGISTRY` | `display_name_zh`, `description` |
```

A category SHALL resolve exactly one registry; a key SHALL be validated
against that registry (`category:key` such as `race:elf`, never a subrace or tier key). Unknown
categories and unresolvable keys SHALL reject with named errors.

#### Scenario: Every declared category resolves to exactly one registry
- **WHEN** the `CODE_CATEGORIES` mapping is inspected
- **THEN** each of the eight categories maps to exactly the registry named above (the map-owned
  categories resolve the currently published geography views), with no duplicate or missing entry

#### Scenario: Every card's first field is the entry's player-facing name

- **WHEN** any category's card is rendered
- **THEN** the first card field is the entry's player-facing name, so a card never carries an opaque registry key as its title or as a field value: a race's `display_name_zh` is a registry field (人類 / 獸人 / 精靈), a guild rank's `display_name_zh` is its rank letter followed by 級 (`F 級`), and a nation's `capital_name_zh` is the display name of the composed location its `capital_anchor_key` names

#### Scenario: Opaque keys stay the record and command identifiers

- **WHEN** codex records and the `lore` command surface are inspected
- **THEN** the opaque keys stay the record and command identifiers (`race:elf`, `lore race elf`), and the `lore` listing names each entry with its key in brackets (`精靈（elf）`)

#### Scenario: A key is validated against its category's registry
- **WHEN** `record_lore_reveal(player, "race", "elf")` is called with `elf` present in
  `RACE_REGISTRY`
- **THEN** the reveal is accepted

#### Scenario: A subrace key is not a race entry
- **WHEN** `record_lore_reveal(player, "race", "ciaran")` is called (`ciaran` exists only in
  `SUBRACE_REGISTRY`)
- **THEN** the reveal rejects with a named error and the record is unchanged
