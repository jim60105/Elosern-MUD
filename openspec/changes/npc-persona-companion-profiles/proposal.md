## Why

A starting companion currently copies its partner player preset's persona wholesale (`PresetPersona.to_record()`) and appends the owner relationship. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §1, §5.1, §5.3, §6.1) requires companions to receive fully rewritten NPC personas from NPC-specific profiles, separately from the mechanical player-preset reference, while the player presets and existing player characters stay untouched. The four companion declarations are a small, self-contained source set whose content and producer can be delivered together in one workday.

## What Changes

- Author four companion profiles in `world/lore/npc_profiles/companions.py` (`companion_lidzia_rosenthal`, `companion_violet_altoria`, `companion_yuna_darknight`, `companion_yuka_darknight`), each with a complete compact card consistent with the partner preset's established identity but newly written for the NPC, and an offline `greeting` voice line (companions are free-form `LLMNPC`s with no scripted table).
- **BREAKING (pre-release, no compatibility layer):** `StartingCompanion` gains a required `npc_profile_key`; lore-side validation rejects an unresolved key, and the rules-side registry sweep rejects a profile whose card cannot fit the composed owner relationship within the card budget.
- The companion builder stops copying the preset persona: it composes the card from the NPC profile plus one factual owner line (`<owner>：<relationship>`) prepended to the profile's `social_connection`, and writes it through `initialize_npc_persona` with `companion` provenance (profile key, owner pk) inside its existing delete-compensation. Mechanical values (traits, skills, equipment, ages, portrait policy, `creation_preset_key`) still come from the partner preset.
- Player presets, `PresetPersona`, player activation persona, and existing player characters are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `starting-companions`: the declaration carries an NPC profile reference; the built companion's persona comes from that profile plus the factual owner relationship instead of the preset persona.

## Impact

- Code: `world/lore/player_presets/vocab.py` (`StartingCompanion`), `world/lore/player_presets/validation.py`, `world/lore/player_presets/data_story_cards.py` and `data_pack_cards.py` (four declarations), `world/rules/starting_companions.py` (sweep and builder), `world/lore/npc_profiles/companions.py` (content).
- Tests: `world/rules/tests/test_starting_companions.py` (existing, rules shard), `world/lore/tests/test_player_presets.py`, a new companion data-contract module under `world/lore/tests/`.
- Docs: `docs/gm/` preset authoring guidance if it documents `StartingCompanion` fields (checked by `tests.test_preset_authoring_docs_contract`).

## Batch:

depends-on: npc-persona-card-foundation

Code-conflict notes: owns `world/lore/npc_profiles/companions.py`, `world/lore/player_presets/*`, and `world/rules/starting_companions.py` alone in this batch. `npc-persona-roster-cutover` later reads the companion profile and owner rule to replace already-built companions, and `npc-persona-dialogue-consumption` routes the `greeting` line; neither edits these files. Shared append-only files: `tools/test_data_freeze.json`, `.github/evennia-shards.json` (only if a new rules test module is added), the observability catalog. Independent of all content slices.
