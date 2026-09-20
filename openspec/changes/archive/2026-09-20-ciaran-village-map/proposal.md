## Why

The world has one walkable settlement. `world/maps/altoria_capital.py` is the
only map module, `CITY_GATE_REGISTRY` and `ANCHOR_PLACEMENT_REGISTRY` and
`WILDERNESS_ENTRY_REGISTRY` each hold exactly one row, and every one of those
rows is `capital_altoria`.

That makes every settlement-shaped abstraction unproven. A place registry
keyed by settlement, a settlement archetype vocabulary, a per-settlement
coordinate space — none of them has ever resolved against a second entry, so
none of them is known to work.

暗影谷村 is the right second settlement, and the data already expects it.
`world/lore/races.py:216` ships the `ciaran` subrace with
`native_anchor="village_ciaran"`, and `ANCHOR_REGISTRY` already carries
`village_ciaran` — but no map, no placement, and no way in. A playable elf
preset exists with nowhere to come from.

It is also the hardest archetype, which is why it is worth building second
rather than last. `docs/lore/settlement-locations.md:490` sets a deliberate
floor for it: 「玩家必須能像在人類的城鎮一樣在精靈村落裡買賣、補給、休息，而不是走進一座
只能觀賞的空景。」 An elven village has no guild, no temple, no bathhouse, no
walls and no shops — and must still be fully playable. If the settlement
abstractions survive that, the remaining four archetypes are interpolation.

## What Changes

- Add `world/maps/village_ciaran.py`: a six-node tree for 暗影谷村 — 隱密小徑
  as the way in, 村中廣場 as the settlement's `AnchorRoom`, 練刀場 reflecting
  the branch's swordsmanship culture, and three further exteriors
  (溪畔小徑, 村北古樹下, 織房坡) for dwellings a later change attaches.
  Intra-village links spawn as `CostedXYZExit` exactly as the capital's do.
- Register the village in the three geography registries, each of which
  currently pins itself to a single row: `ANCHOR_PLACEMENT_REGISTRY`,
  `WILDERNESS_ENTRY_REGISTRY` (a footprint clear of the capital's) and
  `CITY_GATE_REGISTRY`.
- **BREAKING** (spec-level): three requirements that assert their registry
  holds exactly one entry, and one that calls `capital_altoria` "the sole
  row", become statements about two settlements.
- The village **is** reachable from 虛境. `world/maps/city_gates.py:10`
  records that race-based gate selection is out of scope, so every new
  character will see both the capital's 南門 and the village's 隱密小徑.
  That is accepted: the game ships a playable elf preset, and an elf with no
  elven settlement to start from is the worse outcome. Gating the hidden
  village by race is left open.
- The way in is 隱密小徑, not a gate. `docs/lore/settlement-locations.md:420`
  is explicit that elven villages have no walls and no city gates — the
  forest's concealment is the defence — so the node is named and described
  as a concealed path even though it occupies the registry slot a city gate
  would.

## Capabilities

### New Capabilities

- `village-ciaran-map`: the village's grid topology, its anchor room, its
  single concealed entrance, and its wilderness footprint.

### Modified Capabilities

- `limbo-one-way-gates`: the city-gate registry requirement pins itself to
  exactly one row; it becomes two, and the one-way and exclusive-authorship
  guarantees extend to both.
- `anchor-placement`: the partial-registry requirement states this registry
  holds exactly one entry; it becomes two.
- `wilderness-gateway`: the entry-registry requirement states it holds
  exactly one entry; it becomes two, and the existing global gate-uniqueness
  and footprint-disjointness rules now have something to check.
- `sample-city-altoria`: the bridging-exit requirement calls
  `capital_altoria` the sole `CITY_GATE_REGISTRY` row. The capital's own
  guarantees are unchanged; the claim of sole-ness is not.

## Impact

- `world/maps/village_ciaran.py` — new map module.
- `world/maps/` — a shared assembly exporting both maps' data. `XYMAP_DATA_LIST`
  is defined in `world/maps/altoria_capital.py` and merely imported by
  `world/maps/bootstrap.py:19`, `world/lore/wilderness_entry.py:180` (deferred)
  and `world/quests/definitions.py:16` (through which `KNOWN_GRID_MAP_KEYS`
  grows the village's map key), so "add a map" is an assembly edit, not an
  append to a list literal in bootstrap.
- `world/lore/wilderness_entry.py` — **two** edits, not one. Besides the new
  registry row, `_iter_map_extents()` (line 180) has its **own** deferred
  `from world.maps.altoria_capital import XYMAP_DATA_LIST`, independent of
  bootstrap's. `validate_wilderness_entries()` runs from `sync_all()` at every
  startup and rejects a gate whose `z_map_key` names no known map, so leaving
  this import pointed at the capital alone makes the village's gate fail
  validation and takes the whole lore load down with it. It must read the
  shared assembly.
- `world/lore/anchor_placement.py`, `world/lore/wilderness_entry.py`,
  `world/maps/city_gates.py` — one row each.
- `world/maps/tests/`, `world/lore/tests/` — two-settlement coverage of
  topology, gate exclusivity and footprint disjointness.
- No commerce, place, host or item change. The village is walkable and
  empty; `ciaran-village-commerce` furnishes it.
- **Independent of `commerce-assortment-registry`, `place-price-scaling`
  and `masterwork-gear-price-band`** — disjoint files, any order.
- **Conflicts with `settlement-place-registry`** on
  `world/maps/bootstrap.py`. Land this one first: here the edit is the map
  assembly at the top of the file, while that change rewrites the interior
  function.
