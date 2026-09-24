## MODIFIED Requirements

### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states. At the completion of the contextual HUD
redesign the required manifest SHALL enumerate at minimum: the header; the place card; the message window; the command line; the action dock with its menu,
submenu, and choice-card frames, its scene overview, and the scene overview's verb popover; the status panel with its gauges and conditions; the character status drawer (including the equipment doll); the skill book; the
local map; the scene backdrop and the reference artwork frame; the shop, quest board, and lore drawer (each backed by the `services`
panel); and each full overlay (map, settings, help, and creation). Each component SHALL render
only data sourced from the OOB panel allowlist (art, status, context_actions, local_map, services,
creation, exploration, character) or the transport text stream; a surface with no backing read
model is out of scope and MUST NOT invent data.

A story of a component that consumes a derived render model (a view model the
application builds from a committed payload through a DOM-independent reducer)
SHALL be bound to that same derived shape, not to the raw payload: story args
MUST reproduce the exact prop shape the live wiring passes, so a story that
renders a degenerate or partial surface because it skipped the application's
derivation step is a contract violation and not a presentation choice. The
derived-shape binding SHALL come from one shared story fixture helper reused by
every story of that component family.

#### Scenario: A required component always has a story
- **WHEN** the required-component manifest is enumerated
- **THEN** every listed component has at least one registered Storybook story, including the
  message window's story with its single-page, more-pages, last-page, error-page, oversize-page,
  pending-action, and dialogue states, the scene overview's story with its full-room, empty-rows,
  disabled-exit, and overflowing states, and the verb popover's story with its dialogue-host,
  hostile-target, and look-only states

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

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract
The action-dock components (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`,
`SceneOverview`, and `DockVerbPopover`)
SHALL present the `context_actions` v5 menus and the `exploration` panel's scene overview as a finite
set of framed rows or chips with a guidance line and focused/disabled states, and SHALL render the
option and choice cards in the exact server-authored shape. The action dock SHALL expose the preserved
`action-` and `target-` item keys and the
focusable action-dock target, and SHALL expose a stable `data-testid` on every interactive cell. Every card, row, and chip SHALL be
backed only by the `context_actions` or `exploration` panel and SHALL emit, on activation, the exact OOB action intent — the
`action_id` and `payload` fields of the `ui_action` envelope (the transport-level fields are owned by the
C1 store) — or the local frame-opening intent its row carries, so no action or target SHALL be invented.

The scene overview SHALL render its chips in the rows the overview menu names (出口, 人物, 物件, and a
label-less footer) in the menu's reading order, SHALL render no row whose section is absent, and SHALL
let the chips of a row wrap onto further lines inside the command panel rather than overflow it
horizontally. An exit chip SHALL carry the exit's direction glyph and, while enabled, the destination's
display name, under the same glyph, destination, and disabled-label rules as the move row form. A
disabled chip SHALL stay focusable, SHALL carry its disabled marker in text, and SHALL expose its
server-authored reason to assistive technology and, while focused, in the overview's reason strip. The
verb popover SHALL render a head naming its target and that target's rows in the menu's order, and
SHALL request the parent frame (emit its back intent) when the pointer presses outside the popover
card inside its host.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: The scene overview renders only its non-empty rows
- **WHEN** the scene overview renders a menu whose sections are exits, objects, and the footer, with no people section
- **THEN** the 出口 and 物件 rows and the footer render in that order, no 人物 row or label is present, and each chip carries its row key and row id in reading order

#### Scenario: A disabled exit chip explains itself without submitting
- **WHEN** the scene overview renders a disabled exit chip and the pointer clicks it
- **THEN** the chip becomes the focused chip, its label carries the disabled marker, the reason strip shows the server-authored reason, and no activation intent is emitted

#### Scenario: The verb popover closes on an outside press
- **WHEN** the verb popover is open inside its host and the pointer presses inside the host but outside the popover card
- **THEN** the popover emits its back intent once and emits no activation
