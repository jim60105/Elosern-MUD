## MODIFIED Requirements

### Requirement: The codex defines a closed category-to-registry mapping

`world/rules/lore_knowledge.py` SHALL define `CODE_CATEGORIES` as a bounded mapping from each of the eight codex categories to exactly one immutable lore registry loader and that category's declared card fields. A key SHALL be validated against its category's registry (`category:key`, never a subrace, threat-tier or variant key). Unknown categories and unresolvable keys SHALL reject with named errors.

#### Scenario: Every declared category resolves to exactly one registry
- **WHEN** the `CODE_CATEGORIES` mapping is inspected
- **THEN** each category maps to exactly this registry and these card fields, with no duplicate or missing entry; the map-owned categories resolve the currently published geography views and the others their static lore modules:

  ```
  | Category | Registry | Card fields |
  |---|---|---|
  | `race` | `world.lore.races.RACE_REGISTRY` | `display_name_zh`, `description` |
  | `nation` | `world.lore.nations.NATION_REGISTRY` | `display_name_zh`, `capital_name_zh` |
  | `region` | the published geography's composed region views | `display_name_zh`, `terrain_flavor_zh` |
  | `monster` | `world.lore.monster_species.MONSTER_SPECIES_REGISTRY` | `display_name_zh`, `published_appearance_zh` |
  | `element` | `world.lore.elements.ELEMENT_REGISTRY` | `display_name_zh`, `description` |
  | `magic` | `world.lore.magic.MAGIC_TIER_REGISTRY` | `display_name_zh`, `description` |
  | `anchor` | the published geography's composed location views | `display_name_zh`, `description` |
  | `guild` | `world.lore.guild.GUILD_RANK_REGISTRY` | `display_name_zh`, `description` |
  ```

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

#### Scenario: A threat-tier key is not a monster entry
- **WHEN** `record_lore_reveal(player, "monster", <key>)` is called with a key present in `MONSTER_TIER_REGISTRY` and absent from `MONSTER_SPECIES_REGISTRY`
- **THEN** the reveal rejects with `LoreKeyError` and the record is unchanged

### Requirement: The codex is discoverable with every generative service offline

At least one reveal source SHALL be reachable through purely deterministic play, so a player who never speaks to a generative NPC still accumulates codex entries. Every deterministic source SHALL write exclusively through the `world/rules/lore_knowledge.py` writers, so the append-only semantics, the repeat-is-a-no-op rule, and the sole-writer rule are unchanged.

#### Scenario: A codex fills with every generative profile failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and a character is created, travels to a registered anchor, and defeats a monster of a registered species
- **THEN** the codex holds the corresponding origin, anchor, and monster entries, the species is recorded as defeated, and no generative service was consulted

#### Scenario: Deterministic sources do not bypass the sole writer
- **WHEN** the deterministic reveal sources are inspected
- **THEN** each writes through `record_lore_reveal`, `record_species_sighting` or `record_species_defeat`, and none assigns `db.lore_discovered` or `db.lore_species_defeated` directly

## ADDED Requirements

### Requirement: Combat records the species it sighted and defeated

Creating a hostile combat session SHALL record a sighting of each distinct species among its hostile monsters for the session's player commander. A committed round in which a hostile monster's HP crosses from above zero to zero or below SHALL record a defeat of its species for each player character in the session. A monster without a species key, and any guild-examination session, SHALL record nothing. Recording SHALL run only after the commit.

#### Scenario: An engagement sights each species once
- **WHEN** a hostile session is created against two monsters of one species and one monster of another
- **THEN** exactly those two species are recorded as sighted for the commander, and neither is recorded as defeated

#### Scenario: A rolled-back engagement records nothing
- **WHEN** a hostile session's creation transaction rolls back
- **THEN** no sighting is recorded and no codex push occurs

#### Scenario: A lethal round records the defeat
- **WHEN** a committed hostile round takes a monster from positive HP to zero
- **THEN** its species is recorded as defeated and as sighted for each player character in the session

#### Scenario: A defeat outside the mapped wilderness still records
- **WHEN** the lethal round belongs to a hostile session with no mapped population cell
- **THEN** the species defeat is recorded

#### Scenario: Only a real crossing records
- **WHEN** a committed round ends with a monster that was already at zero HP before the round, or with a monster still above zero HP
- **THEN** no defeat is recorded for that monster

#### Scenario: A guild examination records nothing
- **WHEN** an opponent is defeated in a guild-examination session
- **THEN** no species defeat is recorded

#### Scenario: A species-less monster records nothing
- **WHEN** a monster whose `species_key` is unset is engaged or defeated
- **THEN** no sighting or defeat is recorded for it and no error is raised

#### Scenario: A defeat no longer reveals a tier
- **WHEN** any committed defeat is planned
- **THEN** no `monster:<threat tier>` reveal is scheduled

### Requirement: Monster research has a sighted and a defeated stage under dedicated writers

`record_species_sighting(player, species_key)` SHALL record `monster:<species_key>` through `record_lore_reveal`. `record_species_defeat(player, species_key)` SHALL add the key to the append-only set `player.db.lore_species_defeated` and SHALL also record the sighting. Both SHALL be idempotent. They SHALL reject an unknown species with `LoreKeyError`, and a corrupt record with `LoreRecordError`, leaving both records unchanged. Each SHALL schedule the codex push only when a record changed.

#### Scenario: A sighting records the species
- **WHEN** `record_species_sighting` is called for a registered species the player has not seen
- **THEN** `lore_discovered` gains `monster:<species_key>`, `lore_species_defeated` is unchanged, and one codex push is scheduled

#### Scenario: A defeat implies a sighting
- **WHEN** `record_species_defeat` is called for a registered species the player has never seen
- **THEN** `lore_discovered` gains `monster:<species_key>` and `lore_species_defeated` gains the key

#### Scenario: Repeats are no-ops
- **WHEN** the same sighting or defeat is recorded a second time
- **THEN** both records are unchanged and no codex push is scheduled

#### Scenario: An unknown species rejects without change
- **WHEN** either writer is called with a key absent from the species registry
- **THEN** it raises `LoreKeyError` and neither record changes

#### Scenario: A corrupt defeated record is never repaired
- **WHEN** `lore_species_defeated` holds a value that is not a set of registered species keys and `record_species_defeat` is called
- **THEN** it raises `LoreRecordError`, neither record changes, and the stored value is not rewritten

#### Scenario: The defeated reader is deterministic
- **WHEN** `list_species_defeated(player)` reads a player who defeated two species
- **THEN** it returns exactly those keys in sorted order, an absent record reads as empty, and the tolerant form keeps a well-formed key that no longer resolves

#### Scenario: Best-effort scheduling never fails play
- **WHEN** a scheduled sighting or defeat raises inside its post-commit callback
- **THEN** the failure is logged through the observability facade with its exception, and the triggering combat commit is unaffected

## REMOVED Requirements

### Requirement: Defeating a monster reveals its tier

**Reason**: The 魔物 codex category now resolves species, not threat tiers (design D5). A tier key no longer resolves in the category, so the defeat-time tier reveal could only fail. Defeats now record the species through the new "Combat records the species it sighted and defeated" requirement.

**Migration**: None (pre-release, no released users). The planner's tier reveal is deleted. Stored `monster:<tier>` identifiers are omitted by the tolerant presentation read.
