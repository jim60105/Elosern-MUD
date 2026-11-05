# Proposal

## Why

`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §7.2 adds the one-shot manual encounter `abandoned_transfer_station_encounter` in an authored disused transport facility within `western_hills_valleys`: exactly two `hanging_nest_forager` (one cohesive pair gathering nest materials) and one `wax_cache_forager` (an independent stray gathering grain), co-located but not one group, all admitted by ordinary whole-cell engagement.

## What Changes

- One manual site `abandoned_transfer_station_encounter` (kind `encounter`, one-shot, capacity 3, no site activity override) at a remote western-hills cell chosen by the planning probe (design.md).
- One composition `abandoned_transfer_station_group` whose goblin row (exactly 2) binds a cohesive station activity hostile inside a nest sub-area and whose rat row (exactly 1) binds a solitary station activity hostile inside a cache sub-area, using the per-row bindings from `site-member-activity-bindings`.
- Station grounds and the two defended sub-areas as activity areas.
- A data-contract production smoke module that populates the shipped site and observes three independent identities, two movement groups, one ordinary session admitting all three, distinct targets, defeat credit once per individual and a cleared one-shot site that stays cleared across reload, map read and quest acceptance.
- Review entry and a retained note that future repeatable content declares its own lifecycle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. The site, row bindings, group formation, whole-cell engagement, one-shot lifecycle and identity-keyed defeat credit are all existing requirements (`monster-site-placement`, `monster-field-activity`, `field-combat-initiation`/`player-combat-session`, `monster-individual-construction`).

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`), `world/lore/monster_activity.py` (areas and activities), new `world/maps/tests/test_content_expansion_sites.py`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`, `docs/development/regional-monster-population.md`, regenerated `content/map-reference-context.json`.

No quest commission, reward system or material harvest (design §7.3). Human-reviewed document: the "Content expansion sites" subsection of `docs/development/regional-monster-population.md` (whether the chosen cell reads as a disused transport facility and whether the co-location reads as independent animals).

## Batch:

depends-on: site-member-activity-bindings
depends-on: weak-species-habitats
depends-on: wax-pouch-rat-species
depends-on: sticky-palm-goblin-species

Batch 6, parallel with `ember-bristle-boar-species` (disjoint files except the shard manifest and freeze ledger, where the two changes add entries to different shard and list positions; resolve any textual conflict by keeping both entries).

Code conflicts:
- `weak-species-habitats` (before) and `high-tier-boss-sites` (after) append to the same declaration tuples and review subsection; `high-tier-boss-sites` extends the smoke module created here.
- `content/map-reference-context.json` regenerated after rebase.
