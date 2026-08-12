# player-combat-session Delta Specification

## MODIFIED Requirements

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player
input. After one player request passes preflight, a decided encounter SHALL call the landed overwhelm
resolver **only when the player's team is the overwhelming side**. The selected request SHALL be used for
the first simulated player turn; subsequent compressed player turns SHALL use deterministic
`basic_attack` against the lowest-HP living enemy. Every turn SHALL remain a normal ActionRequest and
emit compressed EventLogs; no path SHALL directly assign HP or bypass quest planners. The facade SHALL
pass the selected action's actor key and skill key to the resolver so the compressed log marks the
commanded action with a `commanded_action` entry, matched only among the encounter's first-round
logs; this identity plumbing SHALL affect only the log record, never the round sequence, combat
math, or settlement. A foe-overwhelming
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

#### Scenario: The compressed log marks the player's commanded action
- **WHEN** an overwhelming encounter compresses after the player selects a valid action
- **THEN** the compressed EventLogs contain exactly one `commanded_action` entry, prepended to the
  first first-round log matching the player's key and the selected skill, and the encounter's
  rounds, HP mutations, and settlement are identical to the same encounter resolved without the
  identity plumbing

#### Scenario: Foe-overwhelming encounter plays round-by-round
- **WHEN** engagement classifies the foe team as overwhelming and the player submits a preflight-valid action
- **THEN** exactly one ordinary round resolves, the player may choose a different skill or flee next round,
  and the compressed resolver is never invoked

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action
