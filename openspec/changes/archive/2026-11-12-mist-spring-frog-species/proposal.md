# Proposal

## Why

`central_mountains` covers about 0.38M cells of the continent's spine and has no species and no monster placement at all. Wave 2 of the near-settlement programme gives it five species (two low, two mid, one high) before its placement change. This change delivers 霧泉蛙 (`mist_spring_frog`), a small mountain frog of 中央山脈 (`central_mountains`). Its role is contact drainer (MP drain on hit), its social structure colony (cohesive 2-3), and it moves as a hopper and wet-rock climber. Its variants are 汲泉型、泉主型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `central_mountains`, and author-private origin boundary, rationale and conjecture. Variants: `seep_sipper` (汲泉型, low F, ordinary), `spring_keeper` (泉主型, low E, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `mist_tongue_sip` (霧舌汲取), which reuse the shipped contact drain composition signature (design D3).
- One narration row per skill. No new timed effect or modifier (design D4).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Batch approval: the fifth-batch approval note in `docs/lore/monster-creation-guidelines.md` and the bestiary header, which name all ten Wave 2 species once (design D6a). Later species changes do not edit either note.
- Regenerated `content/map-reference-context.json`.

No placement: `central-mountains-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_water.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/lore/monster-creation-guidelines.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: moss-crown-stag-species

Species chain (strictly serial): `moss-crown-stag-species` (last Wave 1 link) → `mist-spring-frog-species` → `warm-rock-salamander-species` → `bone-breaker-vulture-species` → `mist-lamp-moth-species` → `rime-scale-serpent-species` → `drum-wing-grouse-species` → `mud-dam-beaver-species` → `ore-vein-mole-species` → `cache-raider-wolverine-species` → `ore-nest-griffin-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `central-mountains-placement` depends on `rime-scale-serpent-species`, and `northwest-highland-placement` depends on `ore-nest-griffin-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every placement change (the five Wave 1 placement changes, `central-mountains-placement` and `northwest-highland-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
