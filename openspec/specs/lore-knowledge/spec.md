## Purpose

Define the player lore codex: the append-only discovered-knowledge store, its sole writer and
readers, the closed category-to-registry mapping, per-category card rendering, and the `lore`
command surface.

## Requirements

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
- **THEN** the card contains the entry's `display_name_zh` and `description` from the lore registry, and no
  opaque key

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

At least one reveal source SHALL be reachable through purely deterministic play, so a player who never speaks to a generative NPC still accumulates codex entries. Every deterministic source SHALL write exclusively through the `world/rules/lore_knowledge.py` writers, so the append-only semantics, the repeat-is-a-no-op rule, and the sole-writer rule are unchanged.

#### Scenario: A codex fills with every generative profile failing
- **WHEN** every `LLM_PROFILES` entry is configured to fail and a character is created, travels to a registered anchor, and defeats a monster of a registered species
- **THEN** the codex holds the corresponding origin, anchor, and monster entries, the species is recorded as defeated, and no generative service was consulted

#### Scenario: Deterministic sources do not bypass the sole writer
- **WHEN** the deterministic reveal sources are inspected
- **THEN** each writes through `record_lore_reveal`, `record_species_sighting` or `record_species_defeat`, and none assigns `db.lore_discovered` or `db.lore_species_defeated` directly

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

A deterministic reveal SHALL be best-effort: a rejection from the writer, a corrupt codex record, or
any other reveal failure SHALL NOT fail or roll back the arrival, the combat settlement, the character
creation, or the guild registration. The failure SHALL be reported through the observability facade
with its exception rather than swallowed silently. A reveal SHALL emit no player-facing message by
default, so it never interrupts movement or combat.

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

### Requirement: Combat records the species it sighted and defeated

Creating a hostile combat session SHALL record a sighting of each distinct species among its hostile monsters for each player character among the session's players. A committed round in which a hostile monster's HP crosses from above zero to zero or below SHALL record a defeat of its species for each player character in the session. A monster without a species key, and any guild-examination session, SHALL record nothing. Recording SHALL run only after the commit.

#### Scenario: An engagement sights each species once
- **WHEN** a hostile session is created against two monsters of one species and one monster of another
- **THEN** exactly those two species are recorded as sighted for each player character in the session, and neither is recorded as defeated

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
