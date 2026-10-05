## Purpose

Define the official content reference — a typed, validated (content kind, registered content key) pair naming reusable authored images in the mounted official directory — and the provenance rules that bind runtime entities to it without ever touching mutable gallery state, display-name inference, or an unapproved monster species catalog.

## ADDED Requirements

### Requirement: An official content reference is typed, validated, and provenance-derived
The engine SHALL represent an official content reference as a validated pair of a content kind — exactly one of `monster`, `preset`, `npc` — and a registered authored content key that satisfies the existing shared stable-key validation contract. A reference SHALL be derived only from an entity's stored provenance or an authored registry declaration, never from a display name, a translated label, a quest role, a database row identity, or free text. An unregistered key SHALL resolve to no reference (with a bounded diagnostic where a named entity carried one), never to a substituted reference. Two distinct entities MAY reference identical official image bytes; sharing a reference SHALL NOT share any mutable state.

#### Scenario: A valid provenance resolves a reference
- **WHEN** an entity carries provenance naming a registered preset key
- **THEN** resolution yields the `(preset, <key>)` reference and nothing else changes on the entity

#### Scenario: Display names never become keys
- **WHEN** an NPC's display name textually matches an authored content directory name but the entity carries no authored provenance
- **THEN** no official content reference resolves for it

#### Scenario: An unregistered key yields no reference
- **WHEN** provenance names a key absent from the owning registry
- **THEN** no reference resolves, one bounded diagnostic is emitted, and resolution degrades to the runtime chain

### Requirement: Preset-born characters resolve their template reference and keep their own gallery
A character created from a player preset SHALL resolve its preset official content reference from the existing `creation_preset_key` provenance while retaining its own runtime art subject and mutable `GalleryRecord`. Preset preview presentation SHALL resolve the same official reference without creating a character, a gallery record, or any game state. Two characters born from the same preset SHALL therefore be able to share official image bytes while independently selecting different images and geometry overrides, and either character's personal changes SHALL NOT affect the other character or the preset's authored source.

#### Scenario: Same preset, independent galleries
- **WHEN** two preset-born characters exist and each sets a different personal selection and geometry override
- **THEN** both resolve the same preset reference for official defaults, their gallery records and personal preferences are disjoint, and the mounted source is unchanged

#### Scenario: A preset preview resolves without side effects
- **WHEN** the creation flow previews a preset's artwork before activation
- **THEN** the preset reference resolves to official artwork, and a database before/after comparison shows no new character, gallery record, or stored file

#### Scenario: Missing preset provenance degrades silently to the runtime chain
- **WHEN** a character carries no `creation_preset_key`
- **THEN** no preset reference resolves and its portrait resolution proceeds through runtime artwork and fallbacks exactly as today

### Requirement: Authored NPCs carry a stable profile provenance established at creation
Every NPC instantiated from an authored NPC/profile identity — settlement service hosts, guild examiners, and blueprint-characterized occupants whose blueprint names a profile identity — SHALL have its authored profile key recorded as stable provenance in the same owning creation/import/spawn path that already establishes its other authored attributes, subject to the same transactional discipline (a rolled-back spawn/import leaves no provenance). Resolution SHALL bind the `npc` official reference to that provenance. The numeric `npc_tier_key` SHALL NOT select an NPC's official content reference: two NPCs sharing one numeric tier SHALL NOT thereby share a named character's image.

#### Scenario: A spawned host resolves its profile reference
- **WHEN** a settlement service host with an authored `host_profile_key` spawns and later presents
- **THEN** its npc official reference is `(npc, <profile key>)`, derived from the provenance written at spawn

#### Scenario: Tier equality never shares a named image
- **WHEN** two scene NPCs share one `npc_tier_key` but only one has authored profile provenance
- **THEN** only the provenance-bearing NPC resolves a named `npc` reference, and the other resolves no official reference

#### Scenario: Rolled-back spawn leaves no provenance
- **WHEN** a spawn or import transaction rolls back after provenance would have been written
- **THEN** no entity carries the new provenance attribute

### Requirement: Dynamically generated NPCs may only carry an explicit allowed reference
A dynamically generated NPC (no authored profile identity) SHALL resolve an official content reference only when an allowed authored channel explicitly attaches one to it; the engine SHALL NOT infer a reference from its display name, tier, quest role, or generator output text. Without an explicit reference it presents through its runtime portrait path and the existing fallback chain unchanged.

#### Scenario: A generated NPC without an explicit reference infers nothing
- **WHEN** a generated NPC with a display name identical to an authored content key presents
- **THEN** no official reference resolves and its presentation proceeds through its runtime chain

#### Scenario: An explicitly attached reference is honored
- **WHEN** an allowed authored channel attaches a validated official reference to a generated NPC
- **THEN** that reference resolves like any other provenance-derived reference

### Requirement: Monster species references await the separate species catalog and forbid tier substitution
Species-specific monster official artwork SHALL resolve only from a validated species/content reference. No such reference producer exists until the separate monster species catalog design lands; until that catalog's owner supplies it, monster subjects SHALL resolve official artwork through no path, presenting runtime artwork or the built-in monster silhouette as they do today, and every existing guarded seam SHALL remain intact. NO code path SHALL substitute a threat tier for a species reference, map an unknown species to a tier, or reuse one content reference's official image for another subject. When a species reference provider exists, the shared-by-species image behavior SHALL be independent of where or how many individuals spawn.

#### Scenario: Monsters resolve no official image before the catalog exists
- **WHEN** any registered threat-tier monster is asked for an official content reference while `monster/` content directories are populated in the official root
- **THEN** the resolver yields no reference for it — no tier-to-species or display-name-to-species mapping runs — and production code constructs no monster reference anywhere

#### Scenario: A threat tier never borrows a species image
- **WHEN** the official root contains `monster/<key>/` directories and a monster of a registered tier whose own key textually equals one of those directory names is asked for a reference
- **THEN** the resolver yields no reference, because no producer keyed by threat tier exists

#### Scenario: Synthetic species references resolve when supplied
- **WHEN** a test injects a species/content reference provider and asks the resolver for a monster carrying a validated species reference
- **THEN** the resolver answers with that monster's own reference — never a sibling content key's — leaving content existence and presentation to the resolution layer

### Requirement: Entity identity is a hash input only, never a manufactured portrait subject
For an entity without a named portrait subject, its stable runtime entity identity SHALL be usable only as the deterministic placeholder selector's hash input. The engine SHALL NOT install a `portrait_policy`, create a gallery record, or enqueue generation on such an entity in order to obtain that input, and the hash input SHALL NOT become an official content reference.

#### Scenario: Placeholder hashing creates no portrait state
- **WHEN** an entity with no named portrait subject resolves a fallback that hashes its runtime identity
- **THEN** the entity still carries no portrait policy, no gallery record exists, and no job was enqueued
