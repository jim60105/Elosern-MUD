# Proposal: remove the baseline art-only visual species

## Batch:

Gallery window programme, stage 0 (design
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`, section
"Prerequisite"). First change of the programme.

- depends-on: none
- conflict: `world/art/tests/test_species_portrait_identity.py`,
  `web/webclient/presentation/tests/test_art_panel.py` are also touched by no
  other change in the programme; `world/art/service.py` is touched later by
  `scene-kind-gallery` and `scene-asset-migration` (different functions).

## Why

The visual-species registry merges the complete combat species with twelve
authored "baseline" rows reached only through `Monster.art_species_key`. No
non-test code writes that attribute (verified: the only references outside
tests are its declaration in `typeclasses/monsters.py` and the two readers in
`world/art/presenter.py` and `world/art/official_refs.py`), so no monster ever
uses those rows, yet startup still generates art for them and the gallery must
special-case them. The gallery window's sighting gate (D3) assumes every visual
species is a codex species; this change makes that true.

## What Changes

- The visual registry becomes exactly the projection of the combat species
  registry; `BASELINE_VISUAL_ROWS` and
  `MonsterVisualDeclaration.is_baseline_art_only` are removed.
- `Monster.art_species_key`, the presenter fallback that reads it and the
  `ART_SPECIES_PROVENANCE_ATTRIBUTE` arm of the official-reference resolver are
  removed. A monster without `species_key` resolves no species subject.
- The startup gallery prune also reclaims stored art of monster keys that are
  not registered visual species: their gallery records, gallery job records,
  classic asset records, and the files only those referenced. This removes the
  twelve keys' stored state and any retired-tier leftovers with one generic rule.
- Tests that borrowed `BASELINE_VISUAL_ROWS[0]` or `art_species_key` switch to
  synthetic species from `world/tests/synthetic_data`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-visual-identity`: the registry is the combat species projection
  alone; provenance is `species_key` alone; baseline scenarios removed.
- `species-portrait-identity`: the tier-built baseline scenario is replaced by
  the no-provenance rule.
- `art-gallery-generation`: the startup prune also reclaims stored art of
  unregistered monster keys.

## Impact

- Code: `world/lore/monster_visuals.py`, `typeclasses/monsters.py`,
  `world/art/presenter.py`, `world/art/official_refs.py`,
  `world/art/service.py` (`prune_gallery_orphans`), `world/art/gallery.py`
  (new sole-writer deletion function).
- Tests: `world/lore/tests/test_monster_visuals.py`,
  `world/art/tests/test_presenter.py`,
  `world/art/tests/test_species_portrait_identity.py`,
  `world/art/tests/test_official_refs.py`,
  `world/art/tests/test_gallery_seed.py`,
  `web/webclient/presentation/tests/test_art_panel.py`, and the prune tests
  beside `world/art/service.py`.
- Data: stored records and files of the twelve keys disappear at the next
  startup. Pre-release: no migration or alias is kept.
- Estimate: 7 hours (registry and attribute removal 1 h, six test modules
  rewritten to synthetic species 3 h, prune extension with tests 2 h, spec and
  gates 1 h).
