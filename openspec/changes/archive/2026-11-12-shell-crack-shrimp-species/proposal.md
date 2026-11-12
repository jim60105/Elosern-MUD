# Proposal

## Why

`southwest_coast` is Altoria's craft shore: small harbours with finely built wooden ships, shipwright workshops, sea cliffs, fishing villages, salt pans and merchant ships carrying fine craft goods, plus the inland ferry towns on its rivers. Its only species is the shore crab 潮燈蟹, so every zone there repeats the same crab compositions, and Wave 1 deferred the hinterland of the three inland settlements because no shore species fits dry ground. Wave 4 of the near-settlement programme gives it five species (two low, two mid, one high) before `southwest-coast-placement`. This change delivers 碎殼蝦 (`shell_crack_shrimp`), a mantis shrimp of harbour shallows of 西南海岸 (`southwest_coast`). Its role is hit-rider bruiser (defense), its social structure solitary burrower, and it moves as a burrower and darting swimmer-crawler. Its variants are 穴擊型、深穴型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `southwest_coast`, and author-private origin boundary, rationale and conjecture. Variants: `reef_burrow_striker` (穴擊型, mid D, ordinary), `seawall_den_holder` (深穴型, mid C, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `club_limb_strike` (錘肢彈擊), which reuse the shipped enemy hit-rider composition signature (design D3).
- Rulebook rows: one timed effect, one combat modifier and two status-display rows, plus one narration row per skill and the one-test-per-rule case (design D4, D7).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `southwest-coast-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_martial.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/tests/test_combat_modifiers.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: stiff-arm-starfish-species

Species chain (strictly serial): `breakwater-seal-species` (last Wave 3 link) → `salt-column-ant-species` → `stiff-arm-starfish-species` → `shell-crack-shrimp-species` → `salt-snort-iguana-species` → `wreck-arm-octopus-species` → `shaft-leap-cricket-species` → `pit-sand-antlion-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `southwest-coast-placement` depends on `wreck-arm-octopus-species`, and `western-hills-deep-placement` depends on `pit-sand-antlion-species`.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every open placement change (`north-deep-forest-placement`, `central-mountains-placement`, `northwest-highland-placement`, `eastern-plains-deep-placement`, `southeast-coast-placement`, `southwest-coast-placement` and `western-hills-deep-placement`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
