# Spec Delta

## MODIFIED Requirements

### Requirement: region_for_coordinates is a pure, deterministic function covering the whole bounded map
The coordinate classifier SHALL return a declared region for every bounded coordinate using only its immutable terrain snapshot, with deterministic results and the mountain corridor derived solely from the stem reference axis.

#### Scenario: Same input always returns the same output
- **WHEN** the classifier is called twice with the same coordinate and snapshot
- **THEN** both calls return the identical declared region key without database, network, random or clock input

#### Scenario: Every region key is reachable
- **WHEN** the classifier is evaluated across the valid coordinate range
- **THEN** every declared region key is returned by at least one coordinate

#### Scenario: The central mountain band spans the full valid Y range
- **WHEN** cells around the bending stem corridor below the forest are classified
- **THEN** the mountain region follows the authored corridor; the separate physical crest's passability does not define region membership

#### Scenario: capital_altoria's derived anchor cells resolve to Altoria's own territory
- **WHEN** the capital's authored cell and all derived gateway approaches are classified
- **THEN** each remains western_hills_valleys

#### Scenario: Branches leave regions unchanged
- **WHEN** otherwise identical synthetic terrain definitions differ only by paired physical branches
- **THEN** every frame cell keeps its region and the region search windows are identical; branch cells in the deep forest remain north_deep_forest

### Requirement: Terrain and political control follow authored geography
Terrain, nominal claims and effective control SHALL remain distinct, with unchanged stem-derived political lines and region boundaries, a walkable deep forest, and a pass-free forked shipped ridge enclosing the independent hidden valley.

#### Scenario: Anchor relationships
- **WHEN** the shipped terrain is evaluated through its authored location identities
- **THEN** Valhalla remains south of the forest edge, Eolas and Eternal Night remain in deep forest, Ciaran and Fionnen remain on the stem's west/east flanks, and all anchors and harbours remain land-side and reachable

#### Scenario: Nominal claims include previously neutral terrain
- **WHEN** land is classified across the stem and border river
- **THEN** each cell has one nominal nation; sampled shares remain Grandia 0.43, Altoria 0.30 and Valhalla 0.27 within 0.015, with effective-rule targets unchanged and shared regions keeping no administrative nation

#### Scenario: Pass and river constraints
- **WHEN** the shipped ridge and waterway declarations are consumed
- **THEN** no pass exemption exists on the physical range, waterways and their fords remain unchanged, and no movement, elevation-dependent gameplay or shipping rule is introduced

#### Scenario: Hidden valley clearance
- **WHEN** the shipped Eolas location is compared with the physical crest
- **THEN** its row lies between the arms at least 30 km from each inner wall edge, no wall lies within a 20 km Euclidean radius, and Eolas remains north_deep_forest with no administrative nation

#### Scenario: Forest detour and preserved shares
- **WHEN** four-connected walkability excludes sea, complete ridge walls, non-ford water and anchor footprints
- **THEN** all 9 location targets and 6 harbours share one component through forest around the inland tips; footprinted anchors use legal gateway approaches, ordinary forest stays walkable and sampled forest share remains 0.20 within 0.02

#### Scenario: Political lines remain on the stem
- **WHEN** otherwise identical synthetic worlds differ only in physical branches
- **THEN** nominal claims and displayed border point sequences are identical, and political lines continue to omit deep-forest segments

## ADDED Requirements

### Requirement: The physical ridge is a continuous forked barrier
The physical ridge SHALL join its active stem and paired deterministic crest arms without a crotch gap, block their wall cells through every physical consumer, and retain separate arm spans with no wall beyond the inland forest tips.

#### Scenario: Deterministic arm bends and crotch
- **WHEN** paired monotone branch routes join the stem's last active row
- **THEN** each arm has deterministic row centres with next-row span closure; the shared crotch is blocked, adjacent rows have no corner-cutting crossing, and the open space between separated arms is not filled

#### Scenario: Invalid geometric relations
- **WHEN** a fork has mismatched starts, nonincreasing rows, inverted arm direction, excessive per-row slope, a crotch pass, off-frame/off-land/non-forest wall cells, or collisions with full waterway cells or authored protected points
- **THEN** candidate authoring reports a semantic terrain diagnostic and runtime rejects that candidate without moving protected content

#### Scenario: All physical consumers agree
- **WHEN** stem and arm wall cells are passed to validity, row-run component indexing, preview/capture, elevation and partition
- **THEN** validity and components reject them, preview/capture draw them, elevation raises them and partition input marks them blocked, including arms outside a synthetic stem's X bounds

#### Scenario: No direct cross-range land route
- **WHEN** the shipped zero-pass ridge is probed across X1300 through X1520
- **THEN** no active row admits a horizontal land crossing, and no four-connected route joins the band edges while restricted to rows at or south of the highest tip; unrestricted travel can detour north through walkable forest

#### Scenario: Terminal rows and optional passes
- **WHEN** a synthetic stem pass is added below the crotch or a crest endpoint is queried
- **THEN** the pass exempts only its stem rows, both arms remain blocked, the last crest row is included and the following row has no wall from that crest
