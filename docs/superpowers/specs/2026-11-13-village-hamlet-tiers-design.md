# Village and hamlet settlement tiers

Date: 2026-11-13

## 1. Purpose

The world has 59 national settlements. The smallest town holds 6,000 people,
and nothing exists below it. Settlements hold 3.47 million of the world's
30 million people. On the official roads (官道), the farthest point from any
settlement is 516 km away, about 20 walking days.

This design adds two settlement tiers below town, places about 250 to 300 of
them, and connects them to the road network. It sets the rules that every later
OpenSpec change in this work must follow.

## 2. Decisions

| Topic | Decision |
| --- | --- |
| New kinds | `village` (村莊) and `hamlet` (小村莊) |
| Nations | Humans and beastfolk share both kinds; the nation selects the archetype |
| Elven villages | IDs move from the `village_` prefix to `elven_village_`. This is an approved exception to the never-rename rule |
| Population | The map is a representative sample. The remaining people live dispersed and have no map |
| Road spacing | Along an official road, the next settlement of any kind is at most 75 km away |
| Minimum spacing | Tiered by kind, see §4 |
| Village roads | Every village gets one spur to its cheapest-to-reach node |
| Hamlet roads | A hamlet may sit on a road or away from every road |
| Count ratio | About one village to two hamlets |
| Placement | A working script proposes candidates; the implementing agent approves and writes them |
| Old saves | Clean cutover. No migration and no aliases |

The place list for each tier is in `docs/lore/settlement-locations.md`, section
〈人類聚落的層級差異〉. That document is the narrative authority; this document is
the structural one.

## 3. Data model

### 3.1 Kinds and IDs

- The closed kind list gains `village` and `hamlet`. `AnchorKind` gains the
  same two members.
- ID prefixes: `village_` for villages, `hamlet_` for hamlets. Both nations use
  the same prefixes.
- The three elven villages become `elven_village_fionnen`,
  `elven_village_ciaran` and `elven_village_eolas`. Every reference changes in
  one cutover: location data, `ANCHOR_LORE`, the settlement map file, service
  host room bindings, quest destinations and tests. No alias remains.

### 3.2 Nation and population

- A settlement's nation is the nation of the national border that contains its
  cell. A candidate outside every national border is rejected.
- Population ranges: village 300 to 2,000; hamlet 50 to 300. The placement
  script assigns a value in range, higher where the site is better (a valley
  floor, a road junction).
- The world population stays 30 million. The sum of settlement populations is
  a sample and is never reconciled against it. Any existing test that assumes
  such a reconciliation is corrected in wave 1.

### 3.3 Monster birth exclusion

- `village` and `hamlet` join the inhabited settlement categories and receive
  the same default birth buffer as the existing kinds.
- A candidate that lies inside an authored monster habitat, or that removes the
  eligibility of a habitat declared as remote from settlements, is a conflict.
  The implementing agent resolves it by moving the settlement or adjusting the
  habitat. No conflict is left unresolved at commit time.

## 4. Spacing rules

One validation step checks all three rules.

| Rule | Statement |
| --- | --- |
| Hamlet minimum spacing | A hamlet is at least 15 km, in a straight line, from every other settlement |
| Village minimum spacing | A village is at least 40 km, in a straight line, from every village, town, city, port and capital |
| Road coverage | From any point on an official road, travelling along the road in either direction reaches a settlement of any kind within 75 km |

- Minimum spacing uses straight-line distance, because settlements that merge
  do so through spatial proximity. Road coverage uses distance along the road,
  because it measures travel time.
- The 75 km figure is three walking days: 4.5 km/h on a road, six walking hours
  a day, and the fatigue rule's 90% stage after 3.75 hours, which gives about
  26 km a day.
- Exemption: a settlement with a special design carries an explicit exemption
  mark and a reason in `content/maps/locations.yaml`. Distances among the 59
  existing national settlements are not checked retroactively.
- Elven villages are hidden from other peoples. They do not count as a road
  settlement, and no new settlement keeps a distance from them. No new
  settlement lies in a road-forbidden region such as the northern deep forest.

## 5. Distribution targets

These are targets for the placement script, not hard limits.

- Villages: about 70% on a trunk road or within 5 km of one, to shorten long
  road stretches. About 30% lie 20 to 60 km from a trunk, at a site with a
  geographic reason (a valley, a lake shore, a mining area), and each receives
  a spur.
- Hamlets: about 80% on an official road, spurs included, to bring road
  coverage under 75 km. About 20% have no road and lie 15 to 30 km from a
  village or town. These do not count toward road coverage.
- Expected totals: 250 to 300 settlements, and 1,000 to 1,500 km of new spur.

Estimate by nation, from current road length divided by 75 km:

| Nation | Road km | New settlements | Villages | Hamlets |
| --- | ---: | ---: | ---: | ---: |
| Altoria | 7,530 | about 100 | about 35 | about 65 |
| Grandia | 7,110 | about 95 | about 30 | about 65 |
| Valhalla | 3,800 | about 50 | about 17 | about 33 |

The table is a lower bound. Spurs and placement constraints raise the totals.

## 6. Road network: spur stage

The road generator gains a second stage.

- Stage 1 is the current algorithm, unchanged. Its nodes remain capital, city,
  port and town.
- Stage 2 processes villages in ID order. For each village it finds the node
  with the lowest walking cost and routes one spur to it. Candidate nodes are
  every stage 1 node and every village already processed. A spur may reuse
  existing road cells.
- The artifact marks each road as trunk or spur.
- Regression guarantee: with no village in the input, the artifact is
  byte-for-byte identical to the current one.
- Hamlets are never road nodes. An on-road hamlet is placed on a cell that
  already carries a road.

## 7. Settlement map generator: single-cell tiers

- A new single-cell layout serves `village` and `hamlet` only. Every kind from
  town upward keeps the minimum footprint of two cells.
- Two new size tiers:

| Kind | Footprint | Outdoor nodes | Typical content |
| --- | ---: | ---: | --- |
| `village` | 1 cell | 4 | Two village ends, the green with the well, the church front |
| `hamlet` | 1 cell | 2 | The crossing and the farmstead front |

- Entrances follow the road segments that meet the settlement: two when a road
  passes through, one at the end of a spur or with no road.
- Node counts are minimums. A site with a geographic feature, such as a ferry
  or a mine mouth, may add one or two nodes.
- Beastfolk villages and camps reuse the existing tribal morphology logic at
  single-cell scale.
- Shops, the guild branch and the church are interiors attached to outdoor
  nodes. They belong to the service layer and are out of scope here.

## 8. Placement

The placement script is a working tool for the implementing agent. It is not a
maintained product: it has no stable interface, no tests and no developer
documentation, and the agent may rewrite it in any wave. The naming vocabulary
is working data of the same kind.

What is maintained is the result and its validation. `locations.yaml`,
`ANCHOR_LORE`, the road artifact and the settlement maps are the committed
source of truth. The validation step of §4 is a tested check that runs in CI.

### 8.1 Names and IDs

The script proposes a Traditional Chinese name and an English ID from the
site's terrain, waterway, region and neighbours, for example a river site named
after a ford or a hill site named after a slope. IDs follow the existing style,
such as `village_willow_ford`. Beastfolk settlements use a separate vocabulary.
An ID is fixed once written to `locations.yaml`.

### 8.2 Approval criteria

Before writing a candidate, the implementing agent confirms that:

1. the spacing and coverage rules of §4 hold;
2. the site has a geographic reason;
3. the name fits the terrain, and the name and ID are globally unique;
4. no monster habitat conflict remains.

### 8.3 Procedure for one area

1. Propose villages, approve them, and write them to `locations.yaml` and
   `ANCHOR_LORE`.
2. Regenerate the road network. Each new village receives a spur.
3. Propose hamlets, approve them, and write them.
4. Generate and review each settlement map.
5. Regenerate the district partition and the elevation tiles, in the order the
   road network guide gives.
6. Run validation: the three spacing rules, ID and name uniqueness, road
   artifact freshness, and monster birth exclusion.

Step 3 depends on step 2, because hamlet sites depend on the spurs. Validation
fails when a village has no spur.

## 9. Waves

| Wave | Content | Result |
| --- | --- | --- |
| 1 | Kinds and `AnchorKind`; elven village ID cutover; monster birth exclusion list | One cutover of code and content |
| 2 | Spacing and coverage validation; road spur stage; single-cell layout and two tiers | Tool extensions, with no new settlement yet |
| 3 | Trial: Altoria's western hills, about 10 to 15 settlements | The first villages and hamlets, and any rule corrections |
| 4 | The rest of Altoria | About 85 settlements |
| 5 | Grandia | About 95 settlements |
| 6 | Valhalla | About 50 settlements |
| 7 onward | Service layer, with the 27 towns | Separate design |

- The trial area is the western hills around town_scarp. It has both hills and
  valleys. It does not hold the road stretch that is farthest from any
  settlement: that stretch (516 km) lies in `southwest_coast`, near cell
  (1015, 339), and the farthest point around town_scarp is 234 km. The coast
  stretch is built in wave 4.
- Road coverage is implemented in wave 2 but applies to an area only after
  that area is built. Validation carries a list of completed areas. Wave 3 adds
  the western hills. After wave 6 the list covers every road and is removed.
- Minimum spacing applies to every `village` and `hamlet` from wave 2, with no
  transition period.
- If the trial shows that a spacing value, a node count or the naming style
  needs to change, this document is revised before wave 4 starts.

## 10. Testing

Specifications and tests define logic and contain no game data.

- Validation: small synthetic maps cover the pass and fail cases of each rule,
  and the exemption mark.
- Road spurs: one spur per village, the cheapest node chosen, a fixed order,
  and an unchanged artifact when no village exists.
- Single-cell layout: node counts, and entrance counts against road segments.
- The placed settlements have no individual tests. The validation step checks
  the committed data in CI.
- No test asserts wall-clock time or hardware speed.

## 11. Documentation

- `docs/development/settlement-synthesis.md`: the two tiers and the single-cell
  layout.
- `docs/development/road-network.md`: the spur stage and the trunk and spur
  distinction.
- `.agents/skills/map-data-authoring` references: the kind list, the ID
  prefixes and the spacing rules.
- `docs/lore/settlement-locations.md`: each wave changes the matching 〔提案〕
  marks to 〔已實作〕.

## 12. Out of scope

- Service hosts, shop stock and interiors.
- Settlements for other peoples, and maps for the two elven villages that have
  none.
- Villages without a road. Every village has a spur.
- The population and guild branch figures in the story settings document. The
  figure of about 200 guild branches there is a rough estimate and constrains
  nothing.

## 13. OpenSpec changes

Fourteen changes implement waves 1 to 6. All are proposed and validated with
`openspec validate --strict`; none is implemented. Each lives in
`openspec/changes/<name>/`. Wave 7 has no change yet.

| # | Change | Wave | Scope |
| ---: | --- | --- | --- |
| 1 | `elven-village-id-cutover` | 1 | Rename the three elven village IDs to `elven_village_*` across about 36 files; no alias, no migration; spec-less |
| 2 | `village-hamlet-kinds` | 1 | Add `village` and `hamlet` to the location kinds and `AnchorKind`; add them to the monster birth exclusion categories, the sight silhouettes and the editor kind list |
| 3 | `single-cell-footprint-entry` | 2 | Add `wilderness_entry.single_cell_footprint`, so a one-cell mask can be a real footprint with several gates (see §14, item 1) |
| 4 | `settlement-spacing-validation` | 2a | The `tools.settlement_spacing` command: the three spacing rules, the completed-area list, the exemption field and a CI step |
| 5 | `road-spur-stage` | 2b | The road generator's second stage; the artifact marks spurs with `spur_of` |
| 6 | `single-cell-size-budget` | 2c | The single-cell size tiers (village 4 nodes, hamlet 2), the road-contact cell query and an entrance-versus-road lint |
| 7 | `single-cell-settlement-layout` | 2c | The generator's single-cell layout and `--missing --kind` |
| 8 | `western-hills-village-trial` | 3 | The trial area around town_scarp (`western_hills_valleys`, x 1000 to 1340, y 501 to 950), 10 to 15 settlements |
| 9 | `altoria-hills-village-placement` | 4 | The rest of the western hills, about 50 |
| 10 | `altoria-coast-village-placement` | 4 | `southwest_coast`, about 35 |
| 11 | `grandia-south-village-placement` | 5 | Eastern plains with y at most 1100, and `southeast_coast`, about 50 |
| 12 | `grandia-north-village-placement` | 5 | Eastern plains with y above 1100, about 45 |
| 13 | `valhalla-village-placement` | 6 | `northwest_highland_forest`, about 50 |
| 14 | `road-coverage-area-removal` | after 6 | Remove the completed-area list, so road coverage applies to every road |

Waves 4 and 5 are split in two, and wave 2c is split in two, so that each
change fits a working day. Splitting the placement changes further was
considered and rejected: the precedent `altoria-settlement-maps` built 19
multi-cell settlements, about 170 nodes, in one change; each placement change
here builds about 50 single-cell settlements, about 130 nodes.

### 13.1 Dependencies and shared files

| Change | Depends on | Shared files that can conflict |
| --- | --- | --- |
| 1 | none | `world/lore/anchors.py`, `content/maps/locations.yaml`, `locations-and-districts.md`, the reference context (with 2) |
| 2 | 1 | `schema.py` (with 3 and 4) |
| 3 | none; in practice after 2 | `schema.py`, `documents.py` (with 4, different declarations); the reference context |
| 4 | 2 | the same as 3; `locations-and-districts.md` |
| 5 | 2 | the reference context only |
| 6 | 2, 3 | `tests/test_settlement_terrain_fit.py` (with 3); `workspace.py`, `__main__.py` and `settlement-synthesis.md` (with 7) |
| 7 | 6 | as 6 |
| 8 to 13 | 3 to 7, and each other in order | `locations.yaml`, `anchors.py`, `content/maps/settlements/`, `tools/settlement_spacing_areas.json`, `road_network.json`, `district_partition.json`, the reference context |
| 14 | 13; 4 archived | `tools/settlement_spacing_areas.json` |

`content/map-reference-context.json` lists `packages/map-core`, `world/lore`,
`world/rules` and `world/quests` as sources, so every change that touches those
directories regenerates it. After a rebase, rerun the command; never merge the
file by hand.

### 13.2 Parallel implementation batches

| Batch | Changes | Mode |
| ---: | --- | --- |
| 1 | 1, then 2 | Serial; they share four files |
| 2 | 3, 4 and 5 | Parallel; they meet only on different declarations in `schema.py` and `documents.py`, and on the reference context |
| 3 | 6, then 7 | Serial with each other; 6 waits for 3 to merge; both run in parallel with 4 and 5 |
| 4 | 8, 9, 10, 11, 12, 13 | Strictly serial, in this order. Each change's spurs and hamlets are the next one's input, and all write the same files |
| 5 | 14 | Last |

## 14. Resolutions where the design met the code

The proposal work found twelve places where this document was ambiguous or
disagreed with the code. These are the resolutions now in force.

1. **Single-cell footprint.** The code treats a mask of exactly one `#` as a
   concealed point entry: one gate, entered by walking toward it from the cell.
   That cannot give the two entrances of §7, because the road would be blocked
   at the gate. Change 3 adds an optional explicit field that marks a real
   single-cell footprint. Documents without it behave as before.
2. **Road before map.** §8.3 builds roads before maps, yet a road node needs a
   settlement document. A village becomes a spur endpoint from its kind and
   cell alone; the map's gates are derived afterwards from the road cells.
3. **Footprints as road obstacles.** A settlement footprint is normally an
   obstacle for roads, which contradicts a hamlet placed on a road cell. The
   road generator skips `village` and `hamlet` footprints, so stage 1 does not
   depend on villages and the trunk never moves because of a placement.
4. **Byte-identical artifact.** The road source signature includes the hash of
   `road_network.yaml`, so the spur kind is a constant in `roads.py`, not a YAML
   field, and the artifact version does not change.
5. **Cheapest node.** The cost includes the road-reuse discount, and one search
   chooses both the target and the path.
6. **75 km wording.** Both phrasings in this document mean the gap along the
   road between adjacent settlements is at most 75 km. Reading it as the
   distance to the nearest settlement would allow a 150 km gap. A gap that
   crosses an area boundary is checked only after both areas are built. The
   end cell of any road also counts as a settlement position, because a merged
   trunk can pass in front of another town's gate.
7. **Nation border.** In code the national border is a line, not an area.
   A cell's nation is the `nation_key` of its terrain region. A region with no
   nation (central mountains, northern deep forest) is outside every border.
   Neither region holds a road cell today.
8. **Trial area.** See §9. The trial rectangle is the one the user named, the
   western hills around town_scarp.
9. **Population reconciliation tests.** No existing test sums town
   populations. The tests reconcile only the three nations, the three capitals
   and the three elven villages, so only a comment in `ANCHOR_LORE` changes.
10. **Habitat keys.** Ecology keys such as `village_eolas_hinterland` are not
    location references and keep their names. The test module
    `test_village_ciaran.py` and historical design documents are not renamed.
11. **Splits.** Waves 2c, 4 and 5 are split as §13 shows.
12. **Beastfolk layout.** A ring does not fit in one cell. Beastfolk settlements
    take the tribal vocabulary and the `tribal_ring` label with the same
    geometry as human ones.
