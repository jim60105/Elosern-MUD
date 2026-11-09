# Proposal: lore-species-research

## Batch: handbook-codex-titles (change 2 of 4)

- depends-on: none
- conflict: `lore-codex-schema-v2` depends on this change. It reads `lore_species_defeated` through this change's `list_species_defeated` reader, relies on the re-pointed monster category, and edits the same `world/rules/lore_knowledge.py`. It must land after this change.
- conflict: none with `handbook-titles-tab` (client-only; disjoint files).

## Why

The approved design `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` (D5, D6, §4.1) turns the codex's 魔物 category into a species bestiary with two research stages. Today `CODE_CATEGORIES["monster"]` resolves `MONSTER_TIER_REGISTRY`, so a codex "monster" is a threat tier, and the only monster reveal is the tier reveal planned by `world/quests/planner.py` on a defeat. Nothing records that a species was seen, and nothing distinguishes a seen species from a defeated one.

## What Changes

- `CODE_CATEGORIES["monster"]` resolves `world.lore.monster_species.MONSTER_SPECIES_REGISTRY`, with card fields `display_name_zh` and `published_appearance_zh`.
- New append-only attribute `lore_species_defeated` (a set of species keys), written only by `world/rules/lore_knowledge.py`.
- New writers `record_species_sighting(player, species_key)` and `record_species_defeat(player, species_key)`. They are idempotent and reject an unknown species with `LoreKeyError`. A defeat also records the sighting. The writers schedule the existing `lore_codex` push only when a record changed. New best-effort post-commit schedulers wrap them, and a pure reader `list_species_defeated` is added.
- Sighting hook: a helper in `world/rules/combat_initiation.py`, called from the shared hostile-session creation body in `world/rules/combat_session/lifecycle.py`, records each hostile individual's species once per new session.
- Defeat hook: `world/rules/combat_session/rounds.py::_record_round_defeats` records the species of every enemy monster whose HP crossed to zero in a committed round. It reads the same per-round HP crossing it already computes, before the mapped-wilderness early return. Guild-examination sessions record nothing.
- **BREAKING (pre-release):** the tier reveal is removed (`world/quests/planner.py::_make_defeat_lore_apply` and its effect block). Stored `monster:<tier>` records no longer resolve. The tolerant presentation read omits them, and the strict writer rejects a record that still holds one. No migration is provided (no released users).

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `lore-knowledge`: the category mapping (monster becomes species); a new two-stage species research requirement; "Defeating a monster reveals its tier" is removed and replaced by a new requirement for combat recording species sightings and defeats; the offline-discoverability scenario now names a species instead of a tier.

## Impact

- Server only: `world/rules/lore_knowledge.py`, `world/rules/combat_initiation.py`, `world/rules/combat_session/lifecycle.py`, `world/rules/combat_session/rounds.py`, `world/quests/planner.py`.
- Tests: `world/rules/tests/test_lore_knowledge.py`, `world/rules/tests/test_lore_deterministic_reveals.py`, a new `world/rules/tests/test_lore_species_research.py` (registered in `.github/evennia-shards.json`), and `web/webclient/presentation/tests/test_lore_codex_panel.py` (its monster fixtures move from tier to species).
- `lore_codex` stays at schema v1 in this change. The v1 drawer shows a species card under 魔物 until `handbook-codex-tab` replaces the drawer. The client display-vocabulary contract requires a readable name for every card field, so `web/webclient-app/lib/codex_field_label.js` gains one label entry (`published_appearance_zh`).
- No other client change, and no protocol, command or docs change. The `lore` command reads through the same reader and card renderer.
- Human-reviewed: none. Every requirement in this change is mechanical.
