## Purpose

Define 虛境 as a backstage holding room that admits no character and owns no exit.

## Requirements

### Requirement: 虛境 admits no character by any path
The starting room SHALL be converged by `sync_limbo()` onto a dedicated `LimboRoom` typeclass
(`typeclasses/rooms.py`) whose entry hook (`at_pre_object_receive`, Evennia's destination-side
`move_to` abort hook) SHALL abort the move of any non-superuser character into the starting
room — whichever path attempts the move, including ordinary exit traversal and
teleport/`moveto`-style `move_to` — leaving the character in its original location and emitting
a zh-tw localized refusal to it.

#### Scenario: Ordinary exit traversal into 虛境 is refused
- **WHEN** a non-superuser `PlayerCharacter` traverses an exit whose destination is the converged
  starting room (a hand-built reverse exit seeded for the test)
- **THEN** the traversal fails, the character's location is unchanged, and the character receives a
  zh-tw localized refusal message

#### Scenario: A forced move_to into 虛境 is refused for non-admins and allowed for superusers
- **WHEN** a non-superuser character is moved to the converged starting room via a forced
  `move_to`/teleport-style call, and separately when a superuser-controlled character is moved the
  same way
- **THEN** the non-superuser move is aborted with the character left in place and a zh-tw refusal,
  while the superuser arrival succeeds

#### Scenario: Gate convergence is idempotent and preserves the authored identity
- **WHEN** `sync_limbo()` runs twice against the same starting room
- **THEN** the room's typeclass is `LimboRoom` after both runs with the second run re-swapping
  nothing, and the room still carries the `LIMBO_KEY` key, the `limbo` alias, and the authored
  zh-tw description

#### Scenario: Superuser admission is the builder/debug convention
- **WHEN** a superuser-controlled character moves into the starting room
- **THEN** it SHALL be admitted, following the builder/debug convention

### Requirement: sync_limbo removes every exit that touches 虛境
On every call that finds the starting room, `sync_limbo()` SHALL delete every persisted exit located in the starting room or leading into it, whatever its key, aliases or subclass. It SHALL log each deletion as the event `bootstrap_limbo_exit_pruned`, with context naming the exit and the side it touched. Objects that have a destination but are not exits SHALL be left alone.

#### Scenario: A leftover forward exit is removed
- **WHEN** a database holds an exit from the starting room to a settlement room and `sync_limbo()` runs
- **THEN** that exit no longer exists, and one `bootstrap_limbo_exit_pruned` event names it

#### Scenario: A reverse exit is removed
- **WHEN** a database holds an exit from any room into the starting room and `sync_limbo()` runs
- **THEN** that exit no longer exists, and one `bootstrap_limbo_exit_pruned` event names it

#### Scenario: A converged room is left alone
- **WHEN** `sync_limbo()` runs twice in a row
- **THEN** the second run deletes nothing and logs no prune event

#### Scenario: A non-exit object with a destination survives
- **WHEN** a non-exit object whose destination is the starting room exists and `sync_limbo()` runs
- **THEN** that object still exists

#### Scenario: Grid synchronization creates no exit touching 虛境
- **WHEN** `sync_grid()` runs over synthetic settlements while a starting room exists
- **THEN** no exit located in or leading into the starting room exists afterwards
