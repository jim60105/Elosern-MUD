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

#### Scenario: A follower's move reuses its leader's catch-up
- **WHEN** a companion's move is settled inside an enclosing movement settlement
- **THEN** the outermost settlement is the only one that catches up, the nested one shares that passage and starts no catch-up of its own, and no nested-catch-up refusal is raised

#### Scenario: Failed catch-up before a command
- **WHEN** the catch-up before a command raises
- **THEN** one `population_catch_up_failed` error event is emitted and the command still runs

### Requirement: Population writers refuse a lagging unit
Outside a running settlement pass, registering an explicit group, creating a group, recording a presence transition, recording a cell protection, and committing a monster departure SHALL raise a named error and write nothing when a unit they touch is behind the current world tick.

#### Scenario: Explicit registration into a lagging unit
- **WHEN** an explicit group is registered on a cell whose unit is at 100 while the world tick is 700
- **THEN** the named not-current error is raised and no group, registration or transition is stored

#### Scenario: Group reaching a lagging unit
- **WHEN** a group is created on a cell of a current unit with an activity area inside a unit that is behind
- **THEN** the named not-current error is raised and no group is stored

#### Scenario: Transition, protection and departure
- **WHEN** a presence transition, a cell protection and a monster departure are each attempted for a cell of a unit that is behind
- **THEN** each raises the named not-current error and the timeline, the coordinate registration and the activity record are unchanged

#### Scenario: Current unit and running pass
- **WHEN** the same writers run for a cell of a current unit, or inside a settlement pass of the cell's unit
- **THEN** they write as before

### Requirement: The GM monster view reports settlement progress without settling
The GM monster placement read SHALL report the settled-through tick of the monster's unit and SHALL mark a unit that is behind the world tick. The read SHALL NOT change any state.

#### Scenario: Lagging monster
- **WHEN** the placement section is read for a monster of a unit at 100 while the world tick is 700
- **THEN** the section carries the progress row with 100 and the behind row with 600, and the unit still reports 100

#### Scenario: Current monster
- **WHEN** the placement section is read for a monster of a current unit
- **THEN** the section carries the progress row and no behind row

### Requirement: A clock advance settles observed units only
The population stage of a clock advance SHALL settle the closed sets of the observed units through the advance's end tick, and SHALL leave every other unit's records, individuals and settled-through tick unchanged. An observed set that is behind the advance's start SHALL be settled from its own settled-through tick inside the same advance, with field contact admitted only at the advance's end tick.

#### Scenario: Far unit is left alone
- **WHEN** a player character stands in one synthetic zone, a second zone beyond the sight radius has due groups and a deficit, and the clock advances from 100 to 700
- **THEN** the first zone's unit reports 700, the second zone's unit reports 100, and the second zone's state projection is unchanged

#### Scenario: Observed set behind the start
- **WHEN** the observed zone's unit is at 100, the world tick is 400 and the clock advances to 700
- **THEN** the unit reports 700 and its state projection equals that of one scoped pass from 100 to 700

#### Scenario: No player
- **WHEN** the clock advances with no player character in the world
- **THEN** only the residual unit's settled-through tick moves

#### Scenario: Rollback
- **WHEN** a later clock stage raises after the observed units were settled, including an inline catch-up
- **THEN** every unit reports its pre-advance tick and the state projection equals its pre-advance value in memory and after an attribute cache reset

### Requirement: Deferred settlement gives the whole-world result
A world advanced with observed-only settlement and then caught up everywhere SHALL have the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as the same world settled by whole-world passes over the same intervals.

#### Scenario: Advance, then catch up
- **WHEN** a synthetic two-zone world with a player in the first zone is advanced by three intervals and the second zone is then caught up, and an identical world is settled by three whole-world passes
- **THEN** both state projections are equal

#### Scenario: Reload while a unit is behind
- **WHEN** every attribute cache is reset while the second zone is behind and the zone is then caught up
- **THEN** its state projection equals the projection without the reset

### Requirement: Advance decisions and snapshots are independent of unobserved units
The groups for which one clock advance plans decisions, and the individuals it snapshots for rollback, SHALL NOT depend on how many groups, individuals or due boundaries unobserved units hold.

#### Scenario: Growing the far zone
- **WHEN** the same advance runs over a world whose unobserved zone holds one due group and over a world whose unobserved zone holds six
- **THEN** both advances plan decisions for the same groups and snapshot the same number of individuals

### Requirement: The contact forecast reads observed units only
The interruptible-skip boundary query SHALL project only the observed units, SHALL return the same tick as a projection of the whole world when every unit is current, and SHALL return that tick unchanged when unobserved units are behind.

#### Scenario: Same answer
- **WHEN** a contact with the observing party is due at one tick and unobserved zones hold earlier maintenance boundaries
- **THEN** the query returns the contact tick, equal to the whole-world projection's answer, and projects no group of an unobserved zone

#### Scenario: Lagging far zone
- **WHEN** the same query runs once with the unobserved zone current and once with it far behind the world tick
- **THEN** both queries return the same tick

### Requirement: A scoped pass enumerates only its own individuals
A scoped settlement pass SHALL build its presence facts from the members of the scope's groups and the individuals registered on cells of the scope, and SHALL give every zone of the scope the counts a whole-world enumeration gives.

#### Scenario: Counts equal the whole-world counts
- **WHEN** zone counts of one synthetic zone are measured in a scoped pass and from a whole-world enumeration, in a world where a second zone holds other individuals
- **THEN** the zone's local, home-owned and per-cell measures are equal

#### Scenario: Home-owned member standing in a linked unit
- **WHEN** a member of a group owned by the scope's zone stands on a cell of another unit that the group links into the scope
- **THEN** the member is counted against the zone's home ceiling

#### Scenario: Registered individual without a group
- **WHEN** a living individual with a home zone of the scope belongs to no group and is registered on a cell of the scope
- **THEN** it is counted locally and against the home ceiling

#### Scenario: Results are unchanged
- **WHEN** the synthetic two-zone world with a player in the first zone is advanced by three intervals and caught up everywhere, once with the scoped enumeration and once with the whole-world enumeration
- **THEN** both state projections are equal

### Requirement: Advance database work is independent of unobserved units
One clock advance SHALL NOT read, snapshot, write or otherwise name any individual, group or cell registration of an unobserved unit. The database work it issues for its own units SHALL be the same work whatever the unobserved units hold, so the rows it touches are those of the observed units, however many groups or individuals an unobserved unit has.

#### Scenario: Growing the far zone
- **WHEN** the same advance runs over a world whose unobserved zone holds one group of one individual and over a world whose unobserved zone holds six groups of three
- **THEN** neither advance issues a statement that names an individual of the unobserved zone, while the same world enumerated whole does name them

### Requirement: A drain run settles the most lagging closed set by one bounded slice
One drain run SHALL select the closed set of units with the lowest settled-through tick, ties broken by the smallest unit identifier, and SHALL settle it forward by at most the configured slice of game time and never past the world tick, admitting no field contact and leaving the world tick unchanged. A world with no lagging unit SHALL be left untouched.

#### Scenario: One slice
- **WHEN** one unit is at 100, another at 400, the world tick is 5000 and the slice is 600
- **THEN** one run moves the first unit to 700, leaves the second at 400 and the world tick at 5000

#### Scenario: Slice ends at the world tick
- **WHEN** the only lagging unit is at 4800, the world tick is 5000 and the slice is 600
- **THEN** one run moves the unit to 5000

#### Scenario: Nothing to do
- **WHEN** every unit is at the world tick
- **THEN** a run writes nothing and emits no event

#### Scenario: Linked units move together
- **WHEN** the most lagging unit is linked to a second unit by a group that touches both
- **THEN** one run moves both units by the same slice

### Requirement: Draining gives the whole-world result
A world whose lagging units were settled by drain runs SHALL have the same activity record, zone records, site records and per-individual position, gauges, reserve, posture and sleep receipt as the same world settled by one whole-world pass to the same tick.

#### Scenario: Drain to completion
- **WHEN** a synthetic two-zone world with both units behind is drained until no unit lags, and an identical world is settled by one whole-world pass to the world tick
- **THEN** both state projections are equal

### Requirement: A drain run is atomic and reports itself
A drain run that settled something SHALL emit one `population_backlog_drained` info event on durable commit with the number of units, both ticks and the number of units still lagging. A set whose settlement fails SHALL keep its complete prior durable state and live caches and SHALL cause one `population_backlog_drain_failed` error event; the same run SHALL then try the next most lagging set, up to three sets per run.

#### Scenario: Reported slice
- **WHEN** a run moves one of two lagging units from 100 to 700
- **THEN** one info event carries one unit, 100, 700 and one unit still lagging

#### Scenario: Failed run
- **WHEN** a fault is injected inside a run after a departure was written
- **THEN** the unit still reports 100, its state projection in memory and after an attribute cache reset equals its prior value, one error event is emitted, and the next run without the fault moves the unit to 700

#### Scenario: A failing set does not starve the next
- **WHEN** the most lagging set fails on every attempt and a second set is also behind
- **THEN** one run emits one error event for the first set, moves the second set by one slice and reports it

### Requirement: The periodic drain honours its switch
The periodic caller SHALL perform one drain run per repeat while the drain is enabled and SHALL perform none while it is disabled.

#### Scenario: Disabled
- **WHEN** the periodic caller repeats with the drain disabled and a unit lagging
- **THEN** no drain run happens and the unit's settled-through tick is unchanged

#### Scenario: Enabled
- **WHEN** the periodic caller repeats once with the drain enabled and a unit lagging
- **THEN** exactly one drain run happens with the configured slice

### Requirement: Player input is recorded at command and action ingress
The server SHALL record the time of the last player input when a session sends a non-idle text command and when a session with a puppet sends a WebClient UI action. An idle keepalive, a synchronization request and a UI action from a session without a puppet SHALL NOT be recorded.

#### Scenario: Text command
- **WHEN** a session sends a text command that is not the idle keepalive
- **THEN** the recorded time of the last player input is the time of that command

#### Scenario: UI action with a puppet
- **WHEN** a WebClient session with a puppet sends a UI action
- **THEN** the recorded time of the last player input is the time of that action

#### Scenario: Idle keepalive
- **WHEN** a session sends the idle keepalive and nothing else
- **THEN** no player input is recorded

#### Scenario: Synchronization and unpuppeted action
- **WHEN** a WebClient session sends a synchronization request, or a session without a puppet sends a UI action
- **THEN** no player input is recorded

### Requirement: The periodic drain yields to recent player input
The periodic caller SHALL perform no drain run while the last recorded player input is more recent than the configured idle window. It SHALL drain as usual when no input has been recorded or when the window has passed. A skipped repeat SHALL read no population record and emit no event.

#### Scenario: Recent input
- **WHEN** the periodic caller repeats with the drain enabled, a unit lagging, an idle window of 20 seconds and a player input recorded 2 seconds earlier
- **THEN** no drain run happens and the unit's settled-through tick is unchanged

#### Scenario: Window passed
- **WHEN** the periodic caller repeats with the same world and a player input recorded 20 seconds earlier
- **THEN** exactly one drain run happens

#### Scenario: No input recorded
- **WHEN** the periodic caller repeats with the drain enabled, a unit lagging and no player input recorded
- **THEN** exactly one drain run happens

### Requirement: Catch-up and direct drains ignore the idle window
The synchronous catch-up and a direct drain call SHALL settle a lagging closed set whatever the recorded player input is.

#### Scenario: Catch-up during activity
- **WHEN** a unit is behind the world tick, a player input was recorded just now, and the catch-up is asked for that unit
- **THEN** the unit reports the world tick

#### Scenario: Direct drain during activity
- **WHEN** a unit is behind the world tick, a player input was recorded just now, and the drain operation is called directly
- **THEN** the unit moves forward by one slice
