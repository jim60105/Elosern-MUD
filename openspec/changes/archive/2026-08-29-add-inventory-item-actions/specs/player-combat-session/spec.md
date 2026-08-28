## MODIFIED Requirements

### Requirement: One preflight-valid player action drives one complete ordinary combat round
During active combat, a selected skill SHALL build one player `ActionRequest` and a selected usable item SHALL build one `ItemUseRequest`. The combat-session facade SHALL call the matching side-effect-free preflight before any initiative action. A preflight rejection SHALL not run NPC actions/upkeep or consume a round. After successful preflight, a session action provider SHALL supply the selected request once for the player and deterministic behavior-policy `ActionRequest` values for every other participant — monsters and allied companions alike, each at most one per round, with targets selected from the opposing team. `run_round()` SHALL preserve initiative, resolution, and upkeep and SHALL dispatch the closed request union explicitly to `ActionResolver` or the deterministic item-use resolver. If an earlier initiative action makes the preflight-valid request reject at the player's turn, the already-started round SHALL remain consumed.

#### Scenario: Player chooses a skill action before NPC turns run
- **WHEN** the player submits a valid combat cast
- **THEN** initiative may place any combatant first, but the queued request is returned exactly once and every eligible non-player participant receives at most one policy action that round

#### Scenario: Player chooses an item action before NPC turns run
- **WHEN** the injured player submits a valid combat item use
- **THEN** initiative may place any combatant first, the queued item request is returned exactly once at the player's position, and every eligible non-player participant receives at most one policy action that round

#### Scenario: Companions receive policy actions like monsters
- **WHEN** a round runs with the player, allied companions, and hostile monsters
- **THEN** each companion and each monster receives at most one deterministic policy request, and companion requests target the opposing team

#### Scenario: A knocked-out companion receives no action
- **WHEN** a round runs after a companion was knocked out
- **THEN** the companion is absent from initiative action, receives no policy request, and is not a selectable target for the player's shortcuts or the opposing team's targeting

#### Scenario: Invalid selected action preserves the round before initiative
- **WHEN** skill or item preflight rejects the player action
- **THEN** no NPC acts, round count and world clock remain unchanged, no item is consumed, and the player may choose again

#### Scenario: Mid-round invalidation does not roll back prior turns
- **WHEN** preflight succeeds but an earlier initiative action makes the player's selected skill or item request invalid
- **THEN** the player's resolution may reject, prior actions and upkeep remain committed, and the round count increases once

### Requirement: Overwhelm waits for one player choice before compressed resolver-backed outcome
At engagement the session SHALL record overwhelm classification but SHALL run no action before player input. After one selected skill or item request passes its matching preflight, a decided encounter SHALL call the landed overwhelm resolver only when the player's team is the overwhelming side. The selected request SHALL be used for the first simulated player turn; subsequent compressed player turns SHALL use deterministic `basic_attack` against the lowest-HP living enemy. Every turn SHALL remain a member of the closed deterministic request union and SHALL emit compressed EventLogs; no path SHALL directly assign HP, consume inventory outside the item resolver, or bypass quest planners. The facade SHALL pass the selected action's actor key, `action_kind` (`skill` or `item`), and `action_key` to the resolver so the compressed log emits exactly one matching first-round `commanded_action` entry. This identity plumbing SHALL affect only log identity, never round sequence, combat math, or settlement. A foe-overwhelming verdict SHALL remain informational and play one ordinary round per player submission, preserving full skill, flee, and item choice. Undecided encounters SHALL pause for player input between ordinary rounds.

#### Scenario: Overwhelming player resolves after a selected skill
- **WHEN** the player's team is overwhelming and the player selects a valid skill
- **THEN** only then does compression resolve through deterministic resolvers, emit ordinary defeat and quest effects, and settle its rounds

#### Scenario: Overwhelming player uses a selected item once
- **WHEN** the player's team is overwhelming and the injured player selects a valid healing potion
- **THEN** the first compressed player turn resolves the item once, subsequent player turns use basic attack, and inventory consumption remains inside the outer combat transaction

#### Scenario: Engage alone never runs an overwhelming round
- **WHEN** an overwhelming target is engaged but the player has not submitted an action
- **THEN** neither team acts, no EventLog is emitted, and world time and round count remain unchanged

#### Scenario: Compressed log marks the selected action kind and key
- **WHEN** an overwhelming encounter compresses after a valid selected skill or item
- **THEN** compressed EventLogs contain exactly one first-round `commanded_action` matching the player's key, action kind, and action key without changing rounds, HP mutations, or settlement

#### Scenario: Foe-overwhelming encounter preserves item choice
- **WHEN** the foe team is overwhelming and the player submits a preflight-valid skill or item
- **THEN** exactly one ordinary round resolves, the player may choose a different skill, item, or flee next round, and compression is never invoked

#### Scenario: Non-overwhelming encounter waits for another command
- **WHEN** one round ends with both teams active and no player-direction overwhelm verdict
- **THEN** the session persists and no additional round runs before the player's next action
