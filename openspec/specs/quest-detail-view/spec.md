# quest-detail-view Specification

## Purpose

Let a player inspect one of their own accepted quest records in full detail from
inside the game, rendered deterministically from immutable quest values.

## Requirements

### Requirement: A player can inspect one own quest's full detail
`guild show <quest_id>` SHALL render one of the caller's own quest records with
its display name, state, stage index, the current stage's objective description,
progress, deadline (when the definition sets one), and the registered reward for
that definition at the caller's branch (when one exists). It SHALL resolve the
record through the quest runtime read APIs and SHALL NOT require a local
`GuildStaff` host. An unknown quest id SHALL produce a Traditional Chinese error
and SHALL cause no state change.

#### Scenario: Accepted quest shows the current objective
- **WHEN** a player with an active `introductory_hunt` record runs
  `guild show introductory_hunt:1`
- **THEN** the output names the quest, its state, the current stage, the defeat
  objective's description, and the current progress

#### Scenario: Detail is available without local guild staff
- **WHEN** a player runs `guild show <quest_id>` in a room with no `GuildStaff`
  host present
- **THEN** the full quest detail is still rendered from the player's own log

#### Scenario: Unknown quest id is rejected
- **WHEN** a player runs `guild show <unknown-id>`
- **THEN** a Traditional Chinese error is shown and the quest log is unchanged

#### Scenario: Reward is rendered only when the branch offers the quest
- **WHEN** a detail view resolves a definition with no registered offer at the
  caller's registered branch
- **THEN** the reward section is omitted instead of erroring

#### Scenario: Unregistered player sees no reward section
- **WHEN** a player without a valid `guild_registration` runs
  `guild show <quest_id>`
- **THEN** the detail still renders and the reward section is omitted

#### Scenario: Deadline is rendered when the definition sets one
- **WHEN** the record carries a `deadline_tick` and the definition declares
  `deadline_hours`
- **THEN** a remaining-hours line is rendered; a deadline-less definition omits it

#### Scenario: Expired quest deadline is reported
- **WHEN** the record's `deadline_tick` is not later than the current world tick
- **THEN** the detail renders an expired-deadline line rather than a negative
  remaining duration

### Requirement: Objective descriptions are deterministic and exhaustive
The rendering layer SHALL produce a Traditional Chinese description for every
`ObjectiveKind` and `DestinationKind` combination used by the closed definition
vocabulary. It SHALL be read-only, SHALL NOT write quest or player state, and
SHALL raise on an unknown `ObjectiveKind` so drift fails loudly in tests.

#### Scenario: DEFEAT objective renders tier and quantity
- **WHEN** a DEFEAT objective declares tier `low` and quantity `1`
- **THEN** the description states the monster tier and the required count

#### Scenario: REACH objective renders its destination
- **WHEN** a REACH objective declares an anchor, grid, or bound-instance
  destination
- **THEN** the description names the destination in Traditional Chinese

#### Scenario: ESCORT objective renders the protected-entity requirement
- **WHEN** an ESCORT objective declares a destination
- **THEN** the description states that every protected entity must be escorted
  to the destination

#### Scenario: ACQUIRE objective renders the item and count
- **WHEN** an ACQUIRE objective declares an item key and quantity
- **THEN** the description names the item and the required count

#### Scenario: Unknown objective kind raises
- **WHEN** the renderer is invoked with an `ObjectiveKind` it does not recognize
- **THEN** it raises an explicit error instead of emitting a wrong description
