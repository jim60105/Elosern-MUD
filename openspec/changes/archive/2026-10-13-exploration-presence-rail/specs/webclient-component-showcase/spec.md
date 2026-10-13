## MODIFIED Requirements

### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states.

#### Scenario: A required component always has a story
- **WHEN** the required-component manifest is enumerated
- **THEN** every listed component has at least one registered Storybook story, including the
  message window's story with its single-page, more-pages, last-page, error-page, oversize-page,
  pending-action, and dialogue name-plate states, the scene overview's story with its full-room and empty-rows
  states, the choice card's story with its verbs, wait, suggestions, and overflow states, the
  presence rail's story with its default, overflow, no-portraits, and objects-only states, the
  exploration screen's story with its default and person-focus states, and the stage actor's story with its player, host-image,
  host-pending-placeholder, host-missing-entry, speaking, and dimmed states, the foe line-up's story
  with its one-foe, two-foe, three-foe, capped-at-three, pending-placeholder, and missing-entry states, and the
  dialogue choice list's story with its picks, no-picks, move-exits, disabled-exit, and overflowing states

#### Scenario: A story documents contract and primary states
- **WHEN** a component story is rendered
- **THEN** the component is bound to representative prop values and exposes at least its primary states

#### Scenario: A surface with no backing read model is absent
- **WHEN** the 設計稿 shows a surface that has no backing OOB read model today
- **THEN** that surface is not among the required components and no component presents invented data for it

#### Scenario: A model-consuming component is story-bound to the model
- **WHEN** a component's live wiring passes a reducer-derived view model and one
  of its stories instead passes the raw committed payload
- **THEN** the showcase contract is violated: the story renders a partial
  surface, and the fix is to bind the story args through the shared derived-shape
  helper the application's derivation produces

#### Scenario: The manifest enumerates the contextual HUD redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required manifest SHALL enumerate at minimum: the header; the place card; the
  message window; the command line; the action dock with its menu, submenu, and choice-card frames,
  its scene overview; the presence rail and the centred choice card; the status panel with its gauges and
  conditions; the character status drawer (including the equipment doll); the skill book; the
  local map; the scene backdrop, the reference artwork frame, the stage actor that stands a portrait
  on the stage, the foe line-up that stands the combat foes on the stage, and the dialogue choice
  list over the stage; the shop, quest board, and lore drawer (each backed by the `services`
  panel); and each full overlay (map, settings, help, and creation)

#### Scenario: Components source only allowlisted panels or the text stream
- **WHEN** any required component renders
- **THEN** it renders only data sourced from the OOB panel allowlist (art, status,
  context_actions, local_map, services, creation, exploration, character, dialogue) or the
  transport text stream, and a surface with no backing read model is out of scope and MUST NOT
  invent data

#### Scenario: Model-binding stories reproduce the live prop shape
- **WHEN** a component consumes a derived render model — a view model the application builds
  from a committed payload through a DOM-independent reducer
- **THEN** that component's stories SHALL be bound to that same derived shape, not to the raw
  payload: story args MUST reproduce the exact prop shape the live wiring passes, and a story that
  renders a degenerate or partial surface because it skipped the application's derivation step is a
  contract violation and not a presentation choice

#### Scenario: One shared fixture helper carries the derived-shape binding
- **WHEN** several stories of one component family bind to a derived render model
- **THEN** the derived-shape binding SHALL come from one shared story fixture helper reused by
  every story of that component family

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract

The action-dock family (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`, `ExitCompass`,
`ExplorationReadout`, `SceneOverview`) SHALL present the `context_actions` v5 menus and, in
exploration, the `exploration` panel's scene overview as an exit compass beside finite footer
chips sharing one readout (the people and objects stand on the `Core/PresenceRail` story's rail), with the mode's guidance line, focused/disabled states, and the exact
server-authored option and choice card shape.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: The scene overview renders only its non-empty rows
- **WHEN** the scene overview renders for a room with people, objects, and exits beside a compass
- **THEN** only the footer row renders, with no 人物, 物件, or 出口 row or label, and each chip carries its row key and row id

#### Scenario: A disabled exit chip explains itself without submitting
- **WHEN** a disabled compass target is aimed or clicked
- **THEN** the shared readout shows its unchanged server reason and no move intent is emitted

#### Scenario: The verb popover closes on an outside press
- **WHEN** the centred choice card is open and the player presses Escape or activates its trailing `✕ 返回` row
- **THEN** the card emits its back intent once and emits no activation

#### Scenario: The dock exposes its keys, target, and test ids
- **WHEN** the action dock renders
- **THEN** it exposes the preserved `action-` and `target-` item keys and the focusable
  action-dock target, and a stable `data-testid` on every interactive cell

#### Scenario: Every cell is panel-backed and emits only real intents
- **WHEN** any action-dock card, row, or chip activates
- **THEN** it is backed only by the `context_actions` or `exploration` panel and emits, on
  activation, the exact OOB action intent — the `action_id` and `payload` fields of the
  `ui_action` envelope (the transport-level fields are owned by the C1 store) — or the local
  frame-opening intent its row carries, so no action or target is invented

#### Scenario: Overview chips wrap inside the command panel
- **WHEN** a scene-overview row's chips exceed its width
- **THEN** they wrap onto further lines inside the command panel rather than overflow it
  horizontally

#### Scenario: An exit chip follows the move row form's rules
- **WHEN** the compass resolves and aims a committed move row
- **THEN** its target and readout obey `webclient-exit-compass`, including bearing, direction and portal resolution, destination fallback, and disabled reason presentation

#### Scenario: The verb popover names its target and its rows
- **WHEN** the choice card renders a target's verb rows
- **THEN** it renders that target's rows in the menu's order with digit badges, followed by the trailing `✕ 返回` row under a hairline rule

#### Scenario: A disabled chip exposes its reason to assistive technology
- **WHEN** the scene overview renders a disabled chip
- **THEN** the chip stays focusable, carries its disabled marker in text, and exposes its
  server-authored reason to assistive technology and, while focused, in the overview's reason
  strip
