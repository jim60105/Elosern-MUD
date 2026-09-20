## 1. Verify the geometry before writing anything

- [x] 1.1 Confirm `(63, 100)` is inside the wilderness provider rectangle (`_in_provider_rect`)
  and outside every registered footprint. `validate_wilderness_entries()` runs from
  `sync_all()` at every startup and a bad cell fails the whole lore load, not just the gate —
  so this is checked first, not discovered last.
- [x] 1.2 Confirm the new `MAPSTR` parses to exactly the twenty-one coordinates and twenty-six
  links in `design.md`, with both diagonals present, using
  `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()`.

## 2. The map

- [x] 2.1 Replace `MAPSTR` in `world/maps/altoria_capital.py` with the design's layout.
- [x] 2.2 Write the twenty-one prototypes. `(3,3)` is the `anchor_room` with
  `anchor_key="capital_altoria"`; the other twenty are `grid_room`. Keep the wildcard
  `CostedXYZExit` override exactly as it is — it already covers diagonals.
- [x] 2.3 Author each room's description so the three terraces read as terraces: the lower city
  as the oldest and most crowded, the market belt as the cleared line of a fallen wall, the
  upper city as the ground that wanted height. 舊城牆遺跡 and 聖階 carry the explanation of the
  shape and deserve the most care. Descriptions are English, matching every existing room.

## 3. The three registries

- [x] 3.1 `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].entrance_xy` → `(3, 3)`.
- [x] 3.2 `CITY_GATE_REGISTRY["capital_altoria"].gate_xyz` → `(3, 0, "capital_altoria")`. The
  exit key 「南門」 and its aliases are unchanged.
- [x] 3.3 `WILDERNESS_ENTRY_REGISTRY["capital_altoria"]` gates → `n` at `(3, 0)` and `w` at
  `(6, 3)`. The mask and origin are unchanged; only the gates move.
- [x] 3.4 Confirm by grep that these three rows plus the five `exterior_xy` values are the
  complete set of production references to a capital coordinate, and record what the grep
  covered. Test assertions are handled in task 5.
  Record: grepped `world/` and `web/` (non-test) for the literal coordinate/`capital_altoria`
  prototypes and for `NORTH_GATE_XYZ`/`SOUTH_GATE_XYZ` imports. Production references are the
  three registry rows (`world/lore/anchor_placement.py`, `world/maps/city_gates.py`,
  `world/lore/wilderness_entry.py`) plus the five `exterior_xy` values in
  `world/lore/settlements/places_altoria.py`. `world/maps/wilderness_population.py` derives
  `CAPITAL_ENTRY_XY` from the `w` gate rather than authoring a coordinate. The authored
  constants in `world/maps/bootstrap.py` were deleted; every consumer resolves coordinates
  through the live registries.

## 4. Re-point the landed five

- [x] 4.1 In `places_altoria.py` set the five `exterior_xy` values per the design table and
  update the trailing comments, which currently name the deleted bootstrap constants.
- [x] 4.2 Change nothing else in that file. The diff must be five coordinates and their
  comments — any other line is out of scope. The terrace split is `altoria-place-slices`.
- [x] 4.3 Give the tailor a doorway name distinct from the forge's, since they now share
  工匠巷. There is no guard for this yet — `altoria-place-slices` adds it — so check it by
  reading.

## 5. Coverage and the lore document

- [x] 5.1 Update the map, anchor, gate and wilderness assertions to the new coordinates and
  counts. Replace the tree assertion with the cycle-count assertion — that the graph is
  connected, has twenty-six edges over twenty-one nodes, and that some pair of rooms has two
  distinct routes.
- [x] 5.2 Cover that one exterior carrying two interiors yields two doorways on it and one 外
  exit from each interior, over the shipped craft alley.
- [x] 5.3 Assert the five landed places' identities, hosts and resolved offers are unchanged —
  the neutrality gate for this change. Only their exteriors moved.
- [x] 5.4 Rewrite `docs/lore/settlement-locations.md` line 7, which calls the capital map an
  unbuilt test skeleton, and the first bullet of 未來擴充方向 at line 500, which asks for this
  rebuild. Both are now done and must stop telling the next author to do them.
- [x] 5.5 Run the maps, lore and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
  Record: all green on feat/altoria-capital-replan — maps (test_bootstrap 37;
  altoria_capital + service_interiors + limbo_room 38; walkthrough/movement-cost/
  city-and-movement roundtrips; wilderness destination/provider/population),
  rules (party-follow + map-knowledge + movement-settlement 52), lore
  (test_sync + anchors + wilderness_regions + guild + settlements +
  anchor_placement), guild-economy-sync 38 (synthetic place-row exterior
  retargeted (4,2)→(4,1), a vacant node on the replanned map), web local_map 95,
  exploration-panel/affordances/node-ids 68, exploration-actions 80.
  `tools.spec_traceability check`: 1633/1636 covered — the 3 uncovered
  place-attendant-hosts requirements are the pre-existing master baseline
  (covered via the web_browser_freeze channel, identical on master).
