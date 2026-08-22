## Purpose

Establishes the component-showcase contract for the Vue migration: every UI component named in the required-component manifest is implemented as a Vue single-file component with at least one documented Storybook story, and every story is driven only by fixed, deterministic offline mock data. The showcase is completed before the application is wired to the live WebSocket transport, and the quality gate makes it a mandatory step by building Storybook and running a deterministic component-coverage check.

## Requirements

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

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract
The action-dock components (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`,
`ChoicePointBlock`) SHALL present the `context_actions` v5 menus as a finite, framed grid with a guidance
line and focused/disabled states, and SHALL render the option and choice cards in the exact
server-authored shape. The action dock SHALL expose the preserved `action-` and `target-` item keys and the
focusable action-dock target, and SHALL expose a stable `data-testid` on every interactive cell. The
choice-point block SHALL show ready and generating states and remain movable. Every card and row SHALL be
backed only by the `context_actions` panel and SHALL emit, on activation, the exact OOB action intent — the
`action_id` and `payload` fields of the `ui_action` envelope (the transport-level fields are owned by the
C1 store) — so no action or target SHALL be invented.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: Choice-point shows generating then ready
- **WHEN** a choice-point transitions from generating to ready
- **THEN** the block renders the generating state then the ready state and remains movable

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, `CharacterPanel`, and `SkillBook` components SHALL present the `status` panel
payload (schema version 1), the `character` panel payload (schema version 3), and the character's
skill data: gauges (hp/mp/sp), counters (magic_level, guild_merit), static traits, wallet, and
conditions with their derived modifiers; character details, equipped items, disguise, guild
rank/merit, and persona; and a skill book with active/passive tabs, categories, search, and per-skill
cost/target/cast detail. The gauges and conditions come from the `status` payload; the counters,
static traits, wallet, character details, equipment, disguise, guild, and persona come from the
`character` payload. Per-skill cost, target, and cast detail fields are rendered only when the
character's skill data provides them (a row the data gives without detail renders without detail
cells, so nothing is invented); where the slice carries them they are the display subset of the
`context_actions` v5 skill descriptor (a `cost` object — the empty object is the free form —,
`target_spec`, and the optional `freeform_scales` / `shorthands`). Status and health information
SHALL never be conveyed by color alone: gauges SHALL pair a symbol with an explicit current/maximum
numeric value, each counter and static trait SHALL render its numeric value, and each condition
SHALL pair a non-color severity glyph with its label plus every numeric or derived-modifier value
the payload provides. Disguised statistics are display-only and SHALL be shown distinct from true
traits. Each surface renders only its OOB-backed payload and SHALL NOT invent any field (the
intimate/adult block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs a symbol with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the panel shows them as display values distinct from the true traits and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field) is invented

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and the `services`-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and
`InventoryPanel` — equipped items only) SHALL render only their OOB data. The local map SHALL render the
`local_map` v1 lattice with its states, actionable adjacent nodes, a legend + detail line, and
colorblind-safe (not-color-only) encoding. The art panel SHALL render the `art` payload as a cover-style
16:9 scene with its contextual portrait overlay, and SHALL render a truthful scene placeholder (never an
invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB
channel is unavailable. The shop, quest-board, and lore panels SHALL render only their `services` payload,
and the inventory panel SHALL render only equipped items. No surface SHALL invent data (a full inventory
bag and a dedicated party panel are not built here).

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders the validated panel when available
- **WHEN** the `art` payload is available
- **THEN** the surface renders the scene cover-style 16:9 with its contextual portrait overlay and the scene label and alternative text outside the bitmap

#### Scenario: Services and inventory are backed only
- **WHEN** the shop, quest, lore, or inventory panel renders
- **THEN** the shop/quest/lore render only the `services` payload and the inventory renders only equipped items, with no invented stock, quest, lore, or bag contents

#### Scenario: Services unavailable surfaces render only the registry-owned reason
- **WHEN** the `services` OOB channel is unavailable
- **THEN** the shop, quest-board, lore, and inventory panels render only the registry-owned reason message, with no fabricated wallet, stock, quest, lore, rank, or equipped-item values
