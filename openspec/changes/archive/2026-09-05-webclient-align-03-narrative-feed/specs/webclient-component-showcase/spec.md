# Delta spec: webclient-component-showcase (webclient-align-03-narrative-feed)

## MODIFIED Requirements

### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states. At the completion of the contextual HUD
redesign the required manifest SHALL enumerate at minimum: the header; the narrative feed and its
unread indicator; the command line (with its quick-word chips); the action dock with its menu,
submenu, and choice-card frames; the status panel with its gauges, counters,
and conditions; the character status drawer (including the equipment doll); the skill book; the
local map; the art panel; the shop, quest board, and lore drawer (each backed by the `services`
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
- **THEN** every listed component has at least one registered Storybook story

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
The action-dock components (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`)
SHALL present the `context_actions` v5 menus as a finite, framed grid with a guidance
line and focused/disabled states, and SHALL render the option and choice cards in the exact
server-authored shape. The action dock SHALL expose the preserved `action-` and `target-` item keys and the
focusable action-dock target, and SHALL expose a stable `data-testid` on every interactive cell. Every card and row SHALL be
backed only by the `context_actions` panel and SHALL emit, on activation, the exact OOB action intent — the
`action_id` and `payload` fields of the `ui_action` envelope (the transport-level fields are owned by the
C1 store) — so no action or target SHALL be invented.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

## Chain note

This delta modifies requirements not modified by webclient-align-05-party-hud or
webclient-align-09-objective-tracker-ui (no chain collision). Removing the
choice-point block from the minimum enumeration also removes it from the
showcase-coverage manifest minimum: after this change lands, the manifest SHALL NOT
contain a `ChoicePointBlock` entry.
