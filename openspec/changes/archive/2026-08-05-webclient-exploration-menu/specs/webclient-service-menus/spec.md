## MODIFIED Requirements

### Requirement: Service action completion updates canonical panels and preserves narrative
After an admitted service action settles, the server SHALL emit every returned message through the ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before sending the matching safe `ui_action_result`. `guild.register`, `guild.quest_turnin`, `shop.buy`, and `shop.sell` SHALL publish `status` and `services`; `guild.quest_accept` and `guild.quest_abandon` SHALL publish `services`; `guild.exam_start` SHALL publish `status`, `services`, and `context_actions` together with the mode change to `combat`, and the browser SHALL then render the ordinary combat menu. Every success or domain-rejection message SHALL be emitted as text and never parsed by the browser to update panel state.

#### Scenario: Turn-in updates wallet and merit panels together
- **WHEN** a completed quest is turned in successfully
- **THEN** narrative carries the reward message, `status` and `services` reflect the new wallet, merit, claim, and quest-log state at one newer revision, and the dock unlocks only after that revision is accepted

#### Scenario: Exam start hands off to the combat menu
- **WHEN** `guild.exam_start` succeeds for the exact next rank
- **THEN** the update carries mode `combat` and a `context_actions` combat payload, `services` becomes unavailable, and no additional service mutation is admitted in that mode

#### Scenario: Mode change tears down the exploration dock and its service submenus atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration action dock — including the service submenus re-homed under its Interact/Quests/Inventory roots — synchronously unloads, unregisters its keyboard handlers, discards any local quantity, selection, confirmation, and speech state, and only the combat dock owns action-dock focus

#### Scenario: Rejected purchase emits no fabricated prose
- **WHEN** the economy API rejects for insufficient funds
- **THEN** no trade message is fabricated beyond the stable safe rejection, wallet and stock remain unchanged, and refreshed `services` state permits another legal choice

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1440x900 and 1280x720: registration success and idempotent re-registration, board list to detail to accept, active-quest abandon behind an explicit confirmation screen, completed-quest turn-in, merit/exam eligibility and the transition into the combat menu with the service dock torn down, shop open/closed status at fixed world times, buy and sell quantity validation with exact copper and stock outcomes, stale and duplicate submission behavior, repeated-inventory display, and reconnect retention. The service submenus SHALL be reached from the exploration dock's Interact/Quests/Inventory roots rather than a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, and SHALL assert that no use/equip control and no remote or ambiguous host control is rendered.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member uses arrows and Enter to open the exploration dock, open Quests, open Guild, open Board, and accept an eligible offer
- **THEN** the flow submits exactly `guild.quest_accept` once with the expected definition key and the refreshed quest log appears without typed input

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses an active quest's abandon action but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without abandoning

#### Scenario: Minimum viewport retains service essentials
- **WHEN** the services panel renders at 1280x720 with a disabled buy row focused
- **THEN** the player can read narrative, wallet, stock, the disabled reason, and the service controls without overlap preventing operation

#### Scenario: Shop is reached through the exploration dock's Interact root
- **WHEN** the actor stands in a general store and opens the exploration dock, then Interact, then Shop
- **THEN** the unchanged `services` shop surface renders stock, prices, quantity, and sell controls, and `shop.buy`/`shop.sell` submit exactly their existing payloads
