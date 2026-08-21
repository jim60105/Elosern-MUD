## ADDED Requirements

### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states. At the completion of the showcase wave the required
manifest SHALL enumerate at minimum: the header; the narrative feed and its unread indicator; the
command drawer; the action dock with its menu, submenu, and choice-card frames; the choice-point
block; the status panel with its gauges, counters, and conditions; the character panel (including
equipped items); the skill book; the local map; the art panel; the shop, quest board, and lore drawer
(each backed by the `services` panel); and each full overlay (map, settings, help, and creation). Each
component SHALL render only data sourced from the OOB panel allowlist (art, status, context_actions,
local_map, services, creation, exploration, character) or the transport text stream; a surface with no
backing read model is out of scope and MUST NOT invent data.

#### Scenario: A required component always has a story
- **WHEN** the required-component manifest is enumerated
- **THEN** every listed component has at least one registered Storybook story

#### Scenario: A story documents contract and primary states
- **WHEN** a component story is rendered
- **THEN** the component is bound to representative prop values and exposes at least its primary states

#### Scenario: A surface with no backing read model is absent
- **WHEN** the 設計稿 shows a surface that has no backing OOB read model today
- **THEN** that surface is not among the required components and no component presents invented data for it

### Requirement: The component showcase is completed before live wiring and is a mandatory CI gate
The component showcase SHALL be completed before the application is wired to the live WebSocket
transport — the component-design phase. The quality gate SHALL build the Storybook (or a Storybook
static build) and SHALL run a deterministic component-coverage check that fails when a required
(manifest-listed) component is unregistered or undocumented.

#### Scenario: Showcase gate runs in CI
- **WHEN** the quality workflow runs
- **THEN** the Storybook build step executes and the component-coverage check passes only for a complete required component manifest

#### Scenario: A missing component fails the gate
- **WHEN** a manifest-listed component has no registered story
- **THEN** the component-coverage check fails the build

### Requirement: Storybook stories use deterministic offline data only
Storybook stories SHALL use fixed, deterministic mock data and SHALL NOT invoke any live Evennia
server, an LLM, an image generator, or any other network service. Story rendering SHALL work with all
non-local network requests blocked.

#### Scenario: Stories need no live server
- **WHEN** a story is rendered
- **THEN** it is driven entirely by embedded mock data with no network or live-server dependency

#### Scenario: Offline rendering succeeds
- **WHEN** a story renders with all non-local network requests blocked
- **THEN** it renders from local assets without failure
