## MODIFIED Requirements

### Requirement: The safety gate rejects outright; it does not compute a partial-safety shortened
duration of its own
`evaluate_skip_safety()` SHALL NOT return any value representing a partially-allowed or
"shortened-but-still-unsafe" duration. When either reject condition applies, the calling command SHALL
treat the skip as fully blocked, not reduced to a smaller nonzero duration. The declared-practice
booking preflight composes with the gate in a fixed order — parse, safety gate, booking preflight —
and each rejection likewise blocks the WHOLE skip: zero clock advance, zero practice.

#### Scenario: No reject reason carries a partial-duration payload
- **WHEN** `SkipRejectReason`'s definition is inspected
- **THEN** it is a plain enumeration of exactly two reasons (`IN_COMBAT`, `HOSTILE_PRESENT`), with no
  associated "allowed seconds" or similar partial-duration field

#### Scenario: A rejected skip command performs no clock advance
- **WHEN** any of `CmdRest`, `CmdSleep`, or `CmdWaitUntil` calls `evaluate_skip_safety()` and receives
  a non-`None` result
- **THEN** the command does not call `WorldClock.advance()` at all, and reports the rejection reason to
  the player

#### Scenario: A rejected practice booking performs no clock advance either
- **WHEN** `CmdRest` passes the safety gate but its booking preflight rejects
- **THEN** the command does not call `WorldClock.advance()` at all, reports the stable practice reason code, and no booking survives for a later advance
