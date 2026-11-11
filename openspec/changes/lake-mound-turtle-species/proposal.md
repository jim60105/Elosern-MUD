# Proposal

## Why

`eastern_plains` is Grandia's farm heartland, with 1.34M valid wilderness cells and 19 inhabited settlements. Wave 1 (`eastern-plains-near-belts`) gave every settlement a hinterland zone and placed twelve remote road corridors, but the region holds only low-tier species, so the corridors and the remote ground carry no mid-tier animal and the region has no deep-wild belt or boss site. Wave 3 of the near-settlement programme gives it four species (one low, two mid, one high) before `eastern-plains-deep-placement`. This change delivers 湖丘巨龜 (`lake_mound_turtle`), a giant snapping turtle of the lakes of 東部大平原 (`eastern_plains`). Its role is high-tier armoured bruiser (single bite + area shell slam), its social structure solitary, and it moves as a slow walker and lake-bottom dweller. Its variants are 丘背型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `eastern_plains`, and author-private origin boundary, rationale and conjecture. Variants: `wide_mound_elder` (丘背型, high B, ordinary). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `lake_mound_bite` (碎顎咬合), `lake_mound_quake` (背甲震地), which reuse the shipped two-strike (single + area damage) composition signature (design D3).
- One narration row per skill. No new timed effect or modifier (design D4).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `eastern-plains-deep-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_earth.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: sluice-spear-heron-species

Species chain (strictly serial): `ore-nest-griffin-species` (last Wave 2 link) → `clod-ball-beetle-species` → `dust-mane-horse-species` → `sluice-spear-heron-species` → `lake-mound-turtle-species` → `flat-leap-goby-species` → `mast-wind-gull-species` → `breakwater-seal-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `eastern-plains-deep-placement` depends on `lake-mound-turtle-species`, and `southeast-coast-placement` depends on `breakwater-seal-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every open placement change (`north-deep-forest-placement`, `highland-road-belts`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement` and `southeast-coast-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
