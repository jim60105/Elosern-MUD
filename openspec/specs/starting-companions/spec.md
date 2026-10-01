# starting-companions Specification

## Purpose

Let a player preset declare NPC starting companions as references to their own preset
cards, validate those declarations at load (lore-side shape plus rules-side
bounds), and build each declaration into a live, fully-configured LLMNPC that
mechanically mirrors the player version of the same card. Preset activation
builds, seeds, and binds every declared companion atomically.

## Requirements

### Requirement: A preset declares its starting companions by partner preset key
`world/lore/player_presets.py` SHALL define a frozen `StartingCompanion` carrying
exactly `preset_key` (the companion's own `PLAYER_PRESET_REGISTRY` key),
`affinity` (the value seeded into the companion's relationship record), and
`relationship` (the label composed into the companion's owner relationship
line). The declaration SHALL NOT carry an NPC profile reference: the partner
preset itself is the companion's single authored characterization source.
`PlayerPreset` SHALL carry a keyword-only `starting_companions` tuple of these
entries, defaulting to empty, so a preset that declares none behaves exactly as
it does today.

`PresetPersona` SHALL carry two optional NPC-need extension fields defaulting
to empty: `speech_style` (the compact card's speech leaf, which the player
persona record does not carry) and `greeting` (the companion's offline voice
line, single-paragraph plain text of at most 300 code points after the card
leaf normalization rule, a newline or overflow rejected at lore import).
Neither field SHALL be projected into the player persona record of a character
activated from the preset, so every preset's existing player-side persona
output is unchanged.

A companion's stats, skills, items, ages, and mechanical identity SHALL come
from the partner's own `PlayerPreset`, never from a second authored copy: the
twin who arrives as an NPC is mechanically the same character the player could
have chosen. The companion's persona SHALL derive from the partner preset's
persona (including its `speech_style` extension field) and SHALL NOT read or
copy any NPC profile, and declaring or building a companion SHALL NOT modify
any player preset.

`yuna_darknight` and `yuka_darknight` SHALL declare each other symmetrically at
affinity `95`, which is above the rulebook `invite_threshold` and inside the
至愛 stage with headroom, so a single negative delta cannot drop the pair a
stage and the companion can never be auto-dismissed on arrival.

A declaration SHALL fail at load, never at player activation. Lore-side
validation SHALL reject an unregistered `preset_key`, a preset naming itself,
and the same partner declared twice by one preset. Because `world/lore/` SHALL
NOT import `world/rules/`, the bounds derived from rules constants SHALL be
swept at `world/rules/` import time: a preset SHALL declare at most
`PARTY_MAX_COMPANIONS` companions, each `affinity` SHALL be an integer in
`1..NATURAL_CAP`, and, for an owner name of the maximum player-name length, the
compact card derived from the partner preset with the composed owner
relationship line SHALL satisfy the compact card contract's required-leaf,
leaf, and total bounds.

#### Scenario: The twins declare each other
- **WHEN** `PLAYER_PRESET_REGISTRY` is inspected
- **THEN** `yuna_darknight` declares `yuka_darknight` and `yuka_darknight` declares `yuna_darknight`, each at affinity `95` with a relationship label and no profile reference

#### Scenario: A preset without companions is unchanged
- **WHEN** any preset other than the four companion-declaring presets is inspected
- **THEN** its `starting_companions` is empty

#### Scenario: Extension fields never reach a player persona record
- **WHEN** a preset authors `speech_style` and `greeting` and its `PresetPersona.to_record()` is inspected
- **THEN** the record carries exactly its existing persona keys and neither extension value

#### Scenario: An invalid declaration is rejected at lore load
- **WHEN** a preset declares an unregistered partner key, names itself, or declares the same partner twice
- **THEN** importing `world.lore.player_presets` raises

#### Scenario: An out-of-bounds declaration is rejected at rules load
- **WHEN** a preset declares more than `PARTY_MAX_COMPANIONS` companions, an affinity below 1 or above `NATURAL_CAP`, or its partner preset cannot derive a card that holds the owner relationship line for a maximum-length owner name within the card bounds
- **THEN** importing `world.rules.starting_companions` raises from its registry sweep, naming the offending preset

### Requirement: A companion is built from its partner preset as a live LLMNPC
`world/rules/starting_companions.py` SHALL provide the deterministic builder
that turns one `StartingCompanion` declaration into a live NPC for one owning
player. The builder SHALL construct an `LLMNPC` — not a plain `NPC` — because
`commands/invite.py` accepts only an `LLMNPC`, so a companion the player later
dismisses must remain re-invitable through the ordinary invite surface.

The built NPC SHALL carry the attribute set
`world/imports/loader.py::_instantiate_validated_character` writes for a
character record: `race`, `subrace`, `sex`, the trait config, `skills`,
`skill_proficiency`, `inventory`, `affinity_elements`, `age`, `apparent_age`,
`persona`, and an explicit named `portrait_policy`. The trait values SHALL be
computed by the same shared pure helper the player path uses, so a companion
built from a preset and a player created from that preset resolve identical
values.

An elf companion's `affinity_elements` SHALL be seeded from its subrace, never
from the preset, matching the player rule. The builder SHALL apply the partner
preset's declared `starting_equipment` through
`world/rules/equipment.py::toggle_equipment`, and SHALL apply the lineage
closure and proficiency seed, so the companion is mechanically identical to the
player version of the same card.

The companion's persona SHALL be the compact NPC card derived from the partner
preset's persona by one shared deterministic rule: identity layers and the
personality, life-story, and habit leaves verbatim; `speech_style` from the
preset's extension field; the preset's authored appearance sub-keys flattened
in render order into the card's single appearance leaf; and
`social_connection` composed as one factual owner line naming the owning
player character and the declaration's `relationship` label, followed by the
preset's own social entries when it authors any. The builder SHALL write the
card through the deterministic NPC persona initializer with `companion`
provenance naming the partner preset key and the owning player, SHALL persist
the preset's authored `greeting` (when non-empty) to the NPC's own bounded
per-instance offline-greeting field in the same build, and SHALL NOT read, copy, or modify
any NPC profile or the partner preset itself. The derivation SHALL NOT project
the preset's `background` into the card.

The NPC's key SHALL be the partner preset's display name; when another
persisted entity already holds that key, the builder SHALL append a `-{pk}`
suffix, following `world/rules/guild_exams.py`'s existing disambiguation. The
`portrait_policy` stable key SHALL be the NPC's own pk, matching the player
portrait policy idiom, so a suffixed name never changes the portrait subject.

The builder SHALL NOT seed affinity, bind party membership, or write any player
state; those are the activation binding's responsibility.

#### Scenario: A companion mirrors its partner preset
- **WHEN** the builder runs for a declaration naming `yuka_darknight`
- **THEN** the resulting NPC's race, subrace, sex, trait values, skills, inventory, and ages all equal what activating `yuka_darknight` as a player would produce

#### Scenario: The companion's persona derives from its partner preset
- **WHEN** the builder runs for a declaration naming `yuka_darknight`
- **THEN** the NPC's persona is a valid compact card whose identity, personality, life-story, and habit leaves equal the `yuka_darknight` preset's persona, whose `speech_style` equals the preset's extension field, whose appearance leaf contains the preset's authored appearance sub-key values, its persona metadata is at version 1 with `companion` provenance naming that preset key and the owner, and the `yuka_darknight` preset itself is unchanged

#### Scenario: The companion speaks its own persisted greeting offline
- **WHEN** the builder completes for a preset that authors a `greeting`
- **THEN** the NPC's own offline-greeting field holds that greeting verbatim and is readable without any lore-registry lookup

#### Scenario: The companion is conversational and re-invitable
- **WHEN** the builder returns an NPC
- **THEN** it is an `LLMNPC` instance, so the `invite` command accepts it as a target

#### Scenario: An elf companion seeds affinity elements from its subrace
- **WHEN** the builder runs for an elf partner preset whose declared affinity set is empty
- **THEN** the NPC's `affinity_elements` equal the subrace's seed, not an empty set

#### Scenario: Declared equipment is worn by the companion
- **WHEN** the partner preset declares `starting_equipment`
- **THEN** the built NPC wears those items with their attached buffs and synced gauge ceilings, applied through the sole equipment writer

#### Scenario: The persona names the owning player
- **WHEN** the builder runs for a player character
- **THEN** the NPC's persona `social_connection` begins with one line naming that player and the declaration's relationship label

#### Scenario: Several player characters get independent companions
- **WHEN** two player characters activate presets that declare the same partner
- **THEN** two distinct NPCs exist, each persona naming its own owner, and editing one never changes the other or the preset

#### Scenario: A failed persona write leaves no companion
- **WHEN** the persona initializer rejects the derived card during a build
- **THEN** the partially built NPC is deleted and the error re-raised

#### Scenario: A taken name takes a suffix without changing the portrait subject
- **WHEN** another persisted entity already holds the partner preset's display name
- **THEN** the built NPC's key is that name with a `-{pk}` suffix, and its `portrait_policy` stable key is its own pk

#### Scenario: The builder writes no player or party state
- **WHEN** the builder completes
- **THEN** no affinity record exists for the pair, `player.db.party` is unchanged, and the NPC's `party_member` is unset

### Requirement: Preset activation builds, seeds, and binds every declared companion atomically
`activate_player_character` SHALL, for each `StartingCompanion` the selected
preset declares, build the companion NPC, seed its affinity toward the
activating player at the declared value, and bind it as a party companion —
all inside the same `transaction.atomic()` block that writes the player's own
identity, traits, skills, inventory, and equipment. A preset declaring no
companions SHALL behave exactly as before.

The companion step SHALL run after the player's own attribute writes, because
the builder places the NPC at `player.location` and `join_party` requires
co-location and a persisted player key. It SHALL run before the activation's
portrait finalization so the ordering of the existing steps is otherwise
unchanged.

The binding SHALL go through `world/rules/party.py::join_party`, which remains
the sole writer of party membership; activation SHALL NOT assign
`player.db.party` or `npc.db.party_member` directly. The affinity seed SHALL go
through the seed writer in `world/rules/affinity.py`, which remains the sole
module writing affinity values.

Any failure in the companion step — a build error, a rejected join, or a
refused seed — SHALL delete every companion NPC built during this activation and
re-raise, so the whole activation rolls back and no partially formed companion
survives. A companion SHALL NOT be best-effort: a character that arrives without
the companion its card declares silently contradicts the card the player chose.

Because the declared seed value is above the rulebook `invite_threshold`, the
party auto-leave recheck SHALL never dismiss a companion on arrival.

#### Scenario: Choosing a twin starts the game with the other in the party
- **WHEN** a pending player activates `yuna_darknight`
- **THEN** an NPC built from `yuka_darknight` exists at the player's location, `player.db.party` contains its dbid, its `party_member` names the player, and its affinity toward the player is the declared value

#### Scenario: The pairing is symmetric
- **WHEN** a pending player activates `yuka_darknight` instead
- **THEN** an NPC built from `yuna_darknight` joins the party under the same rules

#### Scenario: A preset without companions is unchanged
- **WHEN** a pending player activates any preset declaring no companions
- **THEN** activation writes exactly what it wrote before this change and `player.db.party` is empty

#### Scenario: A failed companion step rolls the whole activation back
- **WHEN** a failure is injected into the build, seed, or join of a declared companion
- **THEN** activation raises, the character remains pending with no identity, trait, or inventory state, no companion NPC is persisted, and `player.db.party` is unset

#### Scenario: The companion occupies one of the four party slots
- **WHEN** a player who started with one declared companion invites additional NPCs
- **THEN** the four-companion bound counts the starting companion, and the fifth join is rejected by the existing gate

#### Scenario: A dismissed starting companion stays re-invitable
- **WHEN** the player dismisses the starting companion with `leave`
- **THEN** the NPC remains in the room with its seeded affinity intact, and because that value is above the invite threshold the ordinary `invite` command can bind it again

#### Scenario: The arrival is never auto-dismissed
- **WHEN** the party auto-leave recheck runs immediately after activation
- **THEN** the companion's seeded value is above `invite_threshold` and the binding survives
