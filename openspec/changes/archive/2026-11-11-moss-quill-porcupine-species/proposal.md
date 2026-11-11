# Proposal

## Why

`north_deep_forest` holds 1.00M valid wilderness cells and no species at all. Wave 1 of the near-settlement programme gives it six species (three low, two mid, one high) before its placement change. This change delivers 苔棘豪豬 (`moss_quill_porcupine`), a porcupine of the north deep forest. Its role is self-guard striker (defense), its social structure solitary, and it moves as a ground walker. Its variants are 啃皮型、守洞型.

## What Changes

- Registry rows in `world/lore/monster_species.py`: one `MonsterSpecies` with zh-TW published description, appearance and ecology, habitat `north_deep_forest`, and author-private origin boundary, rationale and conjecture. Variants: `quill_forager` (啃皮型, low F, ordinary), `den_sentry` (守洞型, low E, stronger). Each carries a complete literal profile inside its tier band (design D1, D2).
- Skill rows in `world/skills/registry/data_monster_abilities.py`: `quill_brace_ram` (固棘倒撞), which reuse the shipped self-guard strike composition signature (design D3).
- Rulebook rows: one timed effect, one combat modifier and two status-display rows, plus one narration row per skill and the one-test-per-rule case (design D4, D7).
- AI: legacy binding to an existing archetype, with the activation evidence re-fingerprinted only if the tuning fingerprint moves (design D5).
- Documentation: bestiary overview row, keyed current section and editorial-ledger entry; a developer review section in `docs/development/monster-content-expansion.md` (design D6, D8).
- Regenerated `content/map-reference-context.json`.

No placement: `north-deep-forest-placement` places the species. No new composition signature, effect prefix or decision mode, so no representative smoke module is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is content data executed by the existing `monster-species-registry`, `monster-individual-construction`, `monster-resource-abilities`, `monster-behaviour-profile` and `monster-ai-rollout` contracts. Shipped-registry, kit-contract, narration-coverage, bestiary-index and composition-group tests already cover every new row. No test compares prose, profile numbers or magnitudes.

## Impact

Files: `world/lore/monster_species.py`, `world/skills/registry/data_monster_abilities.py`, `world/skills/narration/data_earth.py`, `world/rules/rulebook/buffs.yaml`, `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/status_display.yaml`, `world/rules/tests/test_combat_modifiers.py`, `docs/lore/bestiary.md`, `docs/development/bestiary-editorial-review.md`, `docs/development/monster-content-expansion.md`, `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` (only if the fingerprint moves), and the regenerated `content/map-reference-context.json`.

Human-reviewed documents: `docs/development/bestiary-editorial-review.md` (affirmative phrasing, and consistency of ecology and abilities in the public prose) and `docs/development/monster-content-expansion.md` (profile relations, role and decision-mode rationale). The zh-TW prose is written verbatim in design.md so the worker transcribes it. Prose quality is judged in those review documents, never by a test.

## Batch:

depends-on: spore-cap-mushroom-species

Species chain (strictly serial): `spore-cap-mushroom-species` → `moss-quill-porcupine-species` → `hollow-tree-bat-species` → `hush-wing-owl-species` → `vine-net-spider-species` → `moss-crown-stag-species`. Every link appends to the same registry, skill, narration, rulebook, bestiary, ledger and review files and may move the AI tuning fingerprint. `north-deep-forest-placement` depends on the last link.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with the placement changes (`eastern-plains-near-belts`, `western-hills-near-belts`, `coastal-near-belts`, `highland-road-belts`). Rerun `uv run --locked python -m tools.map_reference_context` after rebase. No other file is shared with them.
