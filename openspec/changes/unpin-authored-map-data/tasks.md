# Tasks

Ground rules for every task:
- Edit ONLY the files a task names. Do NOT touch production code, `content/`, `docs/`, `tools/`, `.github/`, `openspec/specs/` or any other test file.
- Keep each `@covers_requirement(...)` ID exactly as it is today. Where a task adds a decorator, use the OLD ID it gives. New IDs are applied only after archive (see "Workflow follow-up").
- Never change the first docstring line of a `Data-contract test:` module.
- Run Evennia tests as ONE standalone command with no pipes, redirects or env prefixes, for example `uv run evennia test --keepdb --settings settings.py world.maps.tests.test_wilderness_geography_contract`. Without `--settings settings.py` the run fails with a misleading prototype KeyError. If the output is truncated, read the log artifact path it prints.
- In every code block below, keep the indentation exactly as shown (methods are indented 4 spaces inside their class).

## 1. Wilderness geography contract: remove capital/ford position pins

File: `world/maps/tests/test_wilderness_geography_contract.py` only.

- [ ] 1.1 In class `BorderRiverContractTests`, replace the whole method `test_fords_lie_on_the_river_with_the_principal_on_the_capital_line`, including its `@covers_requirement` line, with:
  ```python
      @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
      def test_border_fords_are_the_only_walkable_river_cells(self):
          fords = terrain().waterway_fords["border_river"]
          self.assertTrue(fords)
          self.assertEqual(len(set(fords)), len(fords))
          raster = rasterize_routes({"border_river": terrain().waterway_routes["border_river"]})
          for ford in fords:
              self.assertIn(ford, raster)
              self.assertTrue(is_valid_wilderness_cell(ford), ford)
          water = {cell for cell in raster if is_inland_water_cell(cell)}
          self.assertEqual(raster - water, set(fords))
  ```
  Check: `grep -n "capital_valhalla\|principal" world/maps/tests/test_wilderness_geography_contract.py` prints no line inside `BorderRiverContractTests` except the ones task 1.2 removes.
- [ ] 1.2 In `test_west_of_the_corridor_only_the_fords_cross_the_border`:
  - replace the comment block and the lines from `from world.lore.anchors import anchor_geography` through `self.assertLess(max(south[0], north[0]), source_x)` with the code below;
  - keep the decorator, the `def` line and everything from `for blocked, connected in (` to the end of the method unchanged.
  ```python
          # Cut the continent along the river's source column. West of the cut
          # the river is a complete barrier except at its declared fords; the
          # bank cells beside one ford stand for the two sides of the border.
          fords = frozenset(terrain().waterway_fords["border_river"])
          source_x = terrain().waterway_routes["border_river"][0][0]
          cut = frozenset((source_x, y) for y in range(wilderness_provider.WILDERNESS_MAX_Y + 1))
          ford_x, ford_y = terrain().waterway_fords["border_river"][0]
          south, north = (ford_x, ford_y - 1), (ford_x, ford_y + 1)
          self.assertTrue(is_valid_wilderness_cell(south), south)
          self.assertTrue(is_valid_wilderness_cell(north), north)
          self.assertLess(ford_x, source_x)
  ```
  Check: the method no longer contains `anchor_geography`, `capital_altoria` or `capital_valhalla`.
- [ ] 1.3 In class `ForestEdgeAndClaimContractTests`, delete the whole method `test_anchor_relationships_to_the_forest_edge`, including its decorator line. Check: `grep -c "test_anchor_relationships_to_the_forest_edge" world/maps/tests/test_wilderness_geography_contract.py` prints `0`.
- [ ] 1.4 Run `uv run evennia test --keepdb --settings settings.py world.maps.tests.test_wilderness_geography_contract`. Expected: `OK`, no failures. This is the first point where master's two failures are gone.

## 2. Wilderness geography contract: remove the remaining data pins

File: `world/maps/tests/test_wilderness_geography_contract.py` only. Requires group 1.

- [ ] 2.1 Replace lines 3–8 of the module docstring (every line after the first line and the blank line, up to the closing `"""`) with the text below. Line 1 (`Data-contract test: authored continental terrain, waterway and anchor-region data contract`) must stay byte-identical.
  ```text
  The shipped geography is checked through invariants derived from the authored
  data itself: classifier joins, walkability and connectivity of every authored
  site, ford and river-cell semantics, nominal-claim agreement and the political
  lines' derivation. No authored coordinate, count or area share is copied here,
  so moving a site, river or edge vertex needs no test edit unless it breaks an
  invariant. Mechanics stay in ``world/maps/tests/test_wilderness_provider.py``.
  ```
  Check: `sed -n 1p world/maps/tests/test_wilderness_geography_contract.py` still prints `"""Data-contract test: authored continental terrain, waterway and anchor-region data contract`.
- [ ] 2.2 Replace the body of `test_central_mountain_region_bends_with_the_authored_corridor` (keep its decorator and `def` line) with:
  ```python
          # Rows come from the authored stem itself; the probes sit one cell
          # outside the authored corridor half-width on both sides.
          half_width = terrain().mountain_corridor_half_width
          rows = [
              y
              for _, y in terrain().ridge_stem
              if y < forest_edge_row(ridge_center_x(terrain(), y))
          ]
          self.assertTrue(rows, "the stem must have rows south of the forest edge")
          for y in rows:
              centre = ridge_center_x(terrain(), y)
              with self.subTest(y=y):
                  self.assertEqual(region_for_coordinates(centre, y), "central_mountains")
                  self.assertNotEqual(
                      region_for_coordinates(centre - half_width - 1, y), "central_mountains"
                  )
                  self.assertNotEqual(
                      region_for_coordinates(centre + half_width + 1, y), "central_mountains"
                  )
  ```
- [ ] 2.3 Delete the whole method `test_settlement_derived_anchor_cells_resolve_to_altoria_territory`, including its decorator.
- [ ] 2.4 Replace the whole method `test_the_physical_ridge_is_a_pass_free_forked_barrier` with the code below. Keep both of its existing `@covers_requirement` decorators (the single-line one and the three-line parenthesised one) exactly as they are, and replace only the `def` line and the body.
  ```python
      def test_unexempted_stem_rows_and_arm_tips_are_closed_walls(self):
          # Derived from the authored stem and its declared pass rows: every
          # active stem row outside a pass is walled at its centre.
          stem = terrain().ridge_stem
          passes = terrain().ridge_passes
          for y in range(stem[0][1], stem[-1][1] + 1):
              if any(low <= y <= high for low, high in passes):
                  continue
              centre = (ridge_center_x(terrain(), y), y)
              self.assertTrue(is_closed_ridge_cell(centre), y)
              self.assertFalse(is_valid_wilderness_cell(centre), y)
          # The stem's crotch and both arm tips are closed cliff walls.
          self.assertTrue(is_closed_ridge_cell(stem[-1]))
          for crest in ("west", "east"):
              tip = terrain().ridge_branches[crest][-1]
              self.assertTrue(is_closed_ridge_cell(tip), crest)
              self.assertFalse(is_closed_ridge_cell((tip[0], tip[1] + 1)), crest)
  ```
- [ ] 2.5 Replace the body of `test_rivers_are_authored_water_with_declared_fords` (keep its decorator and `def` line) with:
  ```python
          # Every ford lies on its own river and is walkable land; every other
          # land cell of any river is impassable inland water.
          routes = terrain().waterway_routes
          all_fords = {ford for fords in terrain().waterway_fords.values() for ford in fords}
          for name, fords in terrain().waterway_fords.items():
              raster = rasterize_routes({name: routes[name]})
              for ford in fords:
                  self.assertIn(ford, raster, name)
                  self.assertFalse(is_inland_water_cell(ford), name)
                  self.assertTrue(is_land_cell(ford), name)
                  self.assertTrue(is_valid_wilderness_cell(ford), name)
          land_water = [
              cell for cell in rasterize_routes(routes) - all_fords if is_land_cell(cell)
          ]
          self.assertTrue(land_water)
          for cell in land_water:
              self.assertTrue(is_inland_water_cell(cell), cell)
              self.assertFalse(is_valid_wilderness_cell(cell), cell)
  ```
- [ ] 2.6 In `test_anchor_and_port_centres_are_land_side`, change the comment line `# seven unbuilt anchors.` to `# unbuilt anchors.`. Change nothing else in that method.
- [ ] 2.7 In `test_river_course_stays_in_the_authored_band_from_corridor_to_coast`:
  - replace the comment line `# One water cell per column, exactly the classifier's river row, every` and the line after it (`# row inside Y 1290..1410.`) with the single line `# One water cell per column, exactly the classifier's river row.`;
  - change no code.
- [ ] 2.8 In `test_classifier_and_claims_flip_across_the_river`, replace the line `for x in (200, 450, 830, 1150, 1300):` with the code below, and keep the four assertions inside the loop and everything after the loop unchanged.
  ```python
          route = terrain().waterway_routes["border_river"]
          source_x, mouth_x = route[0][0], route[-1][0]
          for x in range(mouth_x + 1, source_x, max(1, (source_x - mouth_x) // 6)):
  ```
- [ ] 2.9 Replace the whole method `test_forest_edge_meanders_near_y1920_over_a_fifth_of_the_land`, keeping its decorator line, with:
  ```python
      def test_forest_edge_spans_the_frame_and_starts_the_deep_forest(self):
          xs = [x for x, _ in terrain().forest_edge]
          self.assertEqual(xs, sorted(set(xs)))
          self.assertEqual((xs[0], xs[-1]), (0, wilderness_provider.WILDERNESS_MAX_X))
          for x in range(0, wilderness_provider.WILDERNESS_MAX_X + 1, 97):
              row = forest_edge_row(x)
              self.assertEqual(region_for_coordinates(x, row), "north_deep_forest", x)
              self.assertNotEqual(region_for_coordinates(x, row - 1), "north_deep_forest", x)
  ```
- [ ] 2.10 In `test_forest_around_the_inland_tips_stays_walkable`, delete the last three lines of the method: the comment `# Forest cells off the ridge stay walkable (no new movement block).` and the two `self.assertTrue(is_valid_wilderness_cell((900, 2350)))` / `((700, 1960)))` lines.
- [ ] 2.11 Replace the whole method `test_every_land_cell_has_one_nominal_nation_with_authored_shares`, keeping its decorator line, with:
  ```python
      def test_every_land_cell_has_one_nominal_nation_agreeing_with_its_region(self):
          from world.lore.nations import NATION_REGISTRY

          seen_by_region = {}
          for x, y in _land_sample():
              nation = nominal_nation_for_coordinates(x, y)
              self.assertIn(nation, NATION_REGISTRY, (x, y))
              region = region_for_coordinates(x, y)
              self.assertIn(
                  nation, regions()[region].nominal_nation_keys, (x, y)
              )
              seen_by_region.setdefault(region, set()).add(nation)
          for key, region in regions().items():
              self.assertEqual(seen_by_region[key], set(region.nominal_nation_keys), key)
              if region.nation_key is not None:
                  self.assertEqual(region.nominal_nation_keys, (region.nation_key,), key)
  ```
- [ ] 2.12 Delete the whole method `test_effective_rule_targets_are_unchanged`, including its decorator.
- [ ] 2.13 In `test_displayed_borders_derive_from_ridge_and_river_outside_the_forest`, replace the line `self.assertEqual(river[-1], (ridge_center_x(terrain(), 1410), 1410))` with the two lines below. Change nothing else.
  ```python
          source_row = terrain().waterway_routes["border_river"][0][1]
          self.assertEqual(river[-1], (ridge_center_x(terrain(), source_row), source_row))
  ```
- [ ] 2.14 Pin scan. Run `grep -nE "1920|0\.20|0\.43|0\.30|0\.27|1300|1520|1410|1290|\(900, |\(700, |capital_valhalla|village_eolas|village_ciaran|village_fionnen|dungeon_eternal_night" world/maps/tests/test_wilderness_geography_contract.py`. Expected: no output. Then run `uv run evennia test --keepdb --settings settings.py world.maps.tests.test_wilderness_geography_contract`. Expected: `OK` with `Ran 17 tests`. Master has 20; group 1 deletes 1 and this group deletes 2. `grep -c "    def test_" world/maps/tests/test_wilderness_geography_contract.py` must also print `17`.

## 3. Anchor kind vocabulary and national-settlement lore checks

File: `world/lore/tests/test_anchors.py` only. Independent of groups 1–2.

- [ ] 3.1 Replace the whole method `test_every_supported_kind_appears_without_a_fixed_roster_count` with:
  ```python
      @covers_requirement("lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons")
      def test_anchor_kinds_match_the_schema_location_kinds(self):
          from elosern_map_core.codec import document_from_data
          from elosern_map_core.schema import LOCATION_KINDS
          from world.maps import map_data
          from world.maps.geography import build_geography, current

          self.assertEqual({kind.value for kind in AnchorKind}, set(LOCATION_KINDS))
          shared_cell = next(iter(current().anchor_geography.values())).cell
          synthetic = {
              f"t_kind_{kind}": {
                  "kind": kind,
                  "display_name_zh": f"合成地點{index}",
                  "description": "A synthetic location of one supported kind.",
                  "cell": {"cell_x": shared_cell[0], "cell_y": shared_cell[1]},
                  "geographic_constraint": "synthetic",
                  "scene_archetype": None,
              }
              for index, kind in enumerate(LOCATION_KINDS)
          }
          data = dict(current().locations.data)
          data["locations"] = {**data["locations"], **synthetic}
          snapshot = build_geography(
              current().continent,
              document_from_data("content/maps/locations.yaml", data),
              map_data.current(),
              fingerprints=dict(current().fingerprints),
          )
          for key, declaration in synthetic.items():
              with self.subTest(kind=declaration["kind"]):
                  self.assertEqual(snapshot.anchors[key].kind, AnchorKind(declaration["kind"]))
  ```
- [ ] 3.2 Replace the whole method `test_national_settlements_carry_nation_and_population` with:
  ```python
      @covers_requirement("lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons")
      def test_national_settlements_carry_nation_and_population(self):
          from world.lore.nations import NATION_REGISTRY

          settlement_kinds = {AnchorKind.CITY, AnchorKind.TOWN, AnchorKind.PORT}
          for key, anchor in anchors().items():
              if anchor.kind not in settlement_kinds:
                  continue
              with self.subTest(anchor=key):
                  self.assertIn(anchor.nation_key, NATION_REGISTRY)
                  self.assertIsNone(anchor.floors)
                  self.assertIsInstance(anchor.population, int)
                  self.assertGreater(anchor.population, 0)
  ```
- [ ] 3.3 Run `uv run evennia test --keepdb --settings settings.py world.lore.tests.test_anchors`. Expected: `OK`. Then run `grep -n "assertLess\|capitals\[" world/lore/tests/test_anchors.py`. Expected: no output.

## 4. World-map place classification

File: `web/webclient/presentation/tests/test_world_map.py` only. Independent of groups 1–3.

- [ ] 4.1 Replace the whole method `test_anchor_classification_keeps_villages_and_dungeons_visit_only`, which currently has no decorator, with:
  ```python
      @covers_requirement("webclient-world-map::world-scope-reveals-only-common-geography-and-permitted-district-knowledge")
      def test_anchor_classification_keeps_villages_and_dungeons_visit_only(self):
          from dataclasses import replace
          from types import MappingProxyType

          from world.lore.anchors import AnchorKind
          from world.maps import geography

          expected={
              AnchorKind.CAPITAL:("capital",False),
              AnchorKind.CITY:("settlement",False),
              AnchorKind.TOWN:("settlement",False),
              AnchorKind.PORT:("settlement",False),
              AnchorKind.ELVEN_VILLAGE:("hidden",True),
              AnchorKind.DUNGEON:("hidden",True),
          }
          self.assertEqual(set(expected),set(AnchorKind))
          anchors={
              f"t_{kind.value}":NS(kind=kind,display_name_zh=f"T_PLACE_{kind.value.upper()}")
              for kind in expected
          }
          geography_views={
              key:NS(anchor_key=key,cell=(100+i,200)) for i,key in enumerate(anchors)
          }
          harbours={"t_harbour":NS(key="t_harbour",cell=(90,200),display_name="T_PLACE_HARBOUR")}

          publish_shipped_geography()
          previous = geography.current()
          publish_geography(
              replace(
                  previous,
                  anchors=MappingProxyType(anchors),
                  anchor_geography=MappingProxyType(geography_views),
                  harbor_sites=MappingProxyType(harbours),
              )
          )
          self.addCleanup(publish_geography, previous)
          with patch("world.lore.anchor_placement.ANCHOR_PLACEMENT_REGISTRY",{}), \
               patch("world.maps.district_partition.district_at",return_value=SECRET):
              records=panel.geometry._place_geometry("uncached-probe")
          rows={row["id"]:(row["kind"],hidden) for _,row,hidden,_ in records}
          for kind,outcome in expected.items():
              self.assertEqual(rows[f"t_{kind.value}"],outcome,kind)
          self.assertEqual(rows["t_harbour"],("harbour",False))
  ```
  The method stays at its current position inside class `WorldMapPrivacyTests`.
- [ ] 4.2 Run `uv run evennia test --keepdb --settings settings.py web.webclient.presentation.tests.test_world_map`. Expected: `OK`.

## 5. Integration gates

Requires groups 1–4.

- [ ] 5.1 Run `uv run --locked python -m tools.spec_traceability check`. Expected: `0 uncovered, 0 errors`. The requirement count is unchanged from master: 2677, because the main specs are not yet synced.
- [ ] 5.2 Run `uv run --locked python -m tools.test_data_lint check`. Expected: `violations=0`.
- [ ] 5.3 Run `uv run --locked python -m tools.contract_gate`. Expected: exit status 0.
- [ ] 5.4 Run `openspec validate unpin-authored-map-data --strict`. Expected: `Change 'unpin-authored-map-data' is valid`.
- [ ] 5.5 Run `git diff --stat master...HEAD`. Expected: only these files change: `world/maps/tests/test_wilderness_geography_contract.py`, `world/lore/tests/test_anchors.py`, `web/webclient/presentation/tests/test_world_map.py`, and this change's `tasks.md` checkboxes.

## Workflow follow-up

These steps run AFTER the archive syncs this delta into `openspec/specs/`. Until then the new IDs are unknown to `tools.spec_traceability`.

- Re-anchor the four re-identified requirement IDs with these exact literal replacements:
  - In `world/maps/tests/test_wilderness_geography_contract.py` and `world/maps/tests/test_wilderness_provider.py`, replace `wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map` with `wilderness-terrain::the-coordinate-classifier-is-a-pure-deterministic-function-over-the-whole-bounded-map`.
  - In `world/maps/tests/test_wilderness_geography_contract.py`, replace `wilderness-terrain::terrain-and-political-control-follow-authored-geography` with `wilderness-terrain::terrain-and-political-control-derive-from-authored-geography`.
  - In `world/lore/tests/test_anchors.py`, replace `lore-registries::anchor-registry-covers-capitals-elven-villages-and-known-dungeons` with `lore-registries::anchor-registry-composes-every-declared-location-kind`.
  - In `world/lore/tests/test_anchors.py`, `world/lore/tests/test_anchor_placement.py` and `world/lore/tests/test_wilderness_regions.py`, replace `continental-geography::the-known-continent-has-frozen-geographic-declarations` with `continental-geography::known-continent-geographic-declarations-are-frozen`. The ID may be split across lines inside the decorator's parentheses; replace the full string literal.
- Confirm the new IDs exist: `uv run --locked python -m tools.spec_traceability list` contains all four new IDs and none of the four old ones.
- Then `git grep -n "region-for-coordinates-is-a-pure\|terrain-and-political-control-follow\|anchor-registry-covers-capitals\|the-known-continent-has-frozen" -- '*.py'` prints nothing, and `uv run --locked python -m tools.spec_traceability check` reports 0 uncovered and 0 errors.
