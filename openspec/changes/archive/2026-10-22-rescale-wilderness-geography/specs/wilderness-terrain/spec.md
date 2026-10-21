# Spec Delta

## ADDED Requirements

### Requirement: Terrain and political control follow authored geography
Terrain, nominal claims and actual control SHALL remain separate layers. Central mountains SHALL bend broadly around X1310..1510, northern deep forest begin broadly near Y2200, and the southern coast SHALL support the principal bulk-commerce corridor without adding transport mechanics.

#### Scenario: Anchor relationships
- **WHEN** the geographic layers are inspected
- **THEN** Altoria lies southwest in hills/river valleys, Valhalla northwest highland forest, Grandia eastern productive plains; Ciaran is underground western flank, Fionnen eastern flank and Eolas hidden northern mountain valley.

#### Scenario: Pass and river constraints
- **WHEN** southern mountain crossings and water networks are authored
- **THEN** principal pass near (1410,980) uses explicit slower mountain trail/supply itinerary, never guaranteed all-road shortcut; capital river flows southwest toward kingdom ports and imperial rivers connect eastern plains to southeastern ports; no shipping gameplay appears.

## MODIFIED Requirements

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
- **THEN** every one of the seven keys in `WILDERNESS_REGION_REGISTRY` is returned by at least one
  coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** the authored bending corridor is queried around X1310..1510 below northern forest
- **THEN** mountain, foothill, valley and subsidiary-ridge geography is respected; it is never a
  continuous summit wall or full-frame rectangular band. The region centre follows the authored
  bend per row, the deep forest region starts at Y2200, and the closed summit ridge is a one-cell
  cliff wall broken only at the authored passes.

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
- **WHEN** terrain_description(860,1080) is evaluated in western_hills_valleys
- **THEN** it returns exactly "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。" from (860*92821+1080*68917)%3 == 2, preserving arithmetic constants and existing flavor text.

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

#### Scenario: The constants and flavor text are contract, not discretion
- **WHEN** the formula's constants (`92821`, `68917`) and `WILDERNESS_REGION_REGISTRY`'s exact `terrain_flavor_zh` text are weighed
- **THEN** both are part of this requirement's contract, not implementation detail left to the implementer's discretion — see the literal-pin scenario
