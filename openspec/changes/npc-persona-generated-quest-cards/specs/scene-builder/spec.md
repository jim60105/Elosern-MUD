## REMOVED Requirements

### Requirement: NPC characterization carries an optional authored persona block for look flavor
**Reason**: Every NPC now carries a complete compact card; the optional `background` and three-field flavor block are replaced end to end.
**Migration**: See "NPC characterization carries a complete compact card through compile, restore, and materialization". Stored pre-change payloads are rewritten once by `npc-persona-roster-cutover`; no decoder for the old shape exists.

## ADDED Requirements

### Requirement: NPC characterization carries a complete compact card through compile, restore, and materialization
Every occupant characterization on a `StageSpawnRequirement` SHALL carry a complete compact NPC
card. The compiled requirement, the canonical payload, and the durable generated-quest payload SHALL
store the normalized card, and decoding a durable payload SHALL reproduce it unchanged; a payload
whose occupant card is missing or does not satisfy the card contract SHALL fail decoding with an
error naming the quest, stage, and occupant, with no fallback decoder. Materialization SHALL
revalidate the card through the shared characterization helper before any spawn and SHALL write it
through the deterministic NPC persona initializer with `generated_quest` provenance naming the
quest, stage, and occupant position, inside the same atomic materialization. Re-materializing a
stage SHALL never overwrite an existing occupant's card. The card is characterization only and
SHALL never influence stored stats.

#### Scenario: A card survives compile and restore unchanged
- **WHEN** a blueprint occupant card is compiled, encoded into the durable store, decoded at restore, and materialized
- **THEN** the spawned NPC's persona equals the normalized proposal card leaf for leaf and its metadata is at version 1 with `generated_quest` provenance

#### Scenario: A forged requirement cannot bypass validation
- **WHEN** a `StageSpawnRequirement` is constructed directly with an occupant card that violates the contract and materialization runs
- **THEN** materialization raises before any spawn and no room, NPC, or binding persists

#### Scenario: A pre-change payload fails restore by name
- **WHEN** the durable store holds a payload whose occupant carries the old optional prose block or no card
- **THEN** restore raises naming the quest, stage, and occupant, and no partial registration remains

#### Scenario: Re-materialization keeps an edited occupant card
- **WHEN** an occupant's card was edited to version 2 and the same stage is materialized again idempotently
- **THEN** the occupant's card and version 2 are unchanged
