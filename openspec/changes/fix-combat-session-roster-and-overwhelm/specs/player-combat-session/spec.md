## MODIFIED Requirements

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player
input. After one player request passes preflight, a decided encounter SHALL call the landed overwhelm
resolver **only when the player's team is the overwhelming side**. The selected request SHALL be used for
the first simulated player turn; subsequent compressed player turns SHALL use deterministic
`basic_attack` against the lowest-HP living enemy. Every turn SHALL remain a normal ActionRequest and
emit compressed EventLogs; no path SHALL directly assign HP or bypass quest planners. A foe-overwhelming
(reverse) verdict is informational only: the session SHALL NOT invoke the compressed resolver for it, and
the encounter SHALL play out one ordinary round per player submission, preserving the player's full
per-round agency (skill choice and flee) so no fight is an unavoidable compressed defeat. Undecided
encounters SHALL pause for player input between ordinary rounds.

#### Scenario: Overwhelming player resolves a reachable hunt
- **WHEN** engagement classifies the player's team as overwhelming and the player selects a valid first
  action
- **THEN** only then does the encounter resolve through ActionResolver, emit defeat identity for an
  ordinary lethal target, advance quest progress, and settle its rounds

#### Scenario: Engage alone never runs an overwhelming round
- **WHEN** an overwhelming target is engaged but the player has not submitted an action
- **THEN** neither team acts, no EventLog is emitted, and world time and round count remain unchanged

#### Scenario: Foe-overwhelming encounter plays round-by-round
- **WHEN** engagement classifies the foe team as overwhelming and the player submits a preflight-valid action
- **THEN** exactly one ordinary round resolves, the player may choose a different skill or flee next round,
  and the compressed resolver is never invoked

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action

## ADDED Requirements

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful flee, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`, and the settlement entity scope SHALL be
every living, non-fled member of the session's battlefield roster (player, companions, and any
non-defeated foe still present), so all participants receive gauge regen for the accumulated combat
time. Then active session/context state SHALL be cleared.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the player's ordinary innate flee action succeeds
- **THEN** the session settles elapsed rounds, clears combat state, and leaves no second disengagement path
#### Scenario: Companion gauges regenerate from combat settlement

- **WHEN** a session with a wounded or knocked-out companion reaches a terminal outcome
- **THEN** the companion's HP/MP/SP are regenerated for the accumulated combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

### Requirement: Overwhelm compression is player-direction only

The session facade SHALL invoke the overwhelm resolver only when `classify_overwhelm` returns the player's team; any other verdict (contested or foe-overwhelming) SHALL NOT trigger compression.

#### Scenario: Foe-overwhelming verdict never dispatches the resolver

- **WHEN** the player submits a preflight-valid action in a session classified as foe-overwhelming
- **THEN** the session runs one ordinary round and never calls the overwhelm resolver, for that round or any later round while the verdict holds
