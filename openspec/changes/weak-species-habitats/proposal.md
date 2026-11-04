# Proposal

## Why

`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §4.1–§4.3 and §7.1 give each weak species only bounded authored habitat placement with a separately bound field activity: 泥膜史萊姆 births of one to three dispersing solitary individuals with passive contact; 膠掌小鬼 cohesive groups of two to four, hostile only inside a defended nest area; 蠟囊鼠 cohesive families of two to five, hostile only inside a defended cache area. After the three species changes, none of them is placed anywhere.

## What Changes

- Five new ecology zones, each one bounded 20×20 rectangle wholly inside its habitat region and at least 45 cells from every published location and harbor cell (planning probe, design.md D1): two damp-bank slime zones (`eastern_plains`, `western_hills_valleys`), one quarry/scrub goblin zone (`western_hills_valleys`), two field-margin/cache rat zones (`eastern_plains`, `western_hills_valleys`).
- One complete composition per zone (`mudbank_dweller` 1–3, `hanging_nest_forager` 2–4, `wax_cache_forager` 2–5), each pooled only by its own zone.
- Activity declarations: region-intersection grounds equal to each zone rectangle, a small defended sub-area for the goblin nest and each rat cache, solitary passive activity for the slime (dispersed into one-member groups at birth by `activity-group-formation`), cohesive `defended_area` activity for the goblin and rats.
- Density, cell capacity, wave budget and recovery timing satisfying the existing validators, with the composition maximum fitting one wave and one cell.
- Developer review entry recording the habitat choice rationale; no coordinate, density or count is copied into documentation or tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data executed by `regional-ecology`, `regional-population`, `monster-site-placement` and `monster-field-activity` (including the group-formation requirement added by `activity-group-formation`). Generic shipped-registry tests already validate every zone, composition and activity reference, habitat compatibility and bounds.

## Impact

Files: `world/lore/monster_placement.py` (`_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, regenerated `content/map-reference-context.json`. No test file changes.

Human-reviewed document: the new "Content expansion habitats" subsection of `docs/development/regional-monster-population.md` (whether each rectangle's published geography and scenario context supports the dossier: damp banks, remote scrub/quarry, field margins and abandoned grain facilities). High-tier variants stay outside every ordinary pool. Working canals, granaries and settlement-adjacent conflicts remain for explicit manual or quest placement and are not authored here.

## Batch:

depends-on: activity-group-formation
depends-on: mudfilm-slime-species
depends-on: wax-pouch-rat-species
depends-on: sticky-palm-goblin-species

Batch 5, parallel with `reservoir-warden-variant` (disjoint files).

Code conflicts:
- `abandoned-transfer-station-encounter` and `high-tier-boss-sites` append to the same four declaration tuples and to `docs/development/regional-monster-population.md`; they land after this change.
- `site-member-activity-bindings` changed `CompositionMember`/`MonsterSite` in the same module earlier (batch 2); this change uses only existing fields.
- `content/map-reference-context.json` conflicts mechanically with the parallel content change; rerun `uv run --locked python -m tools.map_reference_context` after rebase.
