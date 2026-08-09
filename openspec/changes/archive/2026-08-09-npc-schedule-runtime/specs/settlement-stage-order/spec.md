# Settlement Stage Order

## MODIFIED Requirements

### Requirement: caravan_arrivals, shop_hours, quest_deadlines, and npc_schedules are declared,
registrable, no-op seams

`world/rules/clock.py` SHALL provide `register_event_source(kind, source)` as the only sanctioned
way to attach a boundary-crossing event query for `caravan_arrivals`, `shop_hours`,
`quest_deadlines`, or `npc_schedules`. When no source is registered for a given `kind`, `advance()`
SHALL treat that stage as producing zero events — never raising, never blocking the rest of
settlement. As of the `npc-schedule-runtime` change, `npc_schedules` SHALL have exactly one
registered source, `settle_npc_schedules`, supplied by `world/rules/npc_schedules.py`.

#### Scenario: An unregistered world-event stage produces no events and does not fail
- **WHEN** `advance()` is called with no source registered for `caravan_arrivals`,
  `shop_hours`, or `quest_deadlines` in the test-isolated clock registry
- **THEN** the call completes successfully and the returned event list contains no entries for any
  of those three kinds

#### Scenario: The npc_schedules stage runs its registered source
- **WHEN** `advance()` crosses a boundary where `settle_npc_schedules` reports a due event
- **THEN** the returned `ScheduledEvent` list includes that event at the `npc_schedules` stage
  position

#### Scenario: A registered synthetic source's events are returned in the correct stage position
- **WHEN** a test registers a source for a synthetic `kind` via `register_event_source()` and calls
  `advance()` across a boundary that source reports an event for
- **THEN** the returned `ScheduledEvent` list includes that source's event, proving the registry
  mechanism works without real scheduling data
