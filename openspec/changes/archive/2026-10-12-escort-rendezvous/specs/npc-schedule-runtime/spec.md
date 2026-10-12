# Spec Delta

## MODIFIED Requirements

### Requirement: Due movement uses real exits and emits events
Schedule movement SHALL retain real Exit traversal, locks/vetoes, state and truthful departure/arrival events. A valid escort reason SHALL give follower movement precedence over ordinary schedule movement with no replayable missed movement. After the last temporary-source release, schedule behavior SHALL resume at the current tick and actual location, neither transporting the actor to the old encounter nor replaying skipped movement.

#### Scenario: Escort follow wins over a due schedule move
- **WHEN** a valid temporary member follows while its normal schedule movement is due
- **THEN** the actor follows once to the real destination and no competing schedule move or clock charge occurs

#### Scenario: Release resumes current schedule without replay
- **WHEN** the last escort reason is released after missed schedule windows
- **THEN** applicable behavior resumes from the actual location/current tick without old-encounter transport or missed departure/arrival events

#### Scenario: Unrelated schedules remain unchanged
- **WHEN** a non-escort scheduled NPC traverses a due ordinary move
- **THEN** its real Exit, locks, state and events retain existing behavior

#### Scenario: A due move traverses a real Exit
- **WHEN** a move target resolves to a destination with a traversable Exit
- **THEN** the NPC reaches it through the Exit; its default state and departure/arrival events are produced

#### Scenario: Events carry safe identity, target, and due tick
- **WHEN** a settlement event is emitted
- **THEN** its JSON-safe payload carries stable `npc_id`, display `npc`, and `state` or `from`/`to`; `due_tick` equals `cycle_start + tick_offset`

#### Scenario: Possession, service and exam holds keep their own authority
- **WHEN** an escort silences a scheduled actor or an exam hold applies
- **THEN** Possession/service silencing and exam holds SHALL retain their own behavior and authority.
