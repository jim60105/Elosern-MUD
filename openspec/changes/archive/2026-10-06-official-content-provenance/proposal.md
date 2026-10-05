## Batch:

- depends-on: official-artwork-catalog
- conflicts: none with `official-art-resolution-contracts` (which lands after this change and consumes these references); `world/art/gallery_fallback.py` docstring/provenance comments are shared with `builtin-silhouette-stage-fallback` (comment-only overlap; serialize this change first)
- external-prerequisite: species-specific monster content references require the separate monster species catalog design (not yet approved). This change ships the `monster/` layout kind and a validated-reference resolver only when a species reference exists; it invents no species keys, aliases, or threat-tier mappings.

## Why

Resolution against the official catalog needs to know *which* authored content an entity is: a preset-born character must resolve its template's reference through existing provenance while keeping its own mutable gallery, and NPCs need a stable authored profile reference instead of the numeric tier they currently record. The source design is §6. Monster species identity is a separate, unapproved catalog — this change states that boundary honestly rather than faking it.

## What Changes

- Define the official content reference as a typed, validated pair (content kind `monster|preset|npc` + registered content key) resolved from provenance — never from a display name, translated label, or runtime database row.
- Preset-born characters: resolve the `preset/<preset-key>` reference from the existing `creation_preset_key` provenance while retaining the character's own runtime gallery subject; preset previews resolve the same reference without creating a character or gallery record.
- NPCs: establish the stable authored NPC/profile provenance (`npc_profile_key`) in the owning creation/import/spawn paths (host profiles, guild examiners, blueprint-characterized occupants), and resolve the `npc/<npc-or-profile-key>` reference from it; two NPCs sharing a numeric `npc_tier_key` never share a named-character reference. A dynamically generated NPC may explicitly carry an allowed official reference or fall back to its runtime portrait — no display-name inference.
- Monsters: honest prerequisite — no producer of a species/content reference exists before the separate monster species catalog lands, so monster resolution continues to use runtime artwork or the built-in silhouette, and no code path may substitute another species' image by threat tier. The existing guarded seams stay untouched until the catalog's owner lands; design amendment 1 (shared-by-species, not by tier) is recorded as the standing rule.
- Entities without a named portrait subject: their stable runtime entity identity may be used only as the deterministic placeholder selector's hash input — no `portrait_policy`, gallery record, or generation enqueue is installed to obtain it.

## Capabilities

### New Capabilities

- `official-content-provenance`: the typed official content reference and the provenance rules that bind entities to it — preset provenance with gallery independence, authored NPC/profile provenance established at creation/import/spawn, dynamic-NPC explicit-reference-only rule, entity-identity-as-hash-input rule, and the monster species-catalog prerequisite with its anti-tier-substitution guarantee.

### Modified Capabilities

- None. (Provenance attributes follow the existing `creation_preset_key`/`npc_tier_key` establishment sites; binding them to official references is the new capability's first behavior, and no existing capability's requirements change.)

## Impact

- Code: `world/art/subjects.py` (reference type/predicates or a sibling module), preset resolution in `world/lore/player_presets.py` consumers, NPC spawn/import paths (`world/quests/scene_builder.py`, `world/imports/loader.py`, settlement host instantiation) writing the new `npc_profile_key` provenance alongside existing attributes, preset-preview resolution seam.
- No gameplay mechanics change; no portrait eligibility, age-bound, or gallery-ownership change; no species registry created.
