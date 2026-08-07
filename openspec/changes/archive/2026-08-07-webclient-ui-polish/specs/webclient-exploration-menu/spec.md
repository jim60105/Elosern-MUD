## MODIFIED Requirements

### Requirement: The exploration dock is keyboard-first and re-homes the service submenus
In exploration mode the exploration dock SHALL own the action-dock surface and SHALL present the stable root Move, Look, Interact, Character, Quests, Inventory, and Wait in that order, composed only from the validated `exploration` panel. Move SHALL open the exit list and submit `explore.move`; Look SHALL open room/entity/object inspection and submit `explore.look`; Interact SHALL first select a present target and then show only that target's server-authored affordances (scripted dialogue keywords as finite buttons, free-form dialogue, engage, or a `navigate`-kind guild/shop service entry); Character SHALL open the validated `character` panel; Quests and Inventory SHALL open the corresponding `services` panel submenus (guild quest log and inventory respectively); Wait SHALL open a rest/wait menu of the four named daypart boundaries plus a bounded custom-duration form and a sleep-to-full-regen entry, with every value parsed and validated server-side and no client-side clock arithmetic. A root entry whose capability surface is absent SHALL NOT render as a dead functional entry. Every exploration submenu — Move, Look, Interact, Wait, each target-affordance menu, and each scripted-keyword menu — SHALL end with an enabled back row that returns to its parent menu (the root has no back row), so pointer and keyboard users backtrack through the identical router path; Escape SHALL pop exactly one level. The dock SHALL render the approved command surface — the root as one equal-width row of grid cells beneath the shortcut guidance line, and each submenu as a grid of cells beside a detail pane that names the focused item and its availability — with the focused cell marked by a seal-red fill plus a leading glyph and disabled cells dimmed but focusable. The dock SHALL keep its rendered cells matched to the keyboard router's current frame at every navigation depth, so a back row, an Escape, or a pointer click on a parent row never leaves a deeper menu's cells on screen while the router navigates the parent. Arrow keys SHALL navigate, Enter SHALL open or submit, disabled entries SHALL remain focusable for their explanation but SHALL NOT submit, and held/repeated Enter and any mutation while one is in flight or awaiting its declared presentation revision SHALL be suppressed. The service dock SHALL be re-homed under the Interact/Quests/Inventory roots instead of a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged.

#### Scenario: Move, Look, and dialogue complete without typed input
- **WHEN** a player uses only arrows and Enter to open Move, select an exit, and later open Interact and choose a scripted keyword
- **THEN** the browser submits exactly `explore.move` then `explore.talk_scripted` with the server-authored IDs, and the refreshed panels appear without a typed command

#### Scenario: The dock renders the mockup grid with a guidance line and detail pane
- **WHEN** the exploration dock is mounted
- **THEN** the root renders as one equal-width row of grid cells beneath the shortcut guidance line, each submenu renders as a grid of cells beside a detail pane that names the focused item and its availability, the focused cell carries a seal-red fill plus a leading glyph, and disabled cells are dimmed but focusable

#### Scenario: A pointer user backs out of a submenu
- **WHEN** a player clicks the Look root entry, then clicks the back cell of the Look submenu
- **THEN** the router returns to the root frame, the dock renders the root cells again, no `ui_action` is sent, and no typed command is required

#### Scenario: A back cell returns to the exact parent menu
- **WHEN** a player navigates Interact → a target's affordances → scripted keywords and activates the back cell at each level
- **THEN** the dock returns to the target-affordance menu and then to the Interact target list, rendering that parent's cells at every step

#### Scenario: Escape keeps the rendered cells matched to the router frame at any depth
- **WHEN** the player presses Escape from a target-affordance or scripted-keyword submenu that is more than one level deep
- **THEN** exactly one menu level closes, the parent menu's cells render immediately, and the prior focused item is restored

#### Scenario: Escape from a re-homed service or character sub-view leaves the exploration root clean
- **WHEN** the player opens Character or a Quests/Inventory service submenu from the exploration root and presses Escape
- **THEN** the sub-view closes without sending an action, the exploration root remains the dock's current frame, and no exploration submenu bookkeeping is corrupted or re-rendered

#### Scenario: Disabled affordance explains without submitting
- **WHEN** focus moves to a disabled `explore.engage` affordance and the player presses Enter
- **THEN** its disabled reason remains readable and no `ui_action` message is emitted

#### Scenario: Quests and Inventory reach the services submenus
- **WHEN** the player opens Quests from the exploration root and the `services` panel is available
- **THEN** the quest-log submenu renders from the unchanged `services` panel payload and its `guild.quest_*` actions

#### Scenario: Mode change tears down the exploration dock atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration dock synchronously unloads, unregisters its keyboard handlers, discards local selection and speech state, and only the combat dock owns action-dock focus
