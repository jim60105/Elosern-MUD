# npc-identity-titles Specification

## Purpose

Define the immutable, author-supplied NPC identity title: the single validator every authored write path validates against, the single deterministic composer of the 「姓名　稱號」 full identity, and the display contract that surfaces it only on the room character line, the look header, and the webclient exploration entity/interact rows while every other surface (echoes, compact panels, targeting, prompts) keeps the plain name byte-identical. Zero coupling with the player title system.

## Requirements

### Requirement: NPC titles are validated single-line plain text

The deterministic core SHALL expose one validator, `world.rules.npc_identity.validate_npc_title(value)`, as the single place every NPC-title write path validates against. It SHALL first normalize the value by stripping surrounding whitespace (of any kind, U+3000 included), and every acceptance decision below SHALL be made on that stripped form, which it SHALL return. It SHALL accept only a `str` (a `bool` is not a `str` and is rejected) whose stripped form contains 1 to 32 code points. It SHALL reject, by raising, a non-`str` value, a stripped form that is empty, a stripped form longer than 32 code points, a stripped form containing any internal whitespace character — including the full-width space U+3000 that the composer reserves as its separator — a stripped form containing any control character, and a stripped form containing the Evennia markup delimiter `|`. Rejection messages SHALL be stable English identifiers carrying no player-facing prose.

#### Scenario: A legal title round-trips stripped

- **WHEN** `validate_npc_title(" 南門守衛 ")` is called
- **THEN** it returns `"南門守衛"` with no surrounding whitespace

#### Scenario: Boundary lengths are decided exactly

- **WHEN** `validate_npc_title` is called with a 32-code-point title and again with a 33-code-point title
- **THEN** the 32-code-point value is accepted and the 33-code-point value is rejected

#### Scenario: Internal separator, whitespace, control, and markup characters are rejected

- **WHEN** `validate_npc_title` is called with a title containing an internal ASCII space, with one containing an internal full-width space U+3000, with one containing a control character, and with one containing `|`
- **THEN** every one of them is rejected, while a value differing from a legal title only by surrounding whitespace is accepted and normalized

#### Scenario: Non-text and empty values are rejected

- **WHEN** `validate_npc_title` is called with `None`, an integer, a boolean, `""`, or `"   "`
- **THEN** every one of them is rejected

### Requirement: The NPC title is a creation-time attribute with no runtime write surface

The `NPC` typeclass SHALL declare a persistent `npc_title` attribute through `AttributeProperty` with the default `""`, materialized lazily (no storage row exists until a write path assigns one). The default is a storage default for entities no authored creation path produced (test fixtures, transient scaffolds) — a degraded state the composer renders as the plain name, NOT a supported production creation shape: every production NPC path (import loader, SceneBuilder occupants, registry-backed hosts and examiners) is fail-closed at its own author face, owned by the later changes in this batch, and the typeclass deliberately provides no create-time title parameter because title validation belongs to those authored paths. This capability SHALL NOT introduce any runtime write surface for it: no setter method, no helper that assigns it, no player or staff command, and no generative or dialogue-intent path SHALL be able to change an NPC's title after creation. The only writers SHALL be authored creation paths, which validate through `validate_npc_title` before assigning. The guarantee is the absence of a title-specific write API on this capability's surfaces; Evennia's generic attribute access (`entity.db.npc_title = ...`) remains framework infrastructure deliberately outside the claim — tests seed malformed stored state through it.

#### Scenario: An untitled NPC is a degraded storage state, not a production path

- **WHEN** an `NPC` is created directly (e.g. a test fixture) with no title supplied
- **THEN** `npc_title` reads as `""`, every display surface renders the plain name, and the
  presentation degrades silently without error

#### Scenario: No runtime write surface exists

- **WHEN** the `NPC` typeclass surface and the registered command sets are inspected for a title write path
- **THEN** no title setter, title-assigning helper, or title-changing command is present

### Requirement: A single deterministic composer renders the NPC full identity

`world.rules.npc_identity` SHALL be the only place the NPC full identity is composed. `npc_title_value(entity)` SHALL return the entity's stored title as a `str`, and SHALL return `""` for an entity that is not an `NPC`, for a missing or empty title, for stored content that is not a non-empty string, for a stored string whose stripped form violates the validator's content rules (internal whitespace, control or non-printable characters, or the markup delimiter — such a row could never come from an authored path, and rendering it would put Evennia markup or a separator-ambiguous identity on screen), and for a title accessor that raises; a stored string that is content-legal but overlong SHALL still be returned, since length corruption is the documented degraded state the display bounds truncate rather than a render hazard. `npc_display_name(entity)` SHALL return `姓名` + U+3000 + `稱號` when both a renderable title and a readable plain key are present, the plain key when the title degrades, and `""` only when even the key is unreadable — never a separator-led composition. Both functions SHALL be pure reads that never write, never log, and never raise: malformed stored state SHALL degrade to the plain key so no presentation surface becomes unavailable over one title field, with accessor failure contained by narrow safe-read boundaries. The separator constant SHALL be held by this module itself and SHALL NOT be imported from the player title system, which this capability leaves entirely unchanged.

#### Scenario: A titled NPC composes with the full-width separator

- **WHEN** `npc_display_name` is called for an NPC named 塞提斯 whose title is 南門守衛
- **THEN** it returns `"塞提斯　南門守衛"` with exactly one U+3000 between the two parts

#### Scenario: An untitled NPC degrades to the plain name

- **WHEN** `npc_display_name` is called for an NPC whose title is `""`
- **THEN** it returns the plain key with no separator and no placeholder

#### Scenario: Players and monsters are never composed

- **WHEN** `npc_title_value` and `npc_display_name` are called for a player character and for a `Monster`
- **THEN** the title is `""` and the display name is the plain key

#### Scenario: Malformed stored state degrades instead of raising

- **WHEN** `npc_display_name` is called for an NPC whose stored title is a non-string value, a whitespace-only string, a string containing markup, internal whitespace or U+3000, or a control character, or whose title accessor raises, or when the title is absent
- **THEN** it returns the plain key and raises nothing

#### Scenario: An unreadable name never composes an ambiguous identity

- **WHEN** `npc_display_name` is called for an entity whose `key` is missing, raises, or renders empty while a title is stored
- **THEN** it returns `""` — never 「　稱號」 with a leading separator — and raises nothing

### Requirement: Full identity appears only on opt-in text display surfaces

`NPC.get_display_name` SHALL accept an opt-in `full_identity` keyword defaulting to false. With the flag absent or false, its return value SHALL be byte-identical to the pre-change plain-name output; with the flag true, it SHALL return `npc_display_name(self)`. Exactly two text surfaces SHALL pass the flag: the shared room character listing (`ObjectParent.get_display_characters`), and the look header of an NPC — the appearance-template name slot, so the text 「看 <目標>」 command, the `at_look` seam, and the webclient `explore.look` action stay identical to one another as the localized-appearance contract requires. Every other caller — movement, say, whisper, give and pickup echoes, the follow-lost notification, and combat text — SHALL NOT pass the flag and SHALL keep rendering the plain name. Passing the flag to a non-NPC character SHALL be accepted and SHALL render that entity's plain name.

#### Scenario: The room character listing shows the full identity

- **WHEN** a player looks at a room containing a titled NPC
- **THEN** the 「人物」 line shows 「姓名　稱號」 for that NPC

#### Scenario: The look header shows the full identity on every entry path

- **WHEN** a player looks at a titled NPC through the text 「看」 command, the `at_look` seam, and the webclient `explore.look` action
- **THEN** all three headers show 「姓名　稱號」 and the three appearances remain identical to one another

#### Scenario: Echo and notification text stays plain-name

- **WHEN** a titled NPC moves, speaks, whispers, is given an item, or is left behind by a following player
- **THEN** every resulting message names the NPC by its plain key only, byte-identical to the untitled rendering

#### Scenario: Players and monsters in the listing render plain names

- **WHEN** a room contains a player character and a monster alongside the titled NPC
- **THEN** the 「人物」 line renders their plain keys and no separator or placeholder appears for them

### Requirement: The webclient exploration panel renders the NPC full identity on entity and interact rows

The `exploration` panel SHALL source the `display_name` of its `look.entities` rows and its `interact` target rows from `npc_display_name`, so a titled NPC reads as 「姓名　稱號」 there. The room row, the `move` rows, and the `look.objects` rows SHALL keep their existing plain-key source. The panel's existing bounds SHALL NOT change: the composed identity is at most 97 code points (a key of at most 64, one separator, a title of at most 32), inside the 128-code-point display-name bound, and the rows SHALL keep their existing truncating (never raising) bounding behavior. The change SHALL NOT alter the panel schema version, field set, ordering, or availability rules.

#### Scenario: A titled NPC reads with its title on both row kinds

- **WHEN** the exploration panel is built for a player in a room with a titled NPC
- **THEN** that NPC's `look.entities` row and its `interact` target row both carry 「姓名　稱號」 as `display_name`

#### Scenario: Non-entity rows are untouched

- **WHEN** the same panel is built in a room carrying exits and present objects
- **THEN** the room row, the `move` rows, and the `look.objects` rows are byte-identical to their pre-change values

#### Scenario: The panel stays available for an untitled or malformed NPC

- **WHEN** the panel is built in a room with an untitled NPC and with an NPC whose stored title is malformed
- **THEN** both rows carry the plain key, the panel is available, and the payload validates

### Requirement: Compact presentation rows keep the plain NPC name

The compact deterministic view models SHALL keep rendering the NPC's plain key: combat participant rows (`world/rules/combat_view.py`), the portrait catalog entries (`world/rules/art_view.py`), and the guild/shop host rows (`world/rules/service_view.py`). These surfaces SHALL NOT consume `npc_display_name`, and each SHALL carry an assertion test pinning the plain-name rendering for a titled NPC so a later change cannot widen them silently.

#### Scenario: Combat participants stay plain-name

- **WHEN** a combat view is built with a titled NPC among the participants
- **THEN** that participant's `display_name` is the plain key with no separator or title

#### Scenario: Portrait catalog and host rows stay plain-name

- **WHEN** an art view is built for a room with a titled NPC and a service view is built for a titled guild or shop host
- **THEN** both rows carry the plain key with no separator or title

### Requirement: The NPC dialogue context carries the title as read-only data

`LLMNPC._npc_context()` SHALL include a `title` key whose value is `npc_title_value(self)` — the stored title, or `""` when the NPC is untitled. Building the context SHALL remain a pure read that never creates, persists, or mutates state. Adding the key SHALL leave every rendered dialogue prompt byte-identical, because the system-message renderer reads only the name, description, and location values.

#### Scenario: A titled NPC exposes its title to the dialogue context

- **WHEN** `_npc_context()` is called on a titled `LLMNPC`
- **THEN** the returned mapping's `title` value is that title and no stored state changed

#### Scenario: An untitled NPC exposes an empty title and an unchanged prompt

- **WHEN** `_npc_context()` is called on an untitled `LLMNPC` and a dialogue prompt is built from it
- **THEN** `title` is `""` and the rendered system message is byte-identical to the pre-change rendering

### Requirement: Command and search targeting matches the plain NPC key only

Player command and object-search targeting SHALL continue to resolve NPCs by their plain `key`. The title SHALL NOT be written into the key, registered as an alias, or added to any search index, so a player never has to type a title to address an NPC.

#### Scenario: The plain name still resolves a titled NPC

- **WHEN** a player targets a titled NPC by its plain name through an ordinary object search
- **THEN** the NPC resolves exactly as it did before the title existed

#### Scenario: The composed full identity is not a search key

- **WHEN** a player searches for the composed 「姓名　稱號」 string
- **THEN** the search does not resolve the NPC through that composed string

### Requirement: The existing appearance and exploration contracts are unchanged

This capability SHALL add the NPC title behavior without changing the requirement text of `localized-appearance` or `webclient-exploration-menu`: the zh-tw appearance frames, the affinity stage line, the displayed-stats block, the exploration panel's schema version, field set, and bounds all keep their current contracts. The title changes only which string fills an already-specified display-name slot.

#### Scenario: The zh-tw appearance frame is preserved

- **WHEN** a player looks at a room containing a titled NPC
- **THEN** the appearance still renders the 「出口」 and 「人物」 zh-tw frames, the affinity stage line, and the displayed-stats block exactly as specified today, with no English frame string

#### Scenario: The exploration panel contract is preserved

- **WHEN** the exploration panel is built in a room containing a titled NPC
- **THEN** the payload still validates against the unchanged schema version 1 field set and bounds
