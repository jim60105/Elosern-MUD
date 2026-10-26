## Purpose

The deterministic, offline-computable terrain model for the wilderness/Virtual map layer, with the declared
named terrain regions of the continent, a pure coordinate-to-region partition, and a pure
coordinate-to-description arithmetic formula, with no LLM, no database read, no randomness, no wall-clock
input. These functions satisfy the design doc's offline-playability criterion at the map layer.

## Requirements

### Requirement: WILDERNESS_REGION_REGISTRY covers the authored terrain regions
`world/lore/wilderness_regions.py` SHALL define a frozen `WildernessRegion` dataclass of exactly
these fields:

```
WildernessRegion(
    key: str,
    display_name_zh: str,
    nation_key: str | None,
    terrain_flavor_zh: tuple[str, ...],   # at least two entries
    nominal_nation_keys: tuple[str, ...],
)
```

It SHALL define a module-level `WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion]` with one
entry per authored terrain region, using the registry's Traditional Chinese display names.
`nation_key` SHALL be `None` for regions shared across nominal borders; `nominal_nation_keys` SHALL
list their claimants, while the provider resolves each cell's claim.

#### Scenario: The registry covers the declared regions without duplicate names
- **WHEN** `WILDERNESS_REGION_REGISTRY` is inspected
- **THEN** it contains the declared region set, and every entry has a distinct authored `display_name_zh`

#### Scenario: Every region carries at least two description variants
- **WHEN** every entry in `WILDERNESS_REGION_REGISTRY` is inspected
- **THEN** each entry's `terrain_flavor_zh` tuple has at least two elements

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
`world/maps/wilderness_provider.py` SHALL define `region_for_coordinates(x: int, y: int) -> str`,
returning a key that exists in `WILDERNESS_REGION_REGISTRY`, for every `(x, y)` pair within the
map's valid coordinate bounds. The function SHALL read no database state, no network state, and no
random or wall-clock input, and SHALL return the same value for the same input on every call.

#### Scenario: Same input always returns the same output
- **WHEN** `region_for_coordinates(x, y)` is called twice with the same `(x, y)` in the same process
- **THEN** both calls return the identical string

#### Scenario: Every region key is reachable
- **WHEN** `region_for_coordinates` is evaluated across the full valid coordinate range
- **THEN** every key in `WILDERNESS_REGION_REGISTRY` is returned by at least one
  coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** `region_for_coordinates(x, y)` is evaluated around X1310..1510 below the northern forest
- **THEN** the mountain region follows the authored bending corridor (its centre shifts per row)
  instead of a fixed rectangular band, and it is never a continuous summit wall: the closed ridge
  is a one-cell cliff wall broken only at the authored passes

#### Scenario: capital_altoria's derived anchor cells resolve to Altoria's own territory
- **WHEN** `region_for_coordinates` is called with the `"capital_altoria"` entry's derived
  `anchor_cell` `(860, 1080)` and with every gate's derived `approach_cell` (`(860, 1077)` and
  `(864, 1080)`)
- **THEN** every call returns `"western_hills_valleys"`, matching `world/lore/nations.py`'s own
  statement that Altoria's territory is "西部丘陵、谷地與西南海岸"

### Requirement: terrain_description is a pure, deterministic function with no LLM or randomness
`world/maps/wilderness_provider.py` SHALL define `terrain_description(x: int, y: int) -> str`,
selecting one of `region_for_coordinates(x, y)`'s region's `terrain_flavor_zh` variants via the fixed
arithmetic formula `index = (x * 92821 + y * 68917) % len(variants)` over `(x, y)` alone. The function
SHALL call no LLM client, no random-number generator, and no wall-clock read, satisfying the design
doc's offline-playability criterion.

#### Scenario: Same coordinates always produce the same description
- **WHEN** `terrain_description(x, y)` is called twice with the same `(x, y)`
- **THEN** both calls return the identical string, including across separate process invocations
  (same input, same output, with no persisted state required to reproduce it)

#### Scenario: The description matches the coordinate's region
- **WHEN** `terrain_description(x, y)` is called
- **THEN** the returned string is one of `WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].
  terrain_flavor_zh`'s own variants

#### Scenario: A fixed coordinate produces a literal, spec-pinned string
- **WHEN** `terrain_description(860, 1080)` is called (the `capital_altoria` anchor cell, which
  `region_for_coordinates` resolves to `"western_hills_valleys"`)
- **THEN** it returns exactly `"低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。"`, the literal third
  (index `2`) entry of `WILDERNESS_REGION_REGISTRY["western_hills_valleys"].terrain_flavor_zh`, per
  `(860 * 92821 + 1080 * 68917) % 3 == 2`. A reimplementation using different formula constants or
  reworded flavor text (either of which would still satisfy every other scenario in this
  requirement) SHALL fail this scenario, which pins the formula and the
  registry text together against silent drift, the same concern that ruled out a `hash()`-based
  formula in this capability's own design rationale

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

#### Scenario: The constants and flavor text are contract, not discretion
- **WHEN** the formula's constants (`92821`, `68917`) and `WILDERNESS_REGION_REGISTRY`'s exact `terrain_flavor_zh` text are weighed
- **THEN** both are part of this requirement's contract, as defined by the literal-pin scenario

### Requirement: WILDERNESS_REGION_REGISTRY is mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::_ALL_REGISTRIES` SHALL include `WILDERNESS_REGION_REGISTRY` under the category
key `"wilderness_regions"`, so `sync_all()` mirrors it into `LoreRecord` Scripts exactly as it mirrors
every other lore registry, including idempotency across repeated calls.

#### Scenario: sync_all mirrors wilderness regions
- **WHEN** `sync_all()` runs
- **THEN** a `LoreRecord` Script exists for each declared region key, keyed
  `"lore:wilderness_regions:<key>"`, with `db.fields` matching the corresponding
  `WildernessRegion` entry

#### Scenario: Repeated sync creates no duplicate region records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly one `LoreRecord` Script per declared region key exists under the `"wilderness_regions"` category after the second call

### Requirement: Terrain and political control follow authored geography
Terrain, nominal claims and effective control SHALL remain distinct. The deep forest's southern edge SHALL meander around Y1920 and keep ordinary forest travel speed. Every land cell SHALL have nominal Grandia east of the ridge, Altoria west and south of the border river, or Valhalla west and north, with stable region keys. Displayed borders SHALL derive from the ridge and river and be omitted inside deep forest; effective-rule demographic targets SHALL remain unchanged.

#### Scenario: Anchor relationships
- **WHEN** the amended geography is evaluated
- **THEN** 咆哮王城 at (780,1910) is about 10 km south of the forest edge, 幽月谷村 at (1410,2150) and 永夜迷宮 at (900,2350) lie in deep forest, and all declared anchors and harbour sites remain on land and reachable; Altoria remains southwest in hills/river valleys, Valhalla northwest, Grandia eastern productive plains, Ciaran underground on the western flank and Fionnen on the eastern flank

#### Scenario: Nominal claims include previously neutral terrain
- **WHEN** land on either side of the ridge and border river is classified, including mountain and deep-forest cells
- **THEN** each cell has exactly one nominal nation, the approximate land shares are Grandia 43%, Altoria 30%, Valhalla 27%, elven valleys remain administratively independent in narrative, and the map adds no nominal-versus-effective display distinction

#### Scenario: Pass and river constraints
- **WHEN** the geography is amended
- **THEN** the one-cell summit ridge retains its declared passes and northern limit, the southwest capital river and southeastern imperial network remain, and no elevation or shipping gameplay is introduced

### Requirement: The border river controls western crossing and classification
A border river SHALL follow `WATERWAY_ROUTES["border_river"]` from the central range's west flank to the west coast. It SHALL separate western hills/valleys from northwest highland forest and SHALL be impassable on foot except at the fords declared in `WATERWAY_FORDS["border_river"]`.

#### Scenario: Fords permit travel across the new border
- **WHEN** ordinary foot movement crosses a river cell and then a declared ford
- **THEN** the river cell blocks traversal and the ford permits it, with a route from Altoria's capital to Valhalla's capital remaining possible

#### Scenario: Region consumers follow the amended boundaries
- **WHEN** region-keyed monster placement and species-hunt destination resolution consume cells on either side of the new river and forest edge
- **THEN** they agree with the amended classifier without unknown region keys or stale rectangular-boundary assumptions
