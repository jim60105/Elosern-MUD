## Purpose

Define when a player time skip is rejected for immediate combat or hostile-presence danger.

## Requirements


### Requirement: evaluate_skip_safety rejects a skip when the actor is actively in combat
`world/rules/skip_safety.py` SHALL provide `evaluate_skip_safety(actor) -> SkipRejectReason | None`,
returning `SkipRejectReason.IN_COMBAT` when `actor` is a living, non-fled roster member of a
`Battlefield` whose `is_battle_over()` is `False`.

#### Scenario: An actor mid-fight is rejected
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor who is a living, non-fled member of an
  unresolved `Battlefield`'s roster
- **THEN** it returns `SkipRejectReason.IN_COMBAT`

#### Scenario: An actor whose fight has concluded is not rejected on this basis
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor who was a roster member of a
  `Battlefield` whose `is_battle_over()` is now `True`
- **THEN** it does not return `SkipRejectReason.IN_COMBAT`

### Requirement: fled Battlefield membership is not, by itself, a reject condition
`evaluate_skip_safety(actor)` SHALL NOT reject a skip solely because `actor` is present in a
`Battlefield`'s `fled` set. `fled` records combatants who successfully disengaged from an encounter —
the opposite of being in danger from it — and SHALL NOT be read anywhere in this module as a positive
signal of hostility. `fled` membership is consulted only as part of `IN_COMBAT`'s own definition (an
actor who fled is not an *active* roster member), never as an independent reject condition.

#### Scenario: An actor who fled an ongoing fight, with no monster co-located, is not rejected
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor present in `battlefield.fled` (that
  `Battlefield`'s `is_battle_over()` is `False`), sharing no room with any living `Monster`
- **THEN** it returns `None` — fled membership alone does not reject the skip

#### Scenario: No function in this module treats fled membership as a hostility signal
- **WHEN** `world/rules/skip_safety.py` is inspected
- **THEN** `battlefield.fled` is read only inside the `IN_COMBAT` check's own exclusion of fled
  members from "active roster member," and nowhere else in the module

### Requirement: evaluate_skip_safety rejects a skip when a living Monster shares the actor's location
`evaluate_skip_safety(actor)` SHALL return `SkipRejectReason.HOSTILE_PRESENT` when any living (`hp >
0`) `Monster` instance is present in `actor.location`, independent of whether any `Battlefield` exists
at all. This single condition is the entirety of what both "targeted by a hostile" and "unsafe
location" mean at this point in the roadmap — design doc §6.5 names them as two phrases, but with no
aggro/threat model anywhere in this project's roadmap, nothing distinguishes them: no terrain, zone, or
map-layer signal is consulted, since none exists yet (changes 12-14).

#### Scenario: A wandering, unengaged monster in the room rejects the skip
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor sharing a room with a living `Monster`
  with no `Battlefield` formed at all
- **THEN** it returns `SkipRejectReason.HOSTILE_PRESENT`

#### Scenario: A dead monster in the room does not reject the skip on this basis
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor sharing a room with a `Monster` whose
  `hp.value` is `0` or less
- **THEN** it does not return `SkipRejectReason.HOSTILE_PRESENT`

#### Scenario: A room with no Monster present is safe on this basis
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor whose room contains no `Monster`
  instance
- **THEN** it does not return `SkipRejectReason.HOSTILE_PRESENT`

### Requirement: A safe actor's skip is unconditionally allowed
`evaluate_skip_safety(actor)` SHALL return `None` when neither reject condition applies, allowing the
requesting command to proceed with its own computed duration.

#### Scenario: An actor with no active battlefield membership and no monster present is allowed
- **WHEN** `evaluate_skip_safety(actor)` is called for an actor not in any `Battlefield`'s roster or
  `fled` set, in a room with no living `Monster`
- **THEN** it returns `None`

### Requirement: The safety gate rejects outright; it does not compute a partial-safety shortened
duration of its own
`evaluate_skip_safety()` SHALL NOT return any value representing a partially-allowed or
"shortened-but-still-unsafe" duration. When either reject condition applies, the calling command SHALL
treat the skip as fully blocked, not reduced to a smaller nonzero duration.

#### Scenario: No reject reason carries a partial-duration payload
- **WHEN** `SkipRejectReason`'s definition is inspected
- **THEN** it is a plain enumeration of exactly two reasons (`IN_COMBAT`, `HOSTILE_PRESENT`), with no
  associated "allowed seconds" or similar partial-duration field

#### Scenario: A rejected skip command performs no clock advance
- **WHEN** any of `CmdRest`, `CmdSleep`, or `CmdWaitUntil` calls `evaluate_skip_safety()` and receives
  a non-`None` result
- **THEN** the command does not call `WorldClock.advance()` at all, and reports the rejection reason to
  the player

sed: -e 表示式 #1，字元 2: 未預期的「,」
