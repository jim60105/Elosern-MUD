## REMOVED Requirements

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
**Reason**: Its scenario "capital_altoria's derived anchor cells resolve to Altoria's own territory" pins one authored site's region; OpenSpec cannot drop a scenario under MODIFIED.
**Migration**: Replaced by "The coordinate classifier is a pure deterministic function over the whole bounded map" below with the remaining scenarios unchanged; tests change their `covers_requirement` ID to `wilderness-terrain::the-coordinate-classifier-is-a-pure-deterministic-function-over-the-whole-bounded-map`.

### Requirement: Terrain and political control follow authored geography
**Reason**: Its scenarios pin authored map data: named sites' regions, flanks and distance to the forest edge, nominal and forest area shares, a zero-pass range with unchanged waterways, hidden-valley clearance distances and a 9-location / 6-harbour roster that commit 1bf6e0ad already invalidated.
**Migration**: Replaced by "Terrain and political control derive from authored geography" below, which keeps the derived invariants (classification, walkability, connectivity, claim/region agreement, ford and river-cell semantics, political-line derivation); tests change their `covers_requirement` ID to `wilderness-terrain::terrain-and-political-control-derive-from-authored-geography`.

## ADDED Requirements

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
Terrain, nominal claims and effective control SHALL remain distinct, with the corridor, nominal nation splits and political lines derived from the same authored stem, deep forest walkable off the ridge, and every authored location and harbour on walkable land in one connected component; no individual site's position, region or nation and no measured area share is contract.

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

## MODIFIED Requirements

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
- **THEN** each probed centre is a closed wall cell for the game's validity rule, each tip is closed and the cell north of it is open, so unrestricted travel crosses the range only through declared passes or the forest beyond the tips

#### Scenario: Terminal rows and optional passes
- **WHEN** a synthetic stem pass is added below the crotch or a crest endpoint is queried
- **THEN** the pass exempts only its stem rows, both arms remain blocked, the last crest row is included and the following row has no wall from that crest
