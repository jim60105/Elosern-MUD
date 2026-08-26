## MODIFIED Requirements

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1440x900 and 1280x720: registration success and idempotent re-registration, board list to detail to accept, active-quest abandon behind an explicit confirmation screen, completed-quest turn-in, merit/exam eligibility and the transition into the combat menu with the service dock torn down, shop open/closed status at fixed world times, buy and sell quantity validation with exact copper and stock outcomes, stale and duplicate submission behavior, repeated-inventory display, and reconnect retention. The service submenus SHALL be reached from the exploration dock's Interact/Quests/Inventory roots rather than a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged. While such a service frame is the keyboard router's current frame it SHALL render inside the right-anchored reference drawer that presents the same surface, which SHALL host that frame's rows through the same shared row renderer the dock uses and SHALL NOT introduce a second frame stack, a second focus model, or a second set of menu keys; the drawer SHALL trap focus while open, Escape SHALL close it and pop exactly one menu level, and leaving the surface SHALL close it. The drawer's own pointer affordances SHALL emit the same server-authored action identifiers and payloads as the hosted rows, through the same dispatch entry, and SHALL be locked by the same in-flight, epoch, and revision gates. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, and SHALL assert that no use/equip control and no remote or ambiguous host control is rendered, and that no service surface is present in the DOM while its drawer is closed.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member uses arrows and Enter to open the exploration dock, open Quests, open Guild, open Board, and accept an eligible offer
- **THEN** the flow submits exactly `guild.quest_accept` once with the expected definition key and the refreshed quest log appears without typed input, with each frame's rows rendered inside the quest drawer that opened with the Quests frame

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses an active quest's abandon action but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without abandoning

#### Scenario: The drawer's pointer path is confirmation-protected too
- **WHEN** the player activates the abandon affordance on an active quest with the pointer inside the quest drawer
- **THEN** an explicit confirmation step renders naming the quest, no mutation is sent until it is confirmed, and cancelling returns without submitting

#### Scenario: Minimum viewport retains service essentials
- **WHEN** the shop drawer is open at 1280x720 with a disabled buy row focused
- **THEN** the player can read the stock, the exact copper values, the disabled reason, and the service controls inside the drawer without overlap preventing operation, closing the drawer is one action that restores the narrative caption and returns focus to the control that opened it, and the wallet stays reachable from the character-status drawer

#### Scenario: No service surface is mounted while its drawer is closed
- **WHEN** the exploration dock is at its root frame with every reference drawer closed
- **THEN** no shop, quest-board, lore, or inventory surface exists in the DOM or in the tab order, and no fabricated stock, quest, lore, or bag row is rendered anywhere
