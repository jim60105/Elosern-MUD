## Purpose

The deterministic, offline-computable terrain model for the wilderness/Virtual map layer, with the declared
named terrain regions of the continent, a pure coordinate-to-region partition, and a pure
coordinate-to-description arithmetic formula, with no LLM, no database read, no randomness, no wall-clock
input. These functions satisfy the design doc's offline-playability criterion at the map layer.

## Requirements

### Requirement: WILDERNESS_REGION_REGISTRY covers the authored terrain regions
Game terrain views SHALL expose immutable schema-valid region values loaded from the continent source, with every classifier result resolving to a declared region.

#### Scenario: Complete region references
- **WHEN** a synthetic continent classifier returns a missing region or a region lacks required typed prose
- **THEN** the candidate is rejected before replacing published terrain values

#### Scenario: Round-trip derived view
- **WHEN** a supported region document is loaded twice and mirrored by lore synchronization
- **THEN** both reads are immutable and synchronization remains idempotent

#### Scenario: The registry covers the declared regions without duplicate names
- **WHEN** a synthetic continent supplies region declarations and classifier references
- **THEN** every classifier target resolves, identities/display names satisfy the existing uniqueness rule and duplicate declarations reject

#### Scenario: Every region carries at least two description variants
- **WHEN** a region has fewer than two typed nonblank description variants
- **THEN** authoring validation rejects that region rather than coercing or fabricating prose

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
`world/maps/wilderness_provider.py` SHALL define `region_for_coordinates(x: int, y: int) -> str`,
returning a key that exists in the published region views, for every `(x, y)` pair within the
map's valid coordinate bounds. The function SHALL read the published snapshot's explicit terrain
definition, no database state, no network state, and no random or wall-clock input, and SHALL
return the same value for the same input on every call.

#### Scenario: Same input always returns the same output
- **WHEN** `region_for_coordinates(x, y)` is called twice with the same `(x, y)` in the same process
- **THEN** both calls return the identical string

#### Scenario: Every region key is reachable
- **WHEN** `region_for_coordinates` is evaluated across the full valid coordinate range
- **THEN** every declared region key is returned by at least one coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** `region_for_coordinates(x, y)` is evaluated around the declared corridor's X band below
  the northern forest
- **THEN** the mountain region follows the authored bending corridor (its centre shifts per row)
  instead of a fixed rectangular band, and it is never a continuous summit wall: the closed ridge
  is a one-cell cliff wall broken only at the authored passes

#### Scenario: capital_altoria's derived anchor cells resolve to Altoria's own territory
- **WHEN** `region_for_coordinates` is called with `capital_altoria`'s declared cell and with every
  gate's derived `approach_cell`
- **THEN** every call returns `"western_hills_valleys"`, matching `world/lore/nations.py`'s own
  statement that Altoria's territory is "西部丘陵、谷地與西南海岸"

### Requirement: terrain_description is a pure, deterministic function with no LLM or randomness
`world/maps/wilderness_provider.py` SHALL define `terrain_description(x: int, y: int) -> str`,
selecting one of `region_for_coordinates(x, y)`'s region's declared `terrain_flavor_zh` variants via
the fixed arithmetic formula `index = (x * 92821 + y * 68917) % len(variants)` over `(x, y)` alone.
The function SHALL call no LLM client, no random-number generator, and no wall-clock read. The
formula constants remain contract; the prose stays the source declaration, never a copied literal.

#### Scenario: Same coordinates always produce the same description
- **WHEN** `terrain_description(x, y)` is called twice with the same `(x, y)`
- **THEN** both calls return the identical string, including across separate process invocations
  (same input, same output, with no persisted state required to reproduce it)

#### Scenario: The description matches the coordinate's region
- **WHEN** `terrain_description(x, y)` is called
- **THEN** the returned string is one of the published region view's own `terrain_flavor_zh`
  variants at index `(x * 92821 + y * 68917) % len(variants)`, and that region is
  `region_for_coordinates(x, y)`

#### Scenario: A fixed coordinate produces a literal, spec-pinned string
- **WHEN** `terrain_description(860, 1080)` is called (the `capital_altoria` anchor cell, which
  `region_for_coordinates` resolves to `"western_hills_valleys"`)
- **THEN** the fixed formula selects index `2` of that region's declared variants; the literal prose
  is the continent source's own declaration, preserved by the conversion comparison rather than
  copied into a second approval table

#### Scenario: The constants and flavor text are contract, not discretion
- **WHEN** the formula's constants (`92821`, `68917`) and the continent source's
  `terrain_flavor_zh` text are weighed
- **THEN** the formula constants remain this requirement's contract, and the prose remains the
  authored source contract validated by schema, never an implementation or test-side copy

#### Scenario: No LLM or network dependency exists in the call path
- **WHEN** `world/maps/wilderness_provider.py` is inspected for imports and calls
- **THEN** it references no module under `world/ai/`, no HTTP client, and no `random` module call

### Requirement: WILDERNESS_REGION_REGISTRY is mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::sync_all()` SHALL mirror the published geography's composed region views under
the category key `"wilderness_regions"`, so the mirror follows the loaded continent source exactly as
it follows every other lore registry, including idempotency across repeated calls.

#### Scenario: sync_all mirrors wilderness regions
- **WHEN** `sync_all()` runs after geography publication
- **THEN** a `LoreRecord` Script exists for each published region key, keyed
  `"lore:wilderness_regions:<key>"`, with `db.fields` matching the corresponding region view

#### Scenario: Repeated sync creates no duplicate region records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly one `LoreRecord` Script per published region key exists under the
  `"wilderness_regions"` category after the second call

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
