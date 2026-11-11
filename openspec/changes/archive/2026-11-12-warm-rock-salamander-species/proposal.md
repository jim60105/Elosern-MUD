# Proposal

## Why

`central_mountains` covers about 0.38M cells of the continent's spine and has no species and no monster placement at all. Wave 2 of the near-settlement programme gives it five species (two low, two mid, one high) before its placement change. This change delivers 暖岩蠑螈 (`warm_rock_salamander`), a fire salamander (folklore amphibian) of 中央山脈 (`central_mountains`). Its role is self-buff striker (physical attack), its social structure solitary, and it moves as a crevice crawler. Its variants are 曬岩型、熱縫型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `central_mountains`, and author-private origin boundary, rationale and conjecture. Variants: `ledge_basker` (曬岩型, low F, ordinary), `vent_crack_dweller` (熱縫型, low E, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `ember_skin_bite` (燃斑咬擊), which reuse the shipped self-guard strike composition signature (design D3).
- Rulebook rows: one timed effect, one combat modifier and two status-display rows, plus one narration row per skill and the one-test-per-rule case (design D4, D7).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `central-mountains-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_fire.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/tests/test_combat_modifiers.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: mist-spring-frog-species

Species chain (strictly serial): `moss-crown-stag-species` (last Wave 1 link) → `mist-spring-frog-species` → `warm-rock-salamander-species` → `bone-breaker-vulture-species` → `mist-lamp-moth-species` → `rime-scale-serpent-species` → `drum-wing-grouse-species` → `mud-dam-beaver-species` → `ore-vein-mole-species` → `cache-raider-wolverine-species` → `ore-nest-griffin-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `central-mountains-placement` depends on `rime-scale-serpent-species`, and `northwest-highland-placement` depends on `ore-nest-griffin-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every placement change (the five Wave 1 placement changes, `central-mountains-placement` and `northwest-highland-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
