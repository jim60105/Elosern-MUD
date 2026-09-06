# defeat-aftermath-violation-sequence delta

## ADDED Requirements

### Requirement: Knocked-out companions wake with their own digest observation
At sequence end each non-fled companion victim SHALL carry its own
per-participant digest observation (the same in-memory outcome shape as the
player's: selected/landed/resisted/climax/zero-landed), and settlement
SHALL emit its zh-tw wake observation line. No companion state kinds beyond
the existing `SexualState` fields are introduced.

#### Scenario: Companion wake observation is emitted
- **WHEN** a sequence ends with one knocked-out companion victim
- **THEN** the returned outcome set contains that companion's counts and one companion wake line is rendered for it

## MODIFIED Requirements

### Requirement: Violation attempts select victims from the target pool
The violation target pool SHALL be every non-fled allied participant — the
defeated player plus each companion in the battlefield's knocked-out set.
Companions that fled the session SHALL be excluded; the player SHALL always
be in the pool. Each attempt's victim SHALL be selected deterministically
through the state-derived dice helper (session id + violator identity +
attempt index), and every write SHALL land on the selected victim's own
records: its `SexualState`, its credited counters, its EventLog entries —
never proxied through the player. A solo party (player only) SHALL behave
exactly as the pinned player-only baseline, and a party whose every other
allied member fled SHALL settle without error.

#### Scenario: Knocked-out companions enter the pool and take their own writes
- **WHEN** a party of the player plus one knocked-out (non-fled) companion is defeated by one violator with cap 2 and the state-derived selection picks the companion once
- **THEN** that attempt's deltas, counter credits, and `violation_act` entry land on the companion's own records and the violator's counters credit symmetrically per the shared crediting convention

#### Scenario: Fled companions are excluded
- **WHEN** the companion fled before the session settled defeat
- **THEN** no attempt targets the companion and its records are untouched

#### Scenario: Solo party matches the pinned baseline
- **WHEN** a solo player is defeated by a violator with cap 3 and every attempt lands
- **THEN** all three attempts target the player, identical to the player-only baseline the violation change pins

#### Scenario: The player's wake prose keys on her own landed attempts
- **WHEN** every landed attempt of the sequence targeted a companion victim
- **THEN** the player's `defeat_settle` wake prose stays the PG line and the companion victim's wake observation renders for the companion
