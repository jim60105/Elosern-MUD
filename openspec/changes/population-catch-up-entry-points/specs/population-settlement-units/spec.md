# Spec Delta

## ADDED Requirements

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

