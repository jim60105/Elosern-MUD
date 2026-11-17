# world/maps guide

This package owns room and instance lifecycle and the monster population of the
wilderness. It is a writer package: it applies its own state changes.

## The map world is authored YAML

Static maps are the YAML files under `content/maps/` (`continent.yaml`,
`locations.yaml`, `districts.yaml`, `road_network.yaml`, `settlements/*.yaml`,
`interiors/*.yaml`). There is no Python map table and no database copy to
edit. Read `.agents/skills/map-data-authoring/SKILL.md` before changing any of
them: it has the file formats, the verification commands and the scripts.

`runtime.py` is the one entry point that loads them. It reads the whole source
set, validates it, checks every join, and only then installs one immutable
`MapWorld`. Publication is all or nothing.

- Consumers read the published world through `runtime.current()` and the views
  in `published.py`, `map_data.py`, `geography.py`, `interiors.py`. A read with
  nothing published raises `MapWorldNotLoaded` or `SettlementNotLoaded`. That
  is intended: never add an implicit load or a fallback to a reader.
- Only a composition root (server startup, a tool, a test fixture) publishes.

## Generated files

Three committed files are derived from the YAML. A freshness check fails when
one is out of date. Regenerate in this order and commit the result:

| File | Regenerate with |
| --- | --- |
| `world/maps/data/district_partition.json` | `uv run --locked python -m tools.map_district_partition` |
| `world/maps/data/road_network.json` | `uv run --locked python -m tools.road_network` (after the partition and the elevation tiles are current) |
| `content/map-reference-context.json` | `uv run --locked python -m tools.map_reference_context` |

Never edit a generated file by hand. `uv run --locked python -m tools.settlement_spacing`
validates village and hamlet placement; it writes nothing.

## Find the owner

| You are changing | Modules |
| --- | --- |
| Loading and publishing the map world | `runtime.py`, `published.py`, `map_data.py`, `geography.py`, `interiors.py`, `static_references.py` |
| Creating rooms from the published world | `bootstrap.py` (`sync_grid()`: idempotent; a coordinate change moves the existing room, it never deletes and recreates it) |
| Instances (spawn, expiry, pins) | `instance.py` |
| Wilderness terrain, elevation, roads, exits | `wilderness_provider.py`, `elevation.py`, `road_network.py`, `wilderness_destination.py`, `wilderness_reachability.py` |
| Districts and area identity | `district_partition.py`, `area_identity.py` |
| Ordinary regional monster population | `regional_population.py` (the single writer), `population_units.py`, `population_geometry.py`, `population_forecast.py`, `wilderness_population.py` (read projection) |
| Authored monster sites (camps, nests, bosses) | `monster_sites.py` |
| When a population boundary happens | `population_lifecycle.py` (the one coordinator; the two owners above never decide timing) |
| Monster groups and journeys | `monster_activity.py` (sole writer of `wilderness.db.monster_activity`) |
| Limbo, room art | `limbo.py`, `room_art.py` |
| Operator repairs | `gm.py` |

Placement *data* (which monsters, where, how many) is not here. It is the
registry in `world/lore/monster_placement.py` and `world/lore/monster_activity.py`.
Those two files are several thousand lines each: search them for the key you
need instead of reading them whole.

## Tests

- A test that reads the map world publishes it first, in module or class setup:
  `world.tests.geography_fixture.publish_shipped_map_world()`.
- A test that needs real rooms materializes only the settlements it uses:
  `sync_test_settlements((map_id,))` from the same module. Put a class-wide
  convergence in `setUpTestData`.
- A test that authors its own room uses `world/tests/interior_fixture.py` or
  `world/tests/synthetic_grid_map.py`, not a shipped room.
- Requirements and tests here define logic, not data. Do not assert a specific
  settlement, coordinate, count or roster. A test that must name shipped
  content is a data-contract test: first docstring line
  `Data-contract test: <rationale>`, registered in `tools/test_data_freeze.json`.
- The persisted population and activity records are strict: a codec rejects an
  unknown or missing key. When you add a field, update the codec, every
  constructor of the record, and the tests that build one by hand.

## Mistakes that have happened here

- A suite passed only because an earlier module in the same shard had already
  published the map world. Publish in your own setup.
- A settlement test asserted the shipped roster, and every later data edit
  broke it. Derive the expectation from the authored documents or use a
  synthetic world.
- A settlement, gate or terrain edit was committed without regenerating the
  road network or the reference context, and CI preflight failed.
- A change decided population timing inside `regional_population.py` or
  `monster_sites.py`. Timing belongs to `population_lifecycle.py`.
