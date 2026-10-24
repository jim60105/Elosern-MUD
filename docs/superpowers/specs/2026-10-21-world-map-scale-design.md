# World Map Scale and Metric Settlement Design

Date: 2026-10-21
Status: Approved; OpenSpec proposals created (§16); not implemented.
Companion design: [Party Fatigue and Sleep](2026-10-21-party-fatigue-and-sleep-design.md).

## 1. Goal and authority

Give Elosern a coherent physical geography and distance-based travel model. Settlement coordinates use meters, with irregular spacing and street alignments. Wilderness coordinates support intercity travel without representing every meter as a room.

The supplied `tmp/story_settings/world_info.md` is the source for continental area, population, national shares, geographic relationships, and named anchors. Existing authored lore registries remain the runtime source of truth. This design records intended updates to those registries; it does not make the temporary source file a runtime dependency.

This document explicitly amends the fixed 30-second movement example in section 6.5 of `2026-07-29-ai-mud-engine-design.md` for distance-bearing settlement and wilderness travel. It preserves the four map layers, deterministic single-writer ownership, player-driven clock, atomic movement settlement, and offline playability. Main OpenSpec capabilities remain the current implemented contract until owning changes land.

The geographic world specified here is the known continent. No planet size or additional continent is inferred.

## 2. Scope and exclusions

Included are the continental outline, existing major anchors, functional port sites, settlement footprints, meter coordinates for the two authored outdoor maps, walking speeds, geometric distances, and the coordinate consumers needed for a clean cutover.

Excluded are vehicles, mounts, shipping gameplay, fast travel, new movement-enhancement abilities, active-monster encounters, a general survival or carrying system, and changes to party capacity. Five or six people describe the travel calibration case, not a new roster limit. Long-distance automatic route execution is not introduced by this design; coordinates and costs must permit a later interruptible route controller without pretending it already exists.

The companion fatigue design supplies travel penalties and forced-sleep restrictions. It does not change the map units.

## 3. Observed implementation baseline

Research inspected `world/maps/wilderness_provider.py`, `world/lore/wilderness_entry.py`, `world/lore/anchor_placement.py`, both authored outdoor maps, movement settlement, clock rules, and local-map presentation.

| Surface | Observed baseline | Consequence |
| --- | --- | --- |
| Wilderness | 224 by 224 cells, 10 km per cell | The enclosing square is 5,017,600 square kilometers, without distinguishing mainland from sea |
| Wilderness movement | 9,000 seconds per ordinary step | Equivalent to 4 km/h over a cardinal 10 km step |
| Capital footprint | 5 by 5 wilderness cells | Represents 2,500 square kilometers at the current scale |
| Ciaran footprint | 3 by 3 wilderness cells | Represents 900 square kilometers for about 100 inhabitants |
| Settlement movement | Fixed 30 seconds per exit | Does not derive time from physical length |
| Authored settlement graphs | Dense-coordinate ASCII parsed by XYZGrid | Simply multiplying coordinates would produce enormous sparse whitespace maps |
| Local-map protocol/layout | Coordinate bounds of -1,024 to 1,024; rank compression after a 64-cell lattice span | Meter coordinates can be rejected or have their unequal spacing erased |
| Synchronization | Missing old grid coordinates can be deleted | A coordinate replacement must preserve existing room identities and references |

The real ASCII parser was exercised for geometry using database-independent prototypes. Altoria has 21 nodes, 26 undirected roads, and 6 cycles. Ciaran has 10 nodes and 9 roads. Database room spawning was not exercised.

## 4. Continental area and demographics

Retain approximately 5,000,000 square kilometers of land and approximately 30,000,000 inhabitants. The elven population is approximately 300; the source population totals are rounded, rather than a census requiring the elves to be subtracted from another nation.

| Region | Territory share | Land target, square kilometers | Authored population | Mean inhabitants per square kilometer |
| --- | --- | --- | --- | --- |
| Grandia Empire | 38% | 1,900,000 | 12,000,000 | 6.32 |
| Altoria Kingdom | 27% | 1,350,000 | 9,000,000 | 6.67 |
| Valhalla Beast Kingdom | 25% | 1,250,000 | 9,000,000 | 7.20 |
| Central neutral lands | Remaining approximately 10% | 500,000 | No separate regional total established | Not inferred |

An overall density near six inhabitants per square kilometer leaves room for mountains, deep forest, monster habitats, and sparse frontiers. Settlement density must be concentrated around productive plains, river valleys, and coasts. It must not be simulated as six inhabitants in every cell.

The three capitals contain 800,000, 600,000, and 400,000 people, totaling 6% of continental population. Treat them as unusually large fantasy cities with regional food supply, storage, and water transport. Retain the authored populations instead of forcing them into ordinary small medieval town footprints. Valhalla's urban population requires pastoral production and trade; nearby hunting alone is insufficient.

## 5. Coordinate frames and mainland outline

### 5.1 Wilderness frame

The wilderness frame is 2,700 by 2,700 one-kilometer cells. Valid indices are `0 <= X < 2700` and `0 <= Y < 2700`. X increases eastward and Y northward. A cell is an area; its representative center in absolute meters is:

`E = 1000 * X + 500`, `N = 1000 * Y + 500`.

The frame contains 7,290,000 logical cells. Land occupies approximately 5,000,000 of their square kilometers; the remainder is nearshore sea and space around the irregular coastline. These are logical cells, never millions of pre-created Evennia rooms.

### 5.2 Coastline control polygon

The following ordered vertices are absolute kilometer positions at cell boundaries, not cell-center indices. Close the last vertex back to the first.

| Vertex | East, km | North, km |
| --- | --- | --- |
| 1 | 450 | 100 |
| 2 | 1850 | 100 |
| 3 | 2400 | 450 |
| 4 | 2600 | 1350 |
| 5 | 1930 | 2250 |
| 6 | 1800 | 2600 |
| 7 | 750 | 2550 |
| 8 | 200 | 2050 |
| 9 | 100 | 1050 |
| 10 | 300 | 350 |

The polygon's shoelace area is 5,000,000 square kilometers. The land spans approximately 2,500 km on each axis, with at least approximately 100 km of ocean margin to the frame edges. Later bays, river mouths, and inland water can refine this approximate outline while preserving the approximate land-area target. Raster cell counts need not equal the vector polygon area exactly.

Sea is not walkable. The ocean margin reserves geographic space for future coastal routes; it does not implement boats or make the open sea traversable.

### 5.3 Settlement frame

Each settlement owns an integer-meter local frame with X eastward and Y northward. Its z-coordinate continues to identify the logical grid/layer. Do not reinterpret that z-coordinate as physical elevation. Interiors that currently have no coordinates remain connected interior scenes; do not invent meter positions for them.

Bind one known local anchor to the absolute center of the settlement's wilderness anchor cell:

`world_position_m = wilderness_anchor_center_m + local_position_m - local_anchor_position_m`.

For Altoria, the local anchor is the central plaza at `(3500, 2850)`, bound to wilderness cell `(860, 1080)`. For Ciaran, it is the village plaza at `(220, 305)`, bound to `(1340, 1220)`.

Cross-layer distances must use this transform and authored approach geometry. Never subtract local-meter coordinates directly from wilderness cell indices.

## 6. Terrain, political geography, and traffic

The central mountain system follows a bending north-south corridor broadly around wilderness X 1,310 to 1,510. Its approximately 200 km width includes foothills, valleys, and subsidiary ridges, consistent with approximately 500,000 square kilometers of neutral mountain lands. It is not a continuous 200 km wall of summit terrain.

Altoria occupies the southwestern hills and river valleys. Valhalla's controlled settlements lie in northwestern highland forest. Grandia's agricultural and political core lies in the eastern plains. Northern deep forest begins broadly around Y 2,200. Preserve the distinction between nominal political claims and actual control, especially in northern forest and neutral elven valleys.

Territory shares are area targets, not instructions to draw straight rectangular national borders. Terrain and political ownership are separate authored layers. Do not preserve the current rectangular region classifier when it contradicts these anchor relationships.

The capital's lower riverfront connects to a southwest-flowing river system and the kingdom's western/southwestern ports. The imperial river network connects the capital's productive plain to southeastern ports. These relationships are geographic authoring constraints; navigable rivers are not new player transport mechanics.

East-west bulk commerce mainly follows the southern coast. Land crossings of the central range require explicit passes or mountain trails. Reserve a principal pass control point near `(1410, 980)`; it is a mountain itinerary requiring supplies and slower segments, not a guaranteed all-road shortcut. Cliffs, closed ridges, and water remain impassable on foot.

## 7. Absolute major-anchor placement

These are intended new wilderness cell indices. They replace the existing placements; they are not a scale multiplication of the old wilderness positions.

| Registry key | Canonical name | X | Y | Geographic constraint |
| --- | --- | --- | --- | --- |
| `capital_altoria` | 聖潔王都 | 860 | 1080 | Western river valley and hills; riverfront below northern terraces |
| `capital_grandia` | 輝煌帝都 | 1970 | 1280 | Eastern agricultural plain and major river supply |
| `capital_valhalla` | 咆哮王城 | 780 | 1910 | Northwestern highland forest and tribal routes |
| `village_ciaran` | 暗影谷村 | 1340 | 1220 | Underground settlement on the western flank of the central mountains |
| `village_fionnen` | 翠綠森林村 | 1490 | 1510 | Forest on the eastern mountain flank |
| `village_eolas` | 幽月谷村 | 1410 | 2150 | Hidden northern mountain valley near deep forest |
| `dungeon_eternal_night` | 永夜迷宮 | 900 | 2350 | Northern deep forest under nominal Valhalla jurisdiction |
| `dungeon_dragon_nest` | 龍之巢穴 | 2340 | 1220 | Remote eastern Grandia |
| `dungeon_arcane_ruins` | 魔導遺跡 | 480 | 1160 | Western Altoria hills and ancient/mineral sites |

All nine proposed anchor cell centers lie within the coastline polygon. Authored knowledge of an elven village's location does not reveal it to players; map-knowledge and visibility rules remain authoritative.

### 7.1 Functional port sites

The source describes southwest and southeast port-city clusters without naming their cities. Reserve the following land-side harbor cells as authoring constraints. They are not new named anchors, spawned cities, quests, or population declarations in this change.

| Functional site | X | Y | Intended role |
| --- | --- | --- | --- |
| Kingdom southwestern main port | 301 | 350 | River/sea transfer and foreign trade |
| Kingdom western secondary port | 201 | 700 | Western mining and craft exports |
| Kingdom southern secondary port | 600 | 101 | Southern coastal supply |
| Imperial southeastern main port | 2070 | 241 | Agricultural and magical-goods exports |
| Imperial southeastern secondary port | 2400 | 454 | Eastern coastal collection |
| Imperial southern secondary port | 1700 | 101 | Southern coastal transfer |

All six cell centers are on the land side of the proposed coast. Further regional towns and guild branches remain necessary in the setting; the nine named anchors do not imply an otherwise empty continent.

## 8. Metric Altoria layout

Target approximately 40 square kilometers of built-up city, about 15,000 inhabitants per square kilometer for 600,000 people. The authored 21 nodes represent major streets/district locations across an irregular roughly seven-kilometer envelope. This area target includes housing and public space; it is not a sum of room squares or a claim that all housing has been authored.

Preserve the riverbank lower city, central market belt, northward ascent through three terraces, and existing street connectivity. Small cross-axis offsets and unequal lengths remove the rigid rectangular alignment. Preserve the existing two diagonal shortcuts and all 26 undirected roads.

| Location | Old local coordinate | New local coordinate, meters |
| --- | --- | --- |
| 南門 | (3, 0) | (3050, 150) |
| 碼頭埠 | (1, 1) | (1250, 760) |
| 河岸道 | (2, 1) | (2150, 920) |
| 南大道 | (3, 1) | (3140, 1050) |
| 客棧巷 | (4, 1) | (3970, 1120) |
| 浴場前 | (5, 1) | (4830, 970) |
| 舊城牆遺跡 | (2, 2) | (2350, 1900) |
| 大道北段 | (3, 2) | (3350, 1980) |
| 工匠巷 | (1, 3) | (1300, 2600) |
| 市場街 | (2, 3) | (2420, 2700) |
| 中央廣場 | (3, 3) | (3500, 2850) |
| 公會前 | (4, 3) | (4380, 3000) |
| 東市 | (5, 3) | (5380, 2850) |
| 東門 | (6, 3) | (6500, 3010) |
| 校場外 | (2, 4) | (2300, 3820) |
| 聖階 | (3, 4) | (3480, 3700) |
| 大神殿前 | (4, 4) | (4560, 3920) |
| 貴族區前 | (3, 5) | (3500, 4850) |
| 上城門 | (4, 5) | (4690, 5010) |
| 學院前 | (5, 5) | (5650, 5200) |
| 王宮前庭 | (4, 6) | (4500, 6350) |

The unmodified connectivity has no coordinate collisions or compass-octant changes under this placement. Shops and interiors remain attached to their host location; do not introduce kilometer-long door links because district nodes are far apart.

## 9. Metric Ciaran layout

Target approximately 0.4 square kilometers of village living space for about 100 elves, with additional surrounding forest and gathering land outside that footprint. Preserve the ten-node, nine-edge branching path topology.

Reconcile the original underground setting with existing trees and daylight by placing the main living chambers under the mountain and the authored outdoor nodes in a small number of skylit collapse basins or ravine openings. The entire settlement must not become an ordinary exposed forest village. Preserve the hidden path rather than introducing city walls or gates.

| Location | Old local coordinate | New local coordinate, meters |
| --- | --- | --- |
| 隱密小徑 | (0, 1) | (35, 270) |
| 村中廣場 | (1, 1) | (220, 305) |
| 溪畔小徑 | (1, 0) | (245, 135) |
| 溪畔下游 | (2, 0) | (430, 85) |
| 練刀場 | (2, 1) | (405, 335) |
| 藥草園 | (3, 1) | (590, 300) |
| 村北古樹下 | (1, 2) | (200, 465) |
| 長老古樹下 | (1, 3) | (165, 650) |
| 織房坡 | (2, 2) | (390, 495) |
| 銀葉坡 | (2, 3) | (440, 665) |

The placement has no collisions or compass-octant changes. The wilderness representation is a hidden point entrance, not a nine-square-kilometer village obstacle after the scale change.

## 10. Distances, speeds, and time

### 10.1 Base speeds

| Travel context | Healthy ordinary human baseline | Cardinal 1 km time |
| --- | --- | --- |
| Settlement walking | 1.25 m/s, or 4.5 km/h | 800 seconds |
| Wilderness good road | 4.5 km/h | 800 seconds |
| Open off-road ground | 3 km/h | 1,200 seconds |
| Passable forest path/woodland | 2 km/h | 1,800 seconds |
| Rough mountain trail | 1.5 km/h | 2,400 seconds |

These are design calibration values for an equipped five- or six-person party. Do not apply a separate headcount speed penalty, average member speeds, or turn combat agility directly into travel speed. Apply each member's actual travel restrictions and fatigue multiplier; party speed is the slowest eligible travelling member's sustainable speed. A forced-sleeping present member blocks party travel under the companion design.

A wilderness diagonal is approximately 1.414 km, not one cardinal kilometer. At healthy road speed it costs 1,132 seconds after rounding up. Impassable corner cutting is forbidden.

### 10.2 Sparse roads and rounding

One meter is coordinate precision, not a requirement for a room or command at each meter. A movement command traverses an authored edge between named locations.

For a straight road, use Euclidean endpoint distance. For an authored bent road, use the full meter-space polyline length. The initial two settlement cutovers preserve their existing edges with straight-segment geometry; additional bend/elevation geometry must be authored explicitly rather than supplied by a hidden universal detour multiplier.

Integrate travel time against actual distance, terrain speed, member restrictions, and fatigue changes along the traversed segment. If a fatigue threshold changes speed during a long traversal, apply the new speed only to the remaining distance. Round up once for the committed traversal, not once per meter. Preserve fractional mental consumption as specified in the companion design.

The healthy straight-segment baselines are approximately 37 minutes from Altoria's south gate to the central plaza, 94 minutes from the south gate to the palace forecourt, and 7 minutes from Ciaran's entrance to the elder's tree. Fatigue and later authored slope/bend geometry increase these estimates.

### 10.3 Gate approaches and footprints

Rasterize the irregular urban footprint at the new wilderness scale from physical settlement geometry. Do not retain the old rectangular cell counts or multiply their area by another arbitrary factor. Bind actual south/east capital gates and Ciaran's hidden path to their meter-space entrance locations and valid exterior approaches. A gate crossing charges the physical approach segment, not an automatic full wilderness step plus another city step for the same distance.

The coarse footprint is a wilderness routing mask, not a replacement for exact gate geometry. Determine approach cells outside that mask and preserve the intended gate facing. Ciaran's point entrance must not hijack unrelated wilderness movement directions or disclose the hidden village.

### 10.4 Travel-day interpretation

Six actual walking hours is a planning reference, not a daily cap. A healthy party's unreduced road baseline is 27 km per six walking hours. Fatigue decreases that result during a real travel day.

An approximately 1,200 km all-road journey requires approximately 267 healthy walking hours and about 45 six-hour walking days before fatigue, mountains, detours, and rest logistics. The accepted cross-country scale is on the order of 50 game days. Do not relocate cities or alter speeds to force an exact 50-day result.

Pure walking hours do not include unperformed sleep or rests. The player explicitly performs sleep, waiting, and other actions; the companion design provides incentives and eventual physiological failure instead of a hard daily mileage limit.

The existing flight-skill wilderness time waiver remains an explicit exception. This design neither invents flight speeds nor removes that skill rule.

## 11. Architecture and clean cutover

Keep lore and geographic declarations frozen/read-only. Persistent room/instance lifecycle remains owned by `world/maps`; movement eligibility, resource effects, time and atomic action settlement remain in the deterministic rules core. No AI module writes coordinates, fatigue, or movement outcomes.

Replace dense ASCII as the settlement authoring source with sparse meter-coordinate nodes and explicit roads. Reuse XYZRoom/XYZExit storage where appropriate; integer coordinate tags can represent the proposed values. Route finding must use the sparse graph rather than allocating a meter-sized lattice. Remove obsolete ASCII-dependent source paths and tests when their owning cutover lands; do not maintain two competing authoritative maps.

Update all coordinate consumers together: anchor placement, wilderness entries, Limbo bridges, settlement-place street coordinates, scene-image indices, services and any NPC/quest references, node IDs, map knowledge, pathfinding, and local-map transport. Coordinates embedded in persistent identity require a deterministic in-place synchronization cutover preserving room dbids, occupants, and references. Do not let the old missing-node deletion behavior delete and recreate occupied rooms. No general compatibility aliases or Django schema migrations are implied.

Local-map protocol bounds must accept the new physical coordinates and wilderness frame. Rendering uses a viewport projection, pan and zoom that preserve relative physical spacing. Remove rank compression as a substitute for metric geometry; viewport scaling may compress the entire map uniformly, never independently equalize gaps between rows or columns. Keep server coordinates authoritative and display coordinates presentation-only.

Wilderness lookup remains virtual/on demand. Do not scan or materialize all 7.29 million cells for an ordinary move. Geographic masks, sparse roads, footprint and gateway indices must support bounded local lookup. This design does not implement continent-wide route search.

## 12. Movement failure and interruption

Validate destination, traversability, party eligibility, and costs before writes. Commit location, followers, clock, mental changes, map knowledge and owning effects atomically through movement settlement; a fault restores every touched member and location.

A member already in forced sleep refuses departure without time advance. A pending traversal predicted to exhaust a member's mental reserve before its destination is refused before writes, with a clear reason; never land the party past a physiological limit or charge an unperformed full segment. The player can sleep voluntarily first. Do not invent a partly traversed unnamed room to evade this rule. Exactly reaching zero at the destination is permitted, then forced sleep and the party travel block apply there. Interruptible noncombat waits and sleep may instead stop at a forced-sleep boundary under the companion design.

This predictable edge-admission rule is a representation constraint of sparse named-node maps, not a daily travel quota. It must account for fatigue speed changes rather than using an incorrect initial-speed estimate. It is an additional technical design choice for written-spec review: with little reserve left, the party must sleep at the current named node rather than collapse at an unrepresented point along a long road.

Indivisible nonmovement actions use their complete accepted time cost and settle depletion at completion, as defined in the companion design. Do not truncate their time while retaining completed effects. Interruptible waits and sleep instead stop at their defined event boundaries.

## 13. Verification and acceptance

Implementation acceptance includes the following consumer-visible scenarios:

- Actual room synchronization preserves occupant/reference identity while changing the authored outdoor coordinates; a later startup is idempotent.
- All nine canonical anchors and six reserved port sites remain on land; the three elven sites satisfy their east/west/north mountain relationships and remain subject to knowledge visibility.
- Existing settlement connectivity, cycles and compass directions survive; a path with unequal segment lengths displays and charges unequal distances.
- A 100 m healthy settlement segment costs 80 seconds; a cardinal 1 km healthy road segment costs 800 seconds; its diagonal costs 1,132 seconds. Terrain and the slowest member affect the real cost.
- Fatigue crossing a threshold inside a long segment changes only the remaining segment's speed; exhausting a member before the next node refuses with zero writes/time.
- A gate approach is charged once across the scale boundary. A hidden point entrance does not block or redirect every neighboring wilderness route.
- New local coordinates survive wire validation and actual map rendering without rank-equalized spacing. Verify the actual client surface in the implementation change.
- A sleeping member in any posture blocks all party exits; possession cannot move the sleeping body through an exit.
- Inject a failure after follower/location or mental writes and prove durable and cached state rolls back with the clock.

The design research verified polygon arithmetic, land-side anchor/port centers, 31 distinct settlement node positions, and compass octants for 35 roads. These calculations and the parser probe are design evidence, not a claim of implemented movement or browser verification.

## 14. Alternatives and evidence

Keeping 10 km wilderness cells makes a step cover too much local activity and inflates settlement footprints. A 500 m wilderness scale doubles pure movement steps with little benefit for this intercity map. One-kilometer cells are the selected compromise. Meter-scale wilderness is rejected.

Uniform multiplication of the old settlement graph keeps its rectangular alignments. Unequal meter-space placement preserves connectivity while changing the physical layout. Dense meter ASCII is rejected in favor of sparse node/road authoring.

Historical military daily rates informed the initial investigation, but the user replaced army calibration with an equipped small adventuring party. The final speed table is a design choice, not a claim that every medieval party had the same speed.

- [Planning and following a route | Mountaineering Scotland](https://www.mountaineering.scot/safety-and-skills/essential-skills/navigation/planning-and-following-a-route) discusses 4 km/h route estimation, alternative speeds, slope, load, and conditions. It supports separating moving speed from elapsed itinerary time.
- [Population-Area Relationship for Medieval European Cities](https://pmc.ncbi.nlm.nih.gov/articles/PMC5051806/) supports treating population, city area, urban history, and walls together, without imposing one universal density on every settlement.
- [The Organisation and Support of an Expeditionary Force: Manpower and Logistics in the Middle Byzantine Period](https://deremilitari.org/2014/05/the-organisation-and-support-of-an-expeditionary-force-manpower-and-logistics-in-the-middle-byzantine-period/) supplies a historical logistics comparison; its army rates do not define the final small-party baseline.

## 15. Delivery boundary

This is a design specification. Implementation requires scoped OpenSpec changes that update the affected current capabilities and their behavior evidence together. Coordinate/rendering cutover and fatigue integration have separate ownership boundaries and must share the units, speed and forced-sleep contract above. Do not ship the meter-coordinate cutover while a consumer still assumes old unit hops. Do not add transport to shorten accepted geographic distances.

## 16. Proposed changes

This design is decomposed into seven dependency-ordered OpenSpec changes. Each is sized to about one workday, was validated with `openspec validate <change> --strict`, and records the exact branch and worktree its implementation worker must use. All are committed on the primary branch; none is implemented.

| Change | Commit | Scope | Tasks |
| --- | --- | --- | ---: |
| `establish-continental-geography` | `787f921e` | Frozen mainland polygon, demographics, nine anchor cells, six harbor sites and coordinate-unit contracts | 13 |
| `implement-sparse-settlement-graphs` | `343239be` | Sparse graph synchronization, route handling and deterministic in-place room identity binding | 13 |
| `project-metric-local-maps` | `833b40bb` | Expanded coordinate transport and uniform physical viewport projection with pan/zoom | 16 |
| `charge-distance-based-travel` | `94ee6ae5` | Physical-edge terrain charging, slowest-member speed, diagonal legality and charge-once approaches | 16 |
| `integrate-fatigue-aware-traversal` | `cf7b3a83` | External fatigue integration, piecewise prediction, pre-destination depletion refusal and atomic rollback | 15 |
| `rescale-wilderness-geography` | `4e02ed96` | Virtual 2700 by 2700 one-kilometer wilderness, mainland validity, terrain relationships and physical gateways | 15 |
| `activate-metric-settlements` | `bef9bced` | Exact 31-node coordinate cutover and identity, reference and knowledge consumer convergence | 21 |

The implementation worker is **luna** for every change, using `feat/<change-slug>` on branch and `.worktrees/<change-slug>` as worktree.

### 16.1 Cross-batch dependency on the fatigue design

`integrate-fatigue-aware-traversal` consumes the fatigue API that the companion design owns. During planning it carried the unresolved token `external:party-fatigue-and-sleep` until the companion batch existed. The companion batch has now landed, and the token was replaced with **`settle-terminal-combat-fatigue`** in `openspec/changes/integrate-fatigue-aware-traversal/proposal.md` and in every matrix row that quoted it (`integrate-fatigue-aware-traversal`, `rescale-wilderness-geography`, `activate-metric-settlements`).

That change transitively requires every component of the companion batch, so the single replacement preserves a full-design scheduling barrier and introduces no dependency cycle. Substituting a narrower fatigue change would have let traversal integrate against a partially landed physiology contract.

## 17. Parallel implementation order

Dependency-correct waves below. A wave may run concurrently only where the changes touch disjoint code surfaces; where two changes declare overlapping files they serialize even inside one wave. With one worker, execute the waves in order.

| Wave | Changes | Workers | Basis |
| --- | --- | ---: | --- |
| 1 | `establish-continental-geography`, `implement-sparse-settlement-graphs`, `establish-mental-reserve-core` | 3 | No prerequisites; lore declarations, map/grid storage and the new reserve module are disjoint |
| 2 | `project-metric-local-maps`, `charge-distance-based-travel`, `project-physiological-fatigue` | 3 | Wave 1 prerequisites satisfied; protocol/client, movement rules and buff projection are disjoint |
| 3 | `settle-party-sleep-and-wait`, `integrate-sleeping-combat-rosters` | 2 | Clock/skip orchestration and combat roster/AI surfaces are disjoint |
| 4 | `handoff-sleeping-party-control` | 1 | Declares conflicts with the sleep adapters and combat authority landed in wave 3 |
| 5 | `settle-terminal-combat-fatigue` | 1 | Needs wave 3 combat rosters and wave 4 handoff post-commit routing |
| 6 | `integrate-fatigue-aware-traversal` | 1 | Needs the fatigue API (wave 5) plus wave 2 charging; shares clock and movement surfaces with wave 3 |
| 7 | `rescale-wilderness-geography` | 1 | Needs geography, projection, charging, fatigue traversal and sparse graphs |
| 8 | `activate-metric-settlements` | 1 | Needs all six preceding map changes |

The critical path runs through `charge-distance-based-travel` to `integrate-fatigue-aware-traversal`, then `rescale-wilderness-geography` and `activate-metric-settlements`. Wave 1 and wave 2 hold the only real parallelism, at three workers; the map batch then serializes because every remaining change declares shared bootstrap, exit, geometry, map-identity or client surfaces.

`activate-metric-settlements` is the last change in both batches' order: it relocates the authored settlement coordinates, so it must not land while any consumer still assumes unit hops or a pre-fatigue traversal contract.
