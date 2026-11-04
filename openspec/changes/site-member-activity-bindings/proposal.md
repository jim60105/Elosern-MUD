# Proposal

## Why

The content-expansion design (§7.2) places the manual encounter `abandoned_transfer_station_encounter`: two 膠掌小鬼 that move as one cohesive pair and one 蠟囊鼠 that stays independent, all co-located in one authored facility. A composition today has exactly one activity binding and a site always applies one required `activity_key` override to every member, so one manual composition cannot hold a cohesive pair beside an independent individual. The design (§3, §4.4, §4.5) also names the designated boss individuals 「閉灣者」 and 「赤背」 as display facts; the site owner constructs every member under its variant display name, so a designated individual cannot carry its local name.

## What Changes

- `CompositionMember` gains an optional per-row `activity_key`. A composition row without one keeps the composition's binding.
- `MonsterSite.activity_key` becomes optional. When a site declares an override, every member uses it (current behaviour, unchanged for all shipped sites). When a site declares none, each row resolves its own binding, else the composition binding. Zone births resolve row binding, else composition binding.
- One pure resolver returns the binding of every row; zone waves, site population and the forecast pass its output to the `movement_units` helper introduced by `activity-group-formation`, so a cohesive row pair and a solitary row form separate groups.
- `MonsterSite` gains optional `individual_label_zh`. Publication accepts it only for a site whose every legal composition outcome is exactly one individual; the site owner passes it as the constructed object's display key. Identity, ownership, quest binding and rewards remain species/variant/site keys.
- Shipped declarations are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-site-placement`: add requirements for effective row bindings with site-override precedence, and for the designated single-individual display label.

## Impact

Code: `world/lore/monster_placement.py` (`CompositionMember.activity_key`, nullable `MonsterSite.activity_key`, `MonsterSite.individual_label_zh`, resolver `composition_row_bindings`, validation), `world/maps/regional_population.py` (wave commit uses the resolver), `world/maps/monster_sites.py` (`_populate` uses the resolver and label), `world/maps/population_forecast.py` (site/zone projection uses the resolver; `ProjectedSite.activity_key` becomes optional). Tests: `world/lore/tests/test_monster_placement.py`, `world/maps/tests/test_monster_sites.py`, `world/maps/tests/test_regional_population.py`, `world/rules/tests/test_field_contact_boundaries.py`. Docs: `docs/development/monster-field-behaviour.md`. Regenerated: `content/map-reference-context.json`.

Human review: none beyond code review; the labels' wording belongs to the content changes that author them. Pre-release: no migration.

## Batch:

depends-on: activity-group-formation

Batch 2, parallel with `mudfilm-slime-species` (disjoint files).

Code conflicts:
- `activity-group-formation` owns the formation helper and the writers' grouping code edited here; land after it.
- `weak-species-habitats`, `abandoned-transfer-station-encounter` and `high-tier-boss-sites` append declarations to `world/lore/monster_placement.py` and `world/lore/monster_activity.py` and use these fields; they land later.
- `content/map-reference-context.json` conflicts mechanically with any parallel lore/rules change; rerun `uv run --locked python -m tools.map_reference_context` after rebase.
