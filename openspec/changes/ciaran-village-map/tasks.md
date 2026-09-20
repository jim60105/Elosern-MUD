Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. The map module

- [ ] 1.1 Add `world/maps/village_ciaran.py` with `MAPSTR`, `PROTOTYPES` and `XYMAP_DATA` for
  `zcoord="village_ciaran"`: a six-node connected tree with 隱密小徑 as the entrance, 村中廣場 as
  the sole `anchor_room` carrying `anchor_key="village_ciaran"`, 練刀場, and three further
  dwelling-approach exteriors. Include the wildcard `CostedXYZExit` link override the capital uses.
- [ ] 1.2 Write Traditional Chinese keys and descriptions that read as a concealed forest
  settlement — no wall, gate, guard or marketplace anywhere in the text.
- [ ] 1.3 Introduce a shared map assembly exporting both settlements' map data. `XYMAP_DATA_LIST`
  is defined in `world/maps/altoria_capital.py` and only imported by `world/maps/bootstrap.py:19`,
  so this is an assembly edit rather than an append to a bootstrap-native list. Repoint
  `bootstrap.py` at it and verify `sync_grid()` spawns both settlements' rooms with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.maps.tests`.

## 2. Geography registries

- [ ] 2.1 Add the `village_ciaran` row to `ANCHOR_PLACEMENT_REGISTRY` pointing at the plaza, and
  verify every entry's `zcoord` and `entrance_xy` match its settlement's spawned `AnchorRoom`.
- [ ] 2.2 Repoint `world/lore/wilderness_entry.py::_iter_map_extents` (line 180) at the shared map
  assembly. It carries its OWN deferred `from world.maps.altoria_capital import XYMAP_DATA_LIST`,
  separate from bootstrap's, and `validate_wilderness_entries()` runs from `sync_all()` at every
  startup — left as is, the village's gate raises `unknown z_map_key` and the whole lore load
  fails. Keep the import deferred: lore must not import `world.maps` at module scope.
- [ ] 2.3 Add the `village_ciaran` entry to `WILDERNESS_ENTRY_REGISTRY` with a footprint well clear
  of the capital's `(58,98)`–`(62,102)` and one gate returning to the entrance node. Verify
  `validate_wilderness_entries()` accepts the village's gate — this is the assertion that proves
  2.2 landed — and that footprints and gate identities are disjoint across both entries.
- [ ] 2.4 Add the `village_ciaran` row to `CITY_GATE_REGISTRY` with `exit_key` 「隱密小徑」 and its
  aliases, and verify no exit key or alias collides with the capital's row.

## 3. Two-settlement behavior

- [ ] 3.1 Verify the starting room gains exactly one forward exit per registry row and that no
  village room holds an exit back to it, with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap`.
- [ ] 3.2 Verify the same coordinate in each settlement resolves to a different room and that
  neither settlement's rooms appear in the other's shortest paths.
- [ ] 3.3 Verify a wilderness traveller standing on the village's approach cell and moving in the
  gate's return direction arrives at 隱密小徑.

## 4. Handoff

- [ ] 4.1 Run `uv run --locked python -m tools.test_data_lint check`, confirm any new test module is
  registered in `.github/evennia-shards.json`, and run
  `openspec validate ciaran-village-map --strict`.
