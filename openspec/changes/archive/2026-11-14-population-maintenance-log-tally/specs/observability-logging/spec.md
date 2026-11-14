# Spec Delta

## ADDED Requirements

### Requirement: World-maintenance settlement reports one aggregated event per pass
A population lifecycle settlement pass SHALL emit its per-entity maintenance events at debug level and SHALL emit one info event `population_maintenance_settled` on durable commit, carrying the pass's tick range and one count for each maintenance event name it emitted. A pass that emitted none SHALL emit no aggregated event.

#### Scenario: Many groups, one info line
- **WHEN** one committed pass settles three group decisions, two departures and two arrivals of synthetic groups no party observes
- **THEN** exactly one `population_maintenance_settled` info event is emitted with those three counts and the pass's `tick_from` and `tick_to`, and no info event is emitted for any single decision, departure or arrival

#### Scenario: Quiet pass
- **WHEN** a committed pass settles no decision, departure, arrival, deferred arrival or fatigue transition
- **THEN** no `population_maintenance_settled` event is emitted

#### Scenario: Rolled-back pass
- **WHEN** a later clock stage raises after the pass counted maintenance events
- **THEN** neither the aggregated event nor any counted event is emitted

### Requirement: Maintenance events outside a settlement pass keep info level
The events `fatigue_transition`, `monster_activity_decided`, `monster_departed`, `monster_arrived` and `monster_arrival_deferred` SHALL be emitted at info level whenever they are committed outside a population lifecycle settlement pass, and whenever they are committed by a field contact admission inside one.

#### Scenario: Direct owner operation
- **WHEN** a group decision is committed directly through the activity owner with no settlement pass running
- **THEN** `monster_activity_decided` is emitted at info level with its unchanged context keys

#### Scenario: Acting party fatigue
- **WHEN** a party member's fatigue interval is settled by the clock's own mental stage
- **THEN** its `fatigue_transition` event is emitted at info level

#### Scenario: Contact inside a pass
- **WHEN** a field contact admitted at the pass endpoint commits a fatigue transition for a contacted body
- **THEN** that `fatigue_transition` is emitted at info level and is not counted in the aggregated event
