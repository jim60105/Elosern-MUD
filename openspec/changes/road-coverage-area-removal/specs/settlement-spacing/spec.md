# Spec Delta

## MODIFIED Requirements

### Requirement: Road coverage bounds the gap between consecutive road settlements
For every road, the validation SHALL treat as settlement positions the road's two ends, every cell on it that is an end of any road, and every village or hamlet cell on it, and SHALL report each pair of consecutive positions whose road length exceeds the configured maximum, counting a diagonal step as the square root of two.

#### Scenario: Gap boundary
- **WHEN** a straight synthetic road has its ends exactly the maximum apart, and a second road is one cell longer
- **THEN** only the second road is reported, naming the road, the two cells and the length

#### Scenario: A hamlet on the road splits a gap
- **WHEN** a hamlet's cell is a cell of the longer road such that both parts are within the maximum
- **THEN** the road is not reported

#### Scenario: A settlement the road passes counts
- **WHEN** the longer road passes through a cell that is the end of another road, such that both parts are within the maximum
- **THEN** the road is not reported

#### Scenario: Off-road places do not count
- **WHEN** a hamlet stands one cell beside the longer road, and an elven village stands on a road cell
- **THEN** the road is still reported

#### Scenario: Diagonal length
- **WHEN** a diagonal road and a straight road have the same number of cells and only the diagonal one exceeds the maximum by length
- **THEN** only the diagonal road is reported

#### Scenario: A gap across regions is checked
- **WHEN** an over-long gap has cells in two different terrain regions
- **THEN** the road is reported

## REMOVED Requirements

### Requirement: Road coverage applies only inside completed areas
**Reason**: Every region with roads has been completed, so the area list no longer narrows the check. The tiers design removes it after the last placement wave.
**Migration**: None. The area file and the `--areas` option are deleted; the command checks every road.
