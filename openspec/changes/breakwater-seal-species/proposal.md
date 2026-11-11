# Proposal

## Why

`southeast_coast` is Grandia's trading shore, with 0.26M valid wilderness cells and three ports. Its only species are the shore crab 潮燈蟹 and the estuary crocodile 吞潮鱷, so every Wave 1 zone there repeats the same crab and crocodile compositions. Wave 3 of the near-settlement programme gives it three species (two low, one mid) before `southeast-coast-placement`. This change delivers 臥堤海豹 (`breakwater_seal`), a harbour seal hauling out on breakwaters of 東南海岸 (`southeast_coast`). Its role is hit-rider bruiser (agility), its social structure haul-out colony (cohesive 1-2), and it moves as a swimmer and belly-slider on wet stone. Its variants are 曬堤型、霸灘型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `southeast_coast`, and author-private origin boundary, rationale and conjecture. Variants: `pier_basker` (曬堤型, mid D, ordinary), `haulout_bull` (霸灘型, mid C, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `flipper_slide_slam` (滑身壓撞), which reuse the shipped enemy hit-rider composition signature (design D3).
- Rulebook rows: one timed effect, one combat modifier and two status-display rows, plus one narration row per skill and the one-test-per-rule case (design D4, D7).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `southeast-coast-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_martial.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/tests/test_combat_modifiers.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: mast-wind-gull-species

Species chain (strictly serial): `ore-nest-griffin-species` (last Wave 2 link) → `clod-ball-beetle-species` → `dust-mane-horse-species` → `sluice-spear-heron-species` → `lake-mound-turtle-species` → `flat-leap-goby-species` → `mast-wind-gull-species` → `breakwater-seal-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `eastern-plains-deep-placement` depends on `lake-mound-turtle-species`, and `southeast-coast-placement` depends on `breakwater-seal-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every open placement change (`north-deep-forest-placement`, `highland-road-belts`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement` and `southeast-coast-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
