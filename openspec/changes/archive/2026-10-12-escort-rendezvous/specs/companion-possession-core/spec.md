# Spec Delta

## MODIFIED Requirements

### Requirement: Entry gates are deterministic, stable-coded, and precede all generative work
Possession SHALL resolve the same canonical effective party membership for general and temporary companions. Existing ordered stable-coded gates `not_bound`, `not_co_located`, `in_combat`, `dialogue_open`, and `already_possessing`, together with existing living-state restrictions, SHALL apply before any generative work or write. Account-wide single-possession scope and fixed reason messages SHALL remain unchanged.

#### Scenario: Temporary membership permits ordinary possession
- **WHEN** a live temporary-only companion passes every existing entry gate
- **THEN** the existing possession transaction and puppet-transfer ladder control that exact NPC and retain the original player as owner

#### Scenario: Temporary status waives no gate
- **WHEN** a temporary target is remote, unavailable, in combat, in dialogue, or the account already possesses an NPC
- **THEN** the existing corresponding refusal writes no possession state

#### Scenario: Every gate names its reason with zero writes
- **WHEN** each of the five gate conditions is provoked individually
- **THEN** the matching `PossessionGateError` reason surfaces with its fixed message and neither possession attribute changes

#### Scenario: One account possesses at most one NPC
- **WHEN** the account's character A possesses companion X, and (through a second session or another character) a possession of Y is attempted
- **THEN** `already_possessing` refuses the second possession

#### Scenario: The bound and co-location gates
- **WHEN** the target is not a live bound companion of this player, or is not co-located
- **THEN** `not_bound` or `not_co_located` refuses accordingly

#### Scenario: The combat gate reuses the party helper
- **WHEN** either side is in an active combat session
- **THEN** `in_combat` refuses, using the same `is_in_active_session` helper the party-adjustment
  boundary uses

#### Scenario: The dialogue gate checks for an open session
- **WHEN** the NPC has an open dialogue session
- **THEN** `dialogue_open` refuses

#### Scenario: The already-possessing gate scans the account's own characters only
- **WHEN** the player already possesses another NPC, or this account's characters already possess
  any NPC
- **THEN** `already_possessing` refuses, scanned over the account's own characters only

### Requirement: Every exit path releases the possession
Actual membership removal SHALL call `release_for_party_change(npc, player)` through full session/control transfer before detaching the NPC; ordinary dismissal/auto-leave/deletion/disconnect semantics SHALL remain unchanged. Ending an escort reason SHALL interrupt possession only when no legitimate membership source remains. A technical handback failure SHALL abort the complete terminal operation; dangling control SHALL never be reported as successful release.

#### Scenario: Last escort reason releases a possessed actor
- **WHEN** an escort terminates while its temporary-only actor is possessed and has no other valid reason
- **THEN** the verified full handback completes, control returns to the owner, possession mirrors/cmdsets are restored to unpossessed state, and the row is removed in the same successful terminal operation

#### Scenario: Surviving source preserves possession
- **WHEN** one escort terminates while the possessed NPC retains general membership or another valid escort reason
- **THEN** that reason is removed and possession stays uninterrupted

#### Scenario: Handback and later-write faults restore live control
- **WHEN** verified handback refuses or a quest/group/reward write fails after handback
- **THEN** the terminal operation reports `control_handback_failed` or `transition_write_failed`, durable reload equals baseline, and the original session puppet, locks, cmdsets, mirrors and cached membership are restored

#### Scenario: Ordinary lifecycle cleanup remains intact
- **WHEN** a general-only actor auto-leaves, is deleted, or its last driving session disconnects
- **THEN** existing full cleanup and disconnect-only hooks apply, with no new unpuppet-hook cleanup

#### Scenario: Auto-leave releases before the affinity write opens
- **WHEN** an ordinary general-only departure applies and a possessed companion's affinity delta is about to drop it below 70
- **THEN** possession release runs and commits first and only then does the affinity/party atomic open, and the notification follows that commit, per the affinity writer's contract

#### Scenario: A failed release aborts the auto-leave write
- **WHEN** `release_for_party_change` raises
- **THEN** no affinity delta or party change is committed and the companion remains bound and possessed with unchanged affinity

#### Scenario: Dismissing a possessed companion is refused
- **WHEN** the player runs `leave` (解散) on the companion they currently possess
- **THEN** the fixed handback-first line is returned and both possession and party attributes are unchanged

#### Scenario: Deletion purge unwinds possession
- **WHEN** a possessed companion NPC is deleted
- **THEN** the purge releases the possession attributes and unwinds the party binding in one transaction, and the player's next read sees no possession

#### Scenario: Disconnect release is account-keyed and idempotent
- **WHEN** `release_on_disconnect` runs twice for the same account
- **THEN** both runs succeed, every `db.possession` mirror under that account is clear after the first, and the second run writes nothing

#### Scenario: Dismissal refuses a possessed companion
- **WHEN** the `leave` command or `leave_party` is invoked on a possessed companion
- **THEN** it is refused with the fixed handback-first message (`REASON_HANDBACK_FIRST`, gate + defense-in-depth inside `leave_party` itself)

#### Scenario: Auto-leave releases before opening the affinity atomic
- **WHEN** an ordinary general-only departure applies and the affinity auto-leave hook runs
- **THEN** it calls `possession.release_for_party_change(npc, player)` as its first step BEFORE opening the affinity write's atomic block (release-then-commit — a database transaction cannot make puppet/session side effects atomic), so a release failure aborts before any affinity delta is written ("affinity below threshold but still possessed" unreachable)

#### Scenario: A failed commit after release converges idempotently
- **WHEN** an ordinary general-only departure applies and the attribute commit itself fails after a successful release
- **THEN** the bounded recovery state is "possession recorded, not yet dismissed" and every leg is idempotent so 歸位 or the next negative delta converges

#### Scenario: Deletion purge releases the full possession first
- **WHEN** `purge_npc_memberships` runs for a possessed companion
- **THEN** it runs the same full release unconditionally before unwinding the binding

#### Scenario: Disconnect release lands on the disconnect-only lifecycle point
- **WHEN** `release_on_disconnect` is wired up with the transition change
- **THEN** its caller lands on `Account.at_post_disconnect` (the disconnect-only lifecycle point — `at_post_unpuppet` fires on every deliberate unpuppet, including possession's own release of A, and must NOT run this)

#### Scenario: The handback seam precedes the attribute clear
- **WHEN** release_for_party_change runs full possession release
- **THEN** the implemented verified unpuppet-NPC/re-puppet-owner ladder precedes mirrored attribute clear

#### Scenario: Terminal escort operations compensate every affected surface
- **WHEN** an escort terminates and a handback or later owning write fails
- **THEN** Escort terminal operations SHALL compensate session puppet, lock grants, cmdsets, mirrored possession, membership and quest caches if handback or any later owning-transaction write fails.
