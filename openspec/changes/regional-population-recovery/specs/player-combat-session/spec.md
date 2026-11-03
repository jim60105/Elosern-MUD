# Spec Delta

## MODIFIED Requirements

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. Every terminal outcome (either
side's defeat, party retreat, nonlethal exam, bounded condition) SHALL settle rounds times six
seconds once via `settle_combat_result()` and settle mental intervals once from recorded activity
accounting, waking naturally only after live combat ends and never for defeated bodies. Session
state SHALL then clear. A durable settled marker SHALL keep settlement idempotent across restart.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the confirmed party retreat succeeds
- **THEN** the session settles one added retreat round plus prior elapsed rounds, clears the whole party combat state, and leaves no allied personal disengagement bypass

#### Scenario: A restarted terminal session is not settled twice
- **WHEN** a hostile session reached a terminal outcome and the process terminates before session clearing completes
- **THEN** after restart the session's accumulated time is settled exactly once, not again by session restoration

#### Scenario: Companion gauges regenerate from combat settlement
- **WHEN** a session with a wounded or knocked-out companion reaches a terminal outcome
- **THEN** the companion's HP/MP/SP are regenerated for the accumulated combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

#### Scenario: Settlement scope is the living non-fled roster
- **WHEN** a terminal settlement runs
- **THEN** the settlement entity scope is every living, non-fled member of the session's battlefield
  roster (player, companions, and any non-defeated foe still present), so all participants receive
  gauge regen for the accumulated combat time

#### Scenario: Population loss carries actual round offset
- **WHEN** a mapped session records a defeat in a later round before terminal-only clock settlement
- **THEN** the persisted start tick and completed-round offset identify its occurrence for delayed population settlement, without advancing the live clock early or double-settling rounds

