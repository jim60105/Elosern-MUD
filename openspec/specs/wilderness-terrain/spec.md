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

#### Scenario: The selected variant is authored data, never a copied literal
- **WHEN** `terrain_description(x, y)` is called for any in-frame coordinate
- **THEN** the returned string is the continent source's own declared variant at the fixed formula's
  index, never a second approval table or a test-side copy

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

### Requirement: The border river controls western crossing and classification
A border river SHALL follow `WATERWAY_ROUTES["border_river"]` from the central range's west flank to the west coast. It SHALL separate western hills/valleys from northwest highland forest and SHALL be impassable on foot except at the fords declared in `WATERWAY_FORDS["border_river"]`.

#### Scenario: Fords permit travel across the new border
- **WHEN** ordinary foot movement crosses a river cell and then a declared ford
- **THEN** the river cell blocks traversal and the ford permits it; west of the river source the two banks beside a declared ford connect only through declared fords, and any single declared ford suffices

#### Scenario: Region consumers follow the amended boundaries
- **WHEN** region-keyed monster placement and species-hunt destination resolution consume cells on either side of the new river and forest edge
- **THEN** they agree with the amended classifier without unknown region keys or stale rectangular-boundary assumptions

### Requirement: The physical ridge is a continuous forked barrier
The physical ridge SHALL derive from arbitrary authored stem and arm routes joined without a crotch gap, expose complete wall geometry to traversal, previews and partition alongside active crest-centre elevation profiles, and retain separate arm spans ending inside the forest.

#### Scenario: Deterministic arm bends and crotch
- **WHEN** paired northward authored routes with arbitrary non-periodic local bends join the stem's last active row
- **THEN** each arm has deterministic row centres with next-row span closure; the shared crotch is blocked, adjacent rows have no corner-cutting crossing, and the open space between separated arms is not filled

#### Scenario: Arbitrary physical stem replaces periodic generation
- **WHEN** a synthetic stem authors unequal bend spacing and local direction changes
- **THEN** blockers, previews, corridor, claims, political lines and elevation derive from the same authored route with repeatable rasterization, never a periodic curve or separate reference axis; the fork joins its endpoint

#### Scenario: Invalid geometric relations
- **WHEN** a fork has mismatched starts, nonincreasing rows, crossed or rejoined arms beyond the crotch, wrongly sided tips, excessive per-row slope, a crotch pass, off-frame/off-land/non-forest arm cells, or collisions with full waterway cells or authored protected points
- **THEN** candidate authoring reports a semantic terrain diagnostic and runtime rejects that candidate without moving protected content

#### Scenario: All physical consumers agree
- **WHEN** a forked ridge is consumed by validity, row-run component indexing, preview/capture, elevation and partition
- **THEN** complete wall spans block validity/components/partition and appear in previews regardless of the stem's X extent; elevation uses all active crest-centre profiles and maximum overlapping rise before unchanged sea/river clamps and ordered shapes

#### Scenario: No direct cross-range land route
- **WHEN** every active stem row of the shipped ridge outside its declared pass rows is probed at the stem centre, and each arm tip and the cell north of it are probed
- **THEN** each probed centre is a closed wall cell that the game's validity rule rejects, and each tip is closed while the cell north of it is open

#### Scenario: Terminal rows and optional passes
- **WHEN** a synthetic stem pass is added below the crotch or a crest endpoint is queried
- **THEN** the pass exempts only its stem rows, both arms remain blocked, the last crest row is included and the following row has no wall from that crest

### Requirement: The coordinate classifier is a pure deterministic function over the whole bounded map
The coordinate classifier SHALL return a declared region for every bounded coordinate using only its immutable terrain snapshot, with deterministic results and the mountain corridor derived from the authored stem route without arm corridors.

#### Scenario: Same input always returns the same output
- **WHEN** the classifier is called twice with the same coordinate and snapshot
- **THEN** both calls return the identical declared region key without database, network, random or clock input

#### Scenario: Every region key is reachable
- **WHEN** the classifier is evaluated across the valid coordinate range
- **THEN** every declared region key is returned by at least one coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** cells around the authored stem corridor below the forest are classified
- **THEN** the mountain region follows the stem's per-row centre and authored half-width, while physical passability remains a separate cell property

#### Scenario: Branches leave regions unchanged
- **WHEN** synthetic terrain definitions retain their authored stem and differ only in paired arm routes
- **THEN** every frame cell keeps its region and the region search windows are identical; branch cells in the deep forest remain north_deep_forest

### Requirement: Terrain and political control derive from authored geography
Terrain, nominal claims and effective control SHALL remain distinct, with the corridor, nominal nation splits and political lines derived from the same authored stem, walkable deep forest beyond the arm tips, and every authored location and harbour on walkable land in one connected component; no individual site's position, region or nation and no measured area share is contract.

#### Scenario: Authored sites stay classified, walkable and connected
- **WHEN** the shipped terrain is evaluated through every authored location and harbour identity
- **THEN** each location cell classifies into a declared region, and each location target (legal gateway approaches for footprinted anchors) and each harbour is walkable land in one four-connected component, whatever the roster size or positions

#### Scenario: Nominal claims agree with region declarations
- **WHEN** land is sampled across the stem and border river
- **THEN** each cell has exactly one nominal nation drawn from its region's declared nominal nations, every declared nominal nation of a region occurs in that region, and a region with an administrative nation claims only that nation; measured shares are authored outcomes, not contract

#### Scenario: Declared fords are land on their own waterway
- **WHEN** every waterway's declared fords and rasterized route cells are consumed
- **THEN** each ford lies on its own route and is walkable land, and every other land cell of any route is impassable inland water

#### Scenario: Forest beyond the arm tips stays walkable
- **WHEN** the row past the stem's crotch and the row north of each authored arm tip are evaluated
- **THEN** the stem has no span past its crotch, and each cell north of a tip is walkable north_deep_forest with no closed wall

#### Scenario: Political lines remain on the stem
- **WHEN** a synthetic stem route changes and paired arms are consumed
- **THEN** the corridor and nominal nation flip follow its row centres, political borders equal its clipped authored polyline and river-source junction, and neither arm nor deep-forest political segments appear

#### Scenario: River-source junction agrees with nominal claims
- **WHEN** a candidate's border river starts at its easternmost vertex and its active stem stays strictly east of that source
- **THEN** the source-row political junction agrees with the nominal west-neighbour nation transition; candidates violating either relation reject semantically instead of displaying contradictory political labels
