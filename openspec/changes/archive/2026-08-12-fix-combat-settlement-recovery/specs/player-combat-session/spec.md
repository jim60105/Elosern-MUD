## MODIFIED Requirements

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful flee, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle exactly once through `settle_combat_result()`, then active session/context state SHALL be
cleared. The settlement SHALL be idempotent: a terminal outcome SHALL record a durable settled marker so a
restart that re-reads the session can never settle the same rounds a second time.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the player's ordinary innate flee action succeeds
- **THEN** the session settles elapsed rounds, clears combat state, and leaves no second disengagement path

#### Scenario: A restarted terminal session is not settled twice
- **WHEN** a hostile session reached a terminal outcome and the process terminates before session clearing completes
- **THEN** after restart the session's accumulated time is settled exactly once, not again by session restoration

## ADDED Requirements

### Requirement: A round and its settlement form one atomic persistence unit

`submit_player_action` SHALL persist the round's action effects (HP/resources/knockouts/quest effects), the updated session metadata (round count, fled/knockout sets), and any terminal settlement (exam outcome, clock advance, session clearing) as a single durable transaction with snapshot/restore of all touched entities, so a process termination can never leave half-round durable state.

#### Scenario: Termination mid-round leaves no half-committed round

- **WHEN** a process terminates after some combatant effects committed but before the session record update
- **THEN** after restart either the full round (effects plus `rounds_elapsed`) is durable or none of it is

#### Scenario: Terminal settlement failure rolls back the round

- **WHEN** a terminal settlement step raises after round effects were applied
- **THEN** the round effects, session metadata, exam outcome, clock tick, and session clearing all roll back together
