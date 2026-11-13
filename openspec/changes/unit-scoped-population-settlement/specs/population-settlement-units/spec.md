# Spec Delta

## ADDED Requirements

### Requirement: A closed set of units settles alone
A scoped lifecycle pass SHALL settle only the groups, journeys, zones and sites of one closed set of units, from that set's settled-through tick to a target tick, and SHALL advance only those units' settled-through ticks. It SHALL leave every record and every individual of other units unchanged.

#### Scenario: Other units are untouched
- **WHEN** a scoped pass settles one of two disjoint synthetic zones, each with due groups, a deficit and bodies below full reserve
- **THEN** the other zone's groups, zone record, bodies and settled-through tick are unchanged, and no decision was planned for any of its groups

#### Scenario: Cursor moves only for the scope
- **WHEN** a scoped pass settles one unit from 100 to 400
- **THEN** that unit reports 400 and every other unit reports 100

#### Scenario: Unequal cursors
- **WHEN** a scope is requested whose closed set holds units with different settled-through ticks
- **THEN** the pass raises the named cursor-mismatch error before any write

### Requirement: Separate settlement equals whole-world settlement
Settling every closed set of units separately SHALL leave the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as one whole-world pass over the same interval, for any order of the sets and any partition of the interval per set.

#### Scenario: Order and partition
- **WHEN** a synthetic world of two disjoint units, with wandering groups, a travelling group, a zone below its lower density and a recoverable site, is settled over one interval as a whole, then unit by unit in both orders, then with one unit in two parts and the other in three
- **THEN** all resulting state projections are equal

#### Scenario: Linked units settle together
- **WHEN** a group owned by one zone stands on a cell of another zone and one of the two units is requested
- **THEN** the pass settles both units and both report the target tick

#### Scenario: Reload between parts
- **WHEN** one unit is settled to the midpoint, every attribute cache is reset, and it is then settled to the endpoint
- **THEN** its state projection equals the projection of settling it in one part

### Requirement: Shared evidence is kept until every concerned unit has passed it
A recorded presence transition SHALL be retired only when every unit of its before and after positions and home zones has been settled to or past its occurrence tick. A closed cell protection interval SHALL be retired only when the unit of its cell has been settled past its end.

#### Scenario: Loss recorded ahead of one unit
- **WHEN** a loss at tick 118 concerns two units, one is settled to 200 and the other stays at 100
- **THEN** the transition is still stored, and settling the second unit through 118 uses it and then retires it

#### Scenario: Protection of a lagging cell
- **WHEN** a closed protection interval ending at 150 lies in a unit at 100 while another unit is settled to 300
- **THEN** the interval is still stored, and a group of the lagging unit settled through 140 does not enter the protected cell

### Requirement: A scoped pass never writes outside its scope
A scoped pass SHALL refuse, with a named error and without partial state, any departure, arrival or birth that would place an individual on a cell outside the scope.

#### Scenario: Out-of-scope destination
- **WHEN** a fault-injected decision inside a scoped pass selects a destination cell of a unit outside the scope
- **THEN** the pass raises the named scope-violation error and the state projection equals its value before the pass
