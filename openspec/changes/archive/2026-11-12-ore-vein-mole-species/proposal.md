# Proposal

## Why

`northwest_highland_forest` holds 0.65M valid wilderness cells, 18 inhabited settlements and one species, the mid-tier 霧鬃山貓, so Wave 1 deferred every hinterland zone there. Wave 2 of the near-settlement programme gives it five species (three low, one mid, one high) before its placement change. This change delivers 礦脈鼴 (`ore_vein_mole`), a mole of 西北高地森林 (`northwest_highland_forest`). Its role is hit-rider debuffer (accuracy), its social structure solitary, and it moves as a burrower. Its variants are 掘脈型、深脈型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `northwest_highland_forest`, and author-private origin boundary, rationale and conjecture. Variants: `vein_digger` (掘脈型, low F, ordinary), `deep_seam_mole` (深脈型, low E, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `grit_claw_scrape` (揚砂爪刨), which reuse the shipped enemy hit-rider composition signature (design D3).
- Rulebook rows: one timed effect, one combat modifier and two status-display rows, plus one narration row per skill and the one-test-per-rule case (design D4, D7).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `northwest-highland-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_earth.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/tests/test_combat_modifiers.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: mud-dam-beaver-species

Species chain (strictly serial): `moss-crown-stag-species` (last Wave 1 link) → `mist-spring-frog-species` → `warm-rock-salamander-species` → `bone-breaker-vulture-species` → `mist-lamp-moth-species` → `rime-scale-serpent-species` → `drum-wing-grouse-species` → `mud-dam-beaver-species` → `ore-vein-mole-species` → `cache-raider-wolverine-species` → `ore-nest-griffin-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `central-mountains-placement` depends on `rime-scale-serpent-species`, and `northwest-highland-placement` depends on `ore-nest-griffin-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every placement change (the five Wave 1 placement changes, `central-mountains-placement` and `northwest-highland-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
