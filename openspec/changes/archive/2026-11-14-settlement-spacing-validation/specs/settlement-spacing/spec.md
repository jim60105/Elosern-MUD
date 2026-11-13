# Spec Delta

## Purpose
Validate the committed village and hamlet placement against the minimum spacing, road coverage and placement identity rules, so that placement work done by a throwaway tool is still checked in continuous integration.

## ADDED Requirements

### Requirement: Minimum spacing is checked by kind in straight-line distance
The validation SHALL report a hamlet closer than the hamlet minimum to any capital, city, town, port, village or other hamlet, and a village closer than the village minimum to any capital, city, town, port or other village, measured between cell centres. Elven villages, dungeons and pairs among the four larger kinds SHALL NOT be checked.

#### Scenario: Hamlet boundary
- **WHEN** a synthetic hamlet lies exactly at the hamlet minimum from a town and a second hamlet lies one cell closer to that town
- **THEN** only the second hamlet is reported, naming the town and the distance

#### Scenario: Village boundary and the village-hamlet pair
- **WHEN** a synthetic village lies below the village minimum from a city, and a hamlet lies between the hamlet minimum and the village minimum from another village
- **THEN** the first village is reported and the hamlet pair is not

#### Scenario: Kinds that take no part
- **WHEN** a hamlet stands next to an elven village and next to a dungeon, and two towns stand next to each other
- **THEN** nothing is reported

#### Scenario: A pair is reported once
- **WHEN** two hamlets are too close to each other
- **THEN** one problem is reported, under the smaller identifier

### Requirement: An exemption mark skips minimum spacing
The validation SHALL skip every minimum-spacing pair in which a village or hamlet carries a spacing exemption reason, and SHALL ignore the mark on any other kind.

#### Scenario: Marked hamlet
- **WHEN** a marked hamlet stands closer than the hamlet minimum to a town and to an unmarked hamlet
- **THEN** neither pair is reported

#### Scenario: Mark on another kind
- **WHEN** a town carries the mark and an unmarked hamlet stands too close to it
- **THEN** the hamlet is reported

### Requirement: Road coverage bounds the gap between consecutive road settlements
For each checked road, the validation SHALL treat as settlement positions the road's two ends, every cell on it that is an end of any road, and every village or hamlet cell on it, and SHALL report each pair of consecutive positions whose road length exceeds the configured maximum, counting a diagonal step as the square root of two.

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

### Requirement: Road coverage applies only inside completed areas
The validation SHALL check a road gap only when every cell of the gap lies in a completed area, where an area is a terrain region optionally narrowed to an inclusive cell rectangle. An empty area list SHALL check no gap.

#### Scenario: Inside, crossing and outside
- **WHEN** three over-long gaps lie wholly inside a completed area, across its boundary and wholly outside it
- **THEN** only the first is reported

#### Scenario: Rectangle bounds
- **WHEN** an area narrows its region to a rectangle and an over-long gap lies in the region but outside the rectangle
- **THEN** the gap is not reported

#### Scenario: Empty list
- **WHEN** the area list is empty and a road has an over-long gap
- **THEN** no road gap is reported, and the other rules still run

#### Scenario: Invalid area file
- **WHEN** an area file has an unknown key, a duplicate identifier, malformed bounds or an undeclared region
- **THEN** loading fails with an error naming the entry

### Requirement: Villages and hamlets satisfy the placement identity rules
The validation SHALL report a village or hamlet with a wrong identifier prefix, no lore row, a cell in a region without a nation, a lore nation that differs from its region's nation, a population outside its kind's range, or a cell in a road-forbidden region; a village on no road cell; any other kind using a reserved prefix; and any two locations sharing a display name.

#### Scenario: One fault each
- **WHEN** synthetic villages and hamlets each carry exactly one of those faults
- **THEN** each is reported once under its own code, and a correct village on a road cell is not reported

#### Scenario: Reserved prefix and duplicate name
- **WHEN** a town's identifier starts with the village prefix, and a hamlet shares a display name with a city
- **THEN** both are reported, the duplicate once

### Requirement: The spacing command reports by exit status and writes nothing
The command SHALL print one line per problem with its code and subject, and SHALL exit 0 with no problem, 1 with any problem, and 2 when the sources, the road artifact, the lore override or the area file do not load. It SHALL write no file.

#### Scenario: Synthetic workspace runs
- **WHEN** the command runs on a clean synthetic workspace, then after a hamlet is moved too close to a town, then with a corrupt road artifact
- **THEN** the exit statuses are 0, 1 and 2, and the workspace file digests are identical before and after every run
