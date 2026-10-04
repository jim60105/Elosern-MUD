## MODIFIED Requirements

### Requirement: Exploration browser acceptance is keyboard-only and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1451x790 and 2560x1440: grid, wilderness, instance, and interior movement through `explore.move` with matching time and map updates; look at the room and look at present entities; scripted keyword dialogue and free-form dialogue with offline degrade to greeting/silence; engage transitioning to the combat dock; wait/rest daypart and duration acceptance plus safety rejections; stale, duplicate, and tampered rejections; the 任務 and 背包 ‧ 裝備 drawers reachable through Quests/Inventory without a service submenu frame; and reconnect retention. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, SHALL assert that no take/drop control and no remote or ambiguous host control is rendered, and SHALL assert that `portrait_ref: null` produces no portrait card and no focus packet.

#### Scenario: A full exploration journey completes in Chromium
- **WHEN** a seeded actor uses arrows and Enter to move through an exit, look at the room, talk to a scripted host, open Quests, and wait until dawn
- **THEN** each step submits exactly one expected `ui_action`, the narrative and panels refresh together, and no typed command is required

#### Scenario: Offline dialogue still completes in the browser
- **WHEN** the LLM is offline and the player chooses free-form dialogue for an `LLMNPC`
- **THEN** the authored greeting or silence appears, the dock unlocks, and no remote request is made

#### Scenario: No take or drop control is rendered
- **WHEN** the exploration dock is open in any room
- **THEN** no `explore.take`/`explore.drop` affordance or generic object-mutation control exists anywhere in the rendered surface
