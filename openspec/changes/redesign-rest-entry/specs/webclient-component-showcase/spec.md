## MODIFIED Requirements

### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states.

#### Scenario: A required component always has a story
- **WHEN** the required-component manifest is enumerated
- **THEN** every listed component has at least one registered Storybook story, including the
  message window's story with its single-page, more-pages, last-page, error-page, oversize-page,
  pending-action, and dialogue name-plate states, the place card's story with and without its room actions,
  the question card's story with its dream question and locked states, the choice card's story with its verbs,
  suggestions, generating, degraded-empty, and overflow states, the time choice card's story with its
  default, locked, no-fatigue-row, and narrow states, the wait form's story with its default and locked states, the
  presence rail's story with its default, overflow, no-portraits, and objects-only states, the
  exploration screen's story with its default, person-focus, wait-card, dream-question, and suggestions-card states, and the stage actor's story with its player, host-image,
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
  message window; the command line; the action dock with its menu and submenu frames and its exploration
  root pane; the presence rail, the centred choice card, and the question card; the status panel with its gauges and
  conditions; the party window with its 背包 tab (including the equipment doll) and its 狀態 tab; the skill book; the
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
