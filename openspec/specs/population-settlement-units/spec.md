# population-settlement-units Specification

## Purpose
Divides the monster population into settlement units whose settlement never reads another unit's state, and records how far each unit has been settled, so that settlement work can be limited to the units that matter to an action.

## Requirements

### Requirement: Authored geometry resolves to settlement units
Ecology zones and region-bound activity areas SHALL resolve to settlement units such that two of them share a unit exactly when a chain of links connects them: a rectangle overlap inside one region, or a zone or site whose births can be bound to an area. A cell or room that belongs to none of them SHALL belong to the residual unit. The resolution SHALL be deterministic and SHALL read no database state.

#### Scenario: Disjoint zones
- **WHEN** two synthetic zones in one region have rectangles that do not overlap and no activity area touches both
- **THEN** they resolve to two different units, and a cell of each zone resolves to that zone's unit

#### Scenario: Area bridges two zones
- **WHEN** a synthetic region-bound activity area overlaps the rectangles of two otherwise disjoint zones
- **THEN** both zones and the area resolve to one unit

#### Scenario: Birth binding links a zone to a distant area
- **WHEN** a synthetic zone's pool can birth a group bound to a region-bound area whose rectangles do not overlap the zone
- **THEN** the zone and the area resolve to one unit

#### Scenario: Same rectangles in different regions
- **WHEN** two synthetic zones have equal rectangles but different region keys
- **THEN** they resolve to two different units

#### Scenario: Residual
- **WHEN** a room locator, and a wilderness cell covered by no zone and no activity area, are resolved
- **THEN** both resolve to the residual unit

#### Scenario: Stable identity
- **WHEN** the same registries are resolved twice, the second time with their entries in reverse order
- **THEN** every zone, area and cell resolves to the same unit identifier both times

### Requirement: A group's units and unit closures are derived from live state
The units a group touches SHALL be the units of its home, its position, its journey endpoints, every cell of its activity area and its owning zone or site. The closure of a set of units SHALL add every unit reachable through groups and sites that touch more than one unit.

#### Scenario: Group inside its zone
- **WHEN** a zone-owned group stands inside its zone with an area inside that zone
- **THEN** it touches exactly that zone's unit, and the closure of that unit is that unit alone

#### Scenario: Escaped member links two units
- **WHEN** a group owned by one zone stands on a cell of a second, disjoint zone
- **THEN** it touches both units, and the closure of either unit contains both

#### Scenario: Journey endpoints
- **WHEN** a group travels from a cell of one unit to a cell of another
- **THEN** it touches both units until its arrival is recorded

### Requirement: Each unit records its settlement progress
The world SHALL store one settled-through tick per settlement unit, with a default for units not yet listed. Fresh provisioning SHALL create the record at the provisioning tick, a pass SHALL record its endpoint, a rolled-back advance SHALL restore the record, and a missing or malformed record SHALL be refused by name.

#### Scenario: Fresh world
- **WHEN** a population is provisioned at tick 100
- **THEN** every unit reports settled-through tick 100

#### Scenario: Pass records its endpoint
- **WHEN** a lifecycle pass settles through tick 260
- **THEN** every unit reports 260

#### Scenario: Rollback
- **WHEN** a later clock stage raises after a pass recorded tick 260 over a world at 100
- **THEN** every unit reports 100 in memory and after reload

#### Scenario: Malformed record
- **WHEN** the stored record is absent, or is not a mapping with an integer default and a mapping of unit identifiers to integers
- **THEN** reading it raises the population owner's malformed-state error and nothing is rewritten

### Requirement: A closed set of units settles alone
A scoped lifecycle pass SHALL settle only the groups, journeys, zones and sites of one closed set of units, from that set's settled-through tick to a target tick, and SHALL advance only those units' settled-through ticks. It SHALL leave every record and every individual of other units unchanged.

#### Scenario: Other units are untouched
- **WHEN** a scoped pass settles one of two disjoint synthetic zones, each with due groups, a deficit and bodies below full reserve
- **THEN** the other zone's groups, zone record, bodies and settled-through tick are unchanged, and no decision was planned for any of its groups

#### Scenario: Cursor moves only for the scope
- **WHEN** a scoped pass settles one unit from 100 to 400
- **THEN** that unit reports 400 and every other unit reports 100

#### Scenario: Unequal cursors
- **WHEN** a closed set holds one unit at 400 and one at 100 and is settled to 700
- **THEN** both units report 700, and no zone or site step ran for the first unit at any tick up to 400

### Requirement: Separate settlement equals whole-world settlement
Settling every closed set of units separately SHALL leave the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as one whole-world pass over the same interval, for any order of the sets and any partition of the interval per set, except each zone record's settled-through marker, which records the boundary the pass itself reached and which no decision reads.

#### Scenario: Order and partition
- **WHEN** a synthetic world of two disjoint units, with wandering groups, a travelling group, a zone below its lower density and a recoverable site, is settled over one interval as a whole, then unit by unit in both orders, then with one unit in two parts and the other in three
- **THEN** all resulting state projections are equal

#### Scenario: Units linked after diverging
- **WHEN** one of two units is settled alone to 400, a group that touches both units is then created at 400, and the closed set is settled to 700; and an identical world is settled as a whole to 400, receives the same group, and is settled as a whole to 700
- **THEN** both state projections are equal

#### Scenario: Linked units settle together
- **WHEN** a group owned by one zone stands on a cell of another zone and one of the two units is requested
- **THEN** the pass settles both units and both report the target tick

#### Scenario: Reload between parts
- **WHEN** one unit is settled to the midpoint, every attribute cache is reset, and it is then settled to the endpoint
- **THEN** its state projection equals the projection of settling it in one part

#### Scenario: Zone progress marker
- **WHEN** a scoped pass settles one unit whose own last boundary lies below another unit's later boundary
- **THEN** that unit's zone record reports the last boundary its own pass noted, the marker never decreases, and the activity record, site records, per-individual facts and timeline evidence of a settlement do not depend on it

### Requirement: Shared evidence is kept until every concerned unit has passed it
A recorded presence transition SHALL be retired only when every unit of its before and after positions and home zones has been settled to or past its occurrence tick. A closed cell protection interval SHALL be retired only when the unit of its cell has been settled past its end.

#### Scenario: Loss recorded ahead of one unit
- **WHEN** a loss at tick 118 concerns two units, one is settled to 200 and the other stays at 100
- **THEN** the transition is still stored, and settling the second unit through 118 uses it and then retires it

#### Scenario: Protection of a lagging cell
- **WHEN** a closed protection interval ending at 150 lies in a unit at 100 while another unit is settled to 300
- **THEN** the interval is still stored, and a group of the lagging unit settled through 140 does not enter the protected cell

### Requirement: A scoped pass never writes outside its scope
A scoped pass SHALL refuse, with a named error and without partial state, any departure, arrival or birth that would place an individual on a cell outside the scope, and any group creation whose units are not all inside the scope.

#### Scenario: Out-of-scope destination
- **WHEN** a fault-injected decision inside a scoped pass selects a destination cell of a unit outside the scope
- **THEN** the pass raises the named scope-violation error and the state projection equals its value before the pass

#### Scenario: Group reaching outside the scope
- **WHEN** a fault-injected birth inside a scoped pass creates a group whose activity area lies in a unit outside the scope
- **THEN** the pass raises the named scope-violation error and no group, individual or registration remains

### Requirement: Catch-up settles a lagging closed set to the current tick
A catch-up of given cells SHALL settle the closed set of units around them from its settled-through tick to the current world tick, admitting no field contact, and SHALL commit it or restore the complete prior durable state and live caches. A set that is already current SHALL be left untouched with no event.

#### Scenario: Lagging unit
- **WHEN** a unit is at 100, the world tick is 700 and a catch-up of one of its cells runs
- **THEN** the unit reports 700, its state projection equals that of one scoped pass from 100 to 700, and one `population_caught_up` info event carries the unit count and both ticks

#### Scenario: Current unit
- **WHEN** a catch-up runs for a cell whose unit is at the world tick
- **THEN** nothing is written and no event is emitted

#### Scenario: Failure
- **WHEN** a fault is injected inside the catch-up after a departure was written
- **THEN** the error propagates, the unit still reports 100, and its state projection in memory and after an attribute cache reset equals its value before the catch-up

### Requirement: Observed units are derived from player positions and announcements
The observed units SHALL be the residual unit, every unit with a cell within the maximum ground sight radius of a player character's wilderness position, and every such unit around a location announced by a running action. A player character in a room SHALL add no unit beyond the residual unit.

#### Scenario: Sight radius
- **WHEN** a player character stands in one synthetic zone, within the sight radius of a second zone's cell and farther than the radius from a third
- **THEN** the observed units are the residual unit and the units of the first and second zones

#### Scenario: Announced destination
- **WHEN** an action announces a location in the third zone while it runs
- **THEN** the third zone's unit is observed during the action and no longer afterwards

### Requirement: Actions begin with the units they touch current
A command SHALL catch up the observed units before it parses or runs, a movement edge SHALL announce and catch up its destination before it is settled, and quest materialisation, GM placement, GM removal, a GM hit-point edit of a monster and the quest site-target read SHALL catch up their target cell before they read or write it. A failed catch-up before a command SHALL be reported as an error event and SHALL NOT prevent the command.

#### Scenario: Command after an untracked relocation
- **WHEN** a player character was relocated beside a lagging unit without a clock advance and then runs any command
- **THEN** that unit is at the world tick before the command's own code runs

#### Scenario: Movement into a lagging unit
- **WHEN** a party moves one edge into a cell whose unit is behind
- **THEN** the unit is caught up to the pre-movement tick before the edge's own settlement starts, and the edge's settlement observes it

#### Scenario: Failed catch-up before a command
- **WHEN** the catch-up before a command raises
- **THEN** one `population_catch_up_failed` error event is emitted and the command still runs
