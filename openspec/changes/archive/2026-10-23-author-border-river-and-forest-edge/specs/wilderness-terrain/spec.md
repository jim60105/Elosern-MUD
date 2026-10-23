# Spec Delta

## MODIFIED Requirements

### Requirement: Terrain and political control follow authored geography
Terrain, nominal claims and effective control SHALL remain distinct. The deep forest's southern edge SHALL meander around Y1920 and keep ordinary forest travel speed. Every land cell SHALL have nominal Grandia east of the ridge, Altoria west and south of the border river, or Valhalla west and north, with stable region keys. Displayed borders SHALL derive from the ridge and river and be omitted inside deep forest; effective-rule demographic targets SHALL remain unchanged.

#### Scenario: Anchor relationships
- **WHEN** the amended geography is evaluated
- **THEN** 咆哮王城 at (780,1910) is about 10 km south of the forest edge, 幽月谷村 at (1410,2150) and 永夜迷宮 at (900,2350) lie in deep forest, and all nine anchors and six harbour sites remain on land and reachable; Altoria remains southwest in hills/river valleys, Valhalla northwest, Grandia eastern productive plains, Ciaran underground on the western flank and Fionnen on the eastern flank

#### Scenario: Nominal claims include previously neutral terrain
- **WHEN** land on either side of the ridge and border river is classified, including mountain and deep-forest cells
- **THEN** each cell has exactly one nominal nation, the approximate land shares are Grandia 43%, Altoria 30%, Valhalla 27%, elven valleys remain administratively independent in narrative, and the map adds no nominal-versus-effective display distinction

#### Scenario: Pass and river constraints
- **WHEN** the geography is amended
- **THEN** the one-cell summit ridge retains its three passes and northern limit, the southwest capital river and southeastern imperial network remain, and no elevation or shipping gameplay is introduced

## ADDED Requirements

### Requirement: The border river controls western crossing and classification
A border river SHALL rise near (1300,1410) on the central range's west flank and reach the west coast near (170,1290), meandering within Y1290..1410 through the vicinity of (1100,1350), (900,1380), (650,1310), and (400,1340). It SHALL separate western hills/valleys from northwest highland forest and SHALL be impassable on foot except at exactly three fords, with the principal ford near (830,1370), one upstream and one downstream.

#### Scenario: Fords permit travel across the new border
- **WHEN** ordinary foot movement crosses a river cell and then a declared ford
- **THEN** the river cell blocks traversal and the ford permits it, with a route from Altoria's capital to Valhalla's capital remaining possible

#### Scenario: Region consumers follow the amended boundaries
- **WHEN** region-keyed monster placement and species-hunt destination resolution consume cells on either side of the new river and forest edge
- **THEN** they agree with the amended classifier without unknown region keys or stale rectangular-boundary assumptions
