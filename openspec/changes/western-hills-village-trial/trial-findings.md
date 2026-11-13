# Trial findings: western-hills village and hamlet placement

Facts from the wave-3 trial of `docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md`
in region `western_hills_valleys`, cells x 1000 to 1340 and y 501 to 950.
This change placed 4 villages and 9 hamlets. The file records what the trial
showed; it changes no threshold, node count or naming rule. A finding that
needs a rule change is reported to the user, who revises the tiers design
before `altoria-hills-village-placement` starts.

## 1. Spacing values

All three values held, with no exemption.

- Fifteen kilometres: the closest settlement pair is 23.2 km (hamlet_stone_wall
  to town_scarp) and the closest hamlet pair is 48.4 km (hamlet_stone_wall to
  hamlet_vale_mouth), so no hamlet needed a second move.
- Forty kilometres: the tightest village pair is 52.0 km
  (village_wheat_plain to village_willow_bank) and the tightest village to a
  national settlement is 65.6 km (village_wheat_plain to town_honey_vale). The
  rule did shape the eastern end of the trunk, where the last 42 km before
  town_scarp may hold no village: hamlet_vale_mouth at 41.6 km and
  hamlet_stone_wall at 23.2 km carry that stretch, and the road gap stays
  inside the maximum.
- Seventy-five kilometres: before the change one gap over 75 km lay wholly
  inside the area, the trunk from town_honey_vale to town_scarp at 273.6 km.
  Three settlements split it into 68.1, 63.0, 70.0 and 72.5 km. Two further
  in-area stretches start at the area boundary and end at the first
  settlement; the salt road runs 31.7 km and the hill road 10 km from the
  boundary before the first settlement. Both are under the maximum, and the
  checker skips them because the gap crosses the boundary.

The rectangle is flat. Every walkable cell carries elevation band 5 or 6 and
the three-cell relief range is 0 or 1, so no candidate had a slope, pass foot
or terrace to justify a site. Every geographic reason written is a valley
floor variant of the hills river, its banks or the two roads that cross the
vale.

## 2. Node counts

No generated map needed more than the minimum. Each village generated four
outdoor nodes (village green, two village ends, church front), and the
one-gate village generated the same four with the second end left as a road
to nowhere rather than a gate. Each hamlet generated two (crossing and
farmstead front). The design allows one or two extra nodes for a site feature
such as a ferry or a mine mouth; no site in this rectangle has one, so the
allowance was unused.

## 3. Naming style

No name written to `locations.yaml` needed a second attempt; the second
attempts happened in review before writing.

- 竹圍 was dropped for 木柵. The character 竹 appears nowhere in the lore
  corpus; the flora vocabulary in use is 柳, 松, 楓, 橄欖, 橙 and 葡萄, so a
  bamboo fence would have introduced a plant no other document names.
- 河灣村 was dropped for 柳岸村. The site is 6 km from the hills river, and
  「灣」 claims a bend the map does not draw, while 「岸」 is true of the south
  bank.

Two naming facts the next change will meet:

- The thirteen candidate names that survived are all two- to three-character
  toponyms from the region's own vocabulary (埔, 坳, 寮, 窯, 圍, 壁, 屋, 磨,
  茶, 炭, 瓦, 羊, 牛, 麥, 柳), and none collides with the 66 existing
  location names.
- The ID decides a village's spur target, because the spur stage offers only
  the settlements whose key sorts earlier. `village_willow_bank` sorts after
  `village_wheat_plain` and therefore spurs 69.8 km to it; any ID sorting
  before it would have targeted town_honey_vale at 111 km and broken the
  75 km road rule. Naming is therefore a placement decision, not a label.

## 4. Monster habitats

No `MonsterSite.coordinates` lies in the rectangle. Four `EcologyZone`
rectangles covered candidate road cells, and every conflict was resolved by
moving the settlement, so no habitat was edited.

| Zone | Rectangle | Cells it removed |
| --- | --- | --- |
| `western_road_01` | x 1025-1044, y 506-525 | the southern end of the salt road, about 20 km of it |
| `town_honey_vale_hinterland` | x 1024-1043, y 675-694 | the northern end of the salt road, about 20 km of it |
| `western_road_02` | x 1186-1205, y 858-877 | a 20 km stretch of the hill road |
| `town_scarp_hinterland` | x 1283-1302, y 693-712 | the eastern tip of the trunk road |

`western_road_05` (x 1151-1170, y 692-711) sits one cell north of the trunk
road and did not remove a cell that any site needed; hamlet_sheep_yard at
(1168, 689) keeps the cell and its eight neighbours outside it.

## 5. Tools

No tool refused a valid site, and none reported a finding that looked wrong.

- `tools.settlement_spacing` reported `village_off_road` for the one village
  without a road before its spur existed, which is the state task 2.1
  expects, and reported `spacing: 0 problems` after the spur stage ran.
- `tools.settlement_synthesis generate` refused nothing; all 13 maps were
  generated on the first run, and `lint` reported no error and no warning.
- `tools.road_network` and `tools.map_reference_context` accepted the
  regenerated artifacts on the first `--check` after each run.
- One operational note, not a tool fault: two Evennia `--keepdb` test runs
  started at the same time fail with `database is locked` in `setUp`. The
  focused modules have to run one after another.
- One test-hygiene fault, found by running the settlement-sensitive modules
  one per command as `docs/development/settlement-synthesis.md` asks. Several
  of them read a published registry in their own fixture before anything
  publishes the map world in that process, so they fail alone with
  `SettlementNotLoaded`, while the same module passes inside a full-suite run
  where an earlier module has published. The fixture in
  `web/webclient/actions/tests/test_node_ids.py` shows the pattern: its
  `setUpClass` resolves `_south_gate_xyz()` before `sync_test_settlements()`,
  and only the latter publishes. The modules that fail this way alone are
  `web.webclient.actions.tests.test_node_ids`,
  `web.webclient.actions.tests.test_travel_actions`,
  `world.quests.tests.test_compile_blueprint`,
  `world.quests.tests.test_encounter_activation`,
  `world.quests.tests.test_encounter_dispatch`,
  `world.quests.tests.test_package_proposal`,
  `world.quests.tests.test_quests_observability` (2 of 16),
  `world.quests.tests.test_scene_smoke`,
  `world.quests.tests.test_story_dialogue`,
  `world.quests.tests.test_story_effects` and
  `world.rules.tests.test_party_follow` (which cannot even be discovered
  alone). Every one of them reaches the registry before the first authored
  settlement is read, so the failure does not depend on the placed data, and a
  placement change cannot fix it from inside its file list. Each label was
  re-run against a clean checkout of the baseline commit `9892e18d` outside
  the repository and fails there with the same error and the same test counts,
  which is the measurement `tasks.md` task 5.2 records.
- `world/quests/tests/test_compile_registration.py` fails four tests on its
  registration rollback with `no such table: django_content_type`, against
  both a reused and a freshly built test database, and on the baseline
  checkout. That path does not read settlement data either.

## 6. Counts

- Settlements: 4 villages and 9 hamlets, 13 in total.
- On a road: 11. Three villages stand on trunk cells and eight hamlets stand
  on inner cells of a trunk road.
- Off a road: 2. One village (village_willow_bank) and one hamlet
  (hamlet_water_mill, a mill on the south bank of the hills river).
- Road cells: the artifact held 15,415 cells before the change and 15,441
  after it.
- Spurs: four records, one per village. Three villages stand on a trunk cell,
  so their spur reuses trunk cells and adds nothing. The off-trunk village's
  spur adds the only new road cells of the change, 26 of them, in a 69.8 km
  road from village_wheat_plain.
