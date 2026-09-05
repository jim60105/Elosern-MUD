# Delta spec: party-system (companion-possession-rules)

Two requirements widen: dismissal refuses a possessed companion until handback, and the auto-leave
hook releases possession first inside its own transaction. Both reproduced in full.

## MODIFIED Requirements

### Requirement: The leave command dismisses a companion without affinity change

The character cmdset SHALL provide `leave <npc>` (alias 解散) that resolves a bound companion (absent, ambiguous, or unbounded targets produce Traditional Chinese errors) and dismisses it through `leave_party(npc, player, reason="dismissed")`. A companion currently possessed by the caller's account SHALL be refused with the fixed handback-first message at the command surface AND inside `leave_party` itself (defense-in-depth for every API caller). Dismissal SHALL NOT change affinity in either direction and SHALL notify the player. A webclient action SHALL offer the same flow.

#### Scenario: Dismissal removes the binding
- **WHEN** a player dismisses a bound companion
- **THEN** `player.db.party` and the NPC's `party_member` are cleared and the player is notified

#### Scenario: Dismissal keeps affinity unchanged
- **WHEN** a player dismisses a companion with a 信賴-stage record
- **THEN** the NPC's affinity value is unchanged

#### Scenario: An unbounded target is rejected
- **WHEN** a player runs `leave` on an NPC that is not a companion
- **THEN** the command reports the Traditional Chinese error and no state changes

#### Scenario: The leave command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `leave` and its alias appear in `docs/game/command-reference.md`

#### Scenario: A possessed companion refuses dismissal
- **WHEN** `leave` (or any `leave_party` caller) targets the companion the account possesses
- **THEN** the fixed handback-first message surfaces and party and possession attributes are
  unchanged

### Requirement: Companions auto-leave when affinity drops below the invite threshold

The auto-leave recheck hook installed by `affinity-system` SHALL be wired: after every negative affinity delta, when the NPC is a bound companion and the NPC's affinity toward the player drops below the invite threshold (70), the hook SHALL call `leave_party(npc, player, reason="affinity_below_threshold")` as part of the affinity write's transaction — a failed leave SHALL roll back the entire negative-delta operation so "affinity below threshold but still bound" is unreachable — and the write API SHALL return the auto-leave notification line, which the caller SHALL send to the player only after its own transaction commits. The writer SHALL never send the notification itself. A negative delta that leaves affinity at or above the threshold SHALL NOT end the party. When the leaving NPC is possessed, the hook SHALL first run `possession.release_for_party_change(npc, player)` BEFORE opening the affinity write's atomic block (release-then-commit — puppet/session side effects cannot be folded into the database transaction), so a release failure aborts before any delta is written and "affinity below threshold but still possessed" is unreachable.

#### Scenario: Below-threshold affinity ends the party
- **WHEN** a bound companion's affinity drops from 70 to 69 through a negative delta
- **THEN** the party binding is removed with the auto-leave reason, the write API returns the notification line, and the caller notifies the player only after the write commits

#### Scenario: At-threshold affinity keeps the party
- **WHEN** a bound companion's affinity drops to exactly 70 through a negative delta
- **THEN** the party binding remains

#### Scenario: A failed auto-leave rolls back or aborts the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold, or the
  possession release of a possessed companion fails
- **THEN** in the first case the affinity value and both party attributes return to their
  pre-delta values and in the second no delta is written at all; either way the companion remains
  bound (and possessed, if it was), and no notification is sent

#### Scenario: Non-companions are unaffected by the hook
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** no party call or notification occurs

#### Scenario: Auto-leaving a possessed companion releases first
- **WHEN** a possessed companion's affinity crosses below the threshold
- **THEN** the possession release commits before the affinity/party atomic opens, and a release
  failure leaves affinity, party binding, and possession all untouched
