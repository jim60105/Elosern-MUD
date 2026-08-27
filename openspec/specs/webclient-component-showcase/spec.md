## Purpose

Establishes the component-showcase contract for the Vue migration: every UI component named in the required-component manifest is implemented as a Vue single-file component with at least one documented Storybook story, and every story is driven only by fixed, deterministic offline mock data. The showcase is completed before the application is wired to the live WebSocket transport, and the quality gate makes it a mandatory step by building Storybook and running a deterministic component-coverage check.
## Requirements
### Requirement: Every required UI component is a Vue SFC with a documented Storybook story
Every UI component named in the required-component manifest SHALL be implemented as a Vue
single-file component and SHALL have at least one Storybook story that documents its props, the
events/actions it emits, and its primary states. At the completion of the contextual HUD
redesign the required manifest SHALL enumerate at minimum: the header; the narrative feed and its
unread indicator; the command line (with its quick-word chips); the action dock with its menu,
submenu, and choice-card frames; the choice-point block; the status panel with its gauges, counters,
and conditions; the character status drawer (including the equipment doll); the skill book; the
local map; the art panel; the shop, quest board, and lore drawer (each backed by the `services`
panel); and each full overlay (map, settings, help, and creation). Each component SHALL render
only data sourced from the OOB panel allowlist (art, status, context_actions, local_map, services,
creation, exploration, character) or the transport text stream; a surface with no backing read
model is out of scope and MUST NOT invent data.

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
The `StatusPanel`, the `CharacterStatusDrawer` (housing the `EquipmentDoll`), and the `SkillBook`
components SHALL present the `status` panel payload (schema version 1), the `character` panel
payload (schema version 3), and the character's skill data: gauges (hp/mp/sp), counters (magic_level,
guild_merit), static traits, wallet, and conditions with their derived modifiers; character
details, the equipment doll's equipped items, disguise, guild rank/merit, and persona; and a skill
book with active/passive tabs, categories, search, and per-skill cost/target/cast/availability detail. The gauges and conditions come from the `status` payload; the counters,
static traits, wallet, character details, equipment, disguise, guild, and persona come from the
`character` payload. Per-skill cost, target, cast, and out-of-combat-availability detail fields are rendered only when the
character's skill data provides them (a row the data gives without detail renders without detail
cells, so nothing is invented); where the slice carries them they are the display subset of the
`context_actions` v5 skill descriptor (a `cost` object — the empty object is the free form —,
`target_spec`, the optional `freeform_scales`, and the boolean `usable_out_of_combat`). `shorthands`
is a combat-only field: the character panel's skill data SHALL NOT carry it, because the shorthand set
depends on a live battlefield/participant roster that does not exist outside combat. The character
panel's presenter SHALL populate `cost`, `target_spec`, `usable_out_of_combat`, and (for a freeform-
eligible skill the actor has mastery to scale) `freeform_scales` for every **active** skill row it can
resolve against the skill registry; a passive skill row SHALL carry only `key` and `label`, and an
active row whose key the registry cannot resolve SHALL carry only `key` and `label` as well (nothing is
invented for an unregistered key).

The skill book's category summaries, group labels, and per-skill rows SHALL NOT convey their meaning by
colour alone: a category summary pairs its skill count with the visible digit text and its
expand/collapse state with a rotating chevron shape (not a colour change); a cost cell's resource
colour-coding (MP/SP/free) always pairs with the resource unit or the word "免費" already present in
the cost text; the out-of-combat `combat` pill and the passive `被動` badge each carry their own visible
text, never a bare colour swatch. An elemental group's colour dot is decorative and SHALL be present
only for an element the binding visual reference (`docs/design/elosern-redesign/index.html`) itself
colour-codes; a group for any other element renders its text label with no dot — no dot colour is
invented for an element the reference never colour-codes. A skill row that carries target or cast detail
renders that detail on the name side of the row, with the cost cell as the row's rightmost column
(matching the reference's `.srow .cost` right-alignment via `margin-left:auto`). A group without a
label SHALL keep the pre-change 8px top spacing, so removing the group-container margin does not regress
ungrouped content.

`StatusPanel` SHALL present its share of that data as the stage's left HUD island stack rather than as
a single boxed column card: a character head card, a vitals island, and a conditions island, composed
from the `CharacterHead`, `VitalsTrack`, and `ConditionChips` components. The head card SHALL render
only identity the payloads carry — the display name, the numeric magic level with its client-derived
display rank title, the guild rank and merit, the wallet, and the disguise marker — with a glyph
portrait rather than an image, and SHALL render no race, subrace, class, or faction line, because no
such field exists in either payload. The wallet SHALL have exactly one persistently-visible surface.

Status and health information SHALL never be conveyed by color alone: gauges SHALL pair an icon and a
text label with an explicit current/maximum numeric value, each counter and static trait SHALL render
its numeric value, and each condition SHALL pair a non-color severity glyph — one distinct glyph shape
per severity, so two severities are never separated by color alone — with its label plus every numeric
or derived-modifier value the payload provides. Where a condition renders as an icon-only chip, that
label, duration, and modifier text SHALL be carried in the chip's accessible name and SHALL also be
presented visibly when the chip is focused or hovered, and any bounded overflow SHALL keep every
committed condition reachable in one action. A gauge's trailing damage indicator SHALL be decorative,
absent from the accessibility tree, and SHALL never display a value that was not previously committed
for that same gauge. Disguised statistics are display-only and SHALL be shown distinct from true
traits, and a disguised displayed value SHALL NOT be substituted for a true trait on the head card.
The character status drawer SHALL present the `character` payload's character details, the equipment
doll's equipped items, disguise, guild rank/merit, and persona, and SHALL NOT present a field the
payload does not carry. Each surface renders only its OOB-backed payload and SHALL NOT invent any
field (the intimate/adult block has no backing field and is not built).

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs an icon and a text label with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a distinct non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the drawer shows them as display values distinct from the true traits, the head card keeps the true trait value, and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field, any race, subrace, class, or faction line, and any `shorthands` value on a character-panel skill row) is invented

#### Scenario: The status surface renders as an island stack
- **WHEN** the `StatusPanel` renders with the `status` and `character` panels available
- **THEN** it renders the head card, the vitals, and the conditions as separate HUD islands composed from `CharacterHead`, `VitalsTrack`, and `ConditionChips`, and not as one boxed column card

#### Scenario: An icon-only condition chip keeps its text reachable
- **WHEN** a condition renders as an icon-only chip with a duration badge
- **THEN** its label, remaining duration, and every derived modifier are in its accessible name and are shown visibly when the chip is focused or hovered, and any hidden overflow is reachable in one action

#### Scenario: The trailing damage indicator carries no information of its own
- **WHEN** a gauge's trailing damage indicator renders
- **THEN** it is absent from the accessibility tree, shows only a previously committed ratio of that same gauge, and the numerals already carry the same information

#### Scenario: The character status drawer presents only the backed character fields
- **WHEN** the character status drawer renders with the `character` panel available
- **THEN** it presents the character details, the equipment doll's equipped items, disguise, guild rank/merit, and persona, and no field the payload does not carry is rendered

#### Scenario: An active skill row carries its registry-backed descriptor detail
- **WHEN** the character panel's presenter serializes an active skill row whose key resolves in the skill registry
- **THEN** the row carries `cost`, `target_spec`, `usable_out_of_combat`, and — when the skill is freeform-eligible and the actor holds scaling mastery — `freeform_scales`, and the `SkillBook` renders a `combat` pill for a row whose `usable_out_of_combat` is `true`

#### Scenario: A passive row and an unregistered active key stay bare
- **WHEN** the character panel's presenter serializes a passive skill row, or an active skill row whose key does not resolve in the skill registry
- **THEN** the row carries only `key` and `label`, and `SkillBook` renders it with no cost, target, cast, or `combat` pill

#### Scenario: A skill category and cost cell are never color-only
- **WHEN** a skill category summary or a skill row's cost cell renders
- **THEN** the category summary shows its skill count as a digit and its open/closed state as a rotating chevron shape, and the cost cell's colour always accompanies the `mp`/`sp`/`免費` text already in the cell — no state is conveyed by colour alone

#### Scenario: A group dot renders only for a reference-sampled element
- **WHEN** an elemental-magic group renders whose element the binding visual reference colour-codes (fire, water, wind) or whose category is `sexual_act`
- **THEN** its label is preceded by the reference's exact colour dot; a group for any other element renders with no dot, because no dot colour is invented for an element the reference never colour-codes

#### Scenario: A passive row carries a visible passive badge
- **WHEN** the skill book renders a skill row on the passive tab
- **THEN** the row displays a `被動` badge that carries its own visible text, never a bare colour swatch, and the badge is absent from active-tab rows

#### Scenario: The active tab shows the list-conventions legend
- **WHEN** the skill book's active tab renders its category list
- **THEN** a one-line legend explaining the grouping, out-of-combat, and hidden-content conventions appears above the list, and the passive tab renders no legend

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `ArtPanel`, and the `services`-backed panels (`ShopPanel`, `QuestBoard`, `LoreDrawer`, and
`InventoryPanel` — the held-item bag plus the equipment presentation) SHALL render only their OOB data. The local map SHALL render the
`local_map` v1 lattice with its states, actionable adjacent nodes, a legend + detail line, and
colorblind-safe (not-color-only) encoding. The art panel SHALL render the `art` payload as a cover-style
16:9 scene with its contextual portrait overlay, and SHALL render a truthful scene placeholder (never an
invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB
channel is unavailable. The shop, quest-board, and lore panels SHALL render only their `services` payload,
and the inventory panel SHALL render the `services` panel's `inventory.rows` — each row's `display_name`,
its `held` count and its `equipped` flag — bounded by the payload's row cap, together with the equipment
presentation built from the `character` panel's `equipment` rows (`slot`, `item_key`, `display_name`).
The inventory panel SHALL NOT render an item rarity, a per-item statistics line, or a comparison tooltip,
because the inventory rows carry no such field, and SHALL NOT render a use, consume, or equip control,
because the payload advertises no such action. No surface SHALL invent data (a dedicated party panel is
not built here).

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders the validated panel when available
- **WHEN** the `art` payload is available
- **THEN** the surface renders the scene cover-style 16:9 with its contextual portrait overlay and the scene label and alternative text outside the bitmap

#### Scenario: Services and inventory are backed only
- **WHEN** the shop, quest, lore, or inventory panel renders
- **THEN** the shop/quest/lore render only the `services` payload and the inventory renders only the `services` panel's inventory rows and the `character` panel's equipment rows, with no invented stock, quest, lore, bag row, rarity, statistic, or equipment slot

#### Scenario: Services unavailable surfaces render only the registry-owned reason
- **WHEN** the `services` OOB channel is unavailable
- **THEN** the shop, quest-board, lore, and inventory panels render only the registry-owned reason message, with no fabricated wallet, stock, quest, lore, rank, bag row, or equipped-item values

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete,
and SHALL each be reachable from a real control in the running application — a built, tested,
manifest-listed overlay that nothing imports is not complete.
The settings overlay SHALL expose the narrative prose scale, the reduced-motion preference, the
text-to-HTML narrative toggle, and the colourblind-safe status palette as **client-local presentation
state**. It SHALL NOT dispatch a `ui_action` for any of them: `options.dismiss` — the suggestions
dismissal — is the only allowlisted `options.*` action, and widening the action allowlist is a
server-side change that no showcase or redesign wave makes. Each setting SHALL be applied to the
document's presentation tokens immediately, SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference, and SHALL be re-applied at load and
reset with that store when its stored version is unrecognised. The reduced-motion preference SHALL be
optional in the stored wrapper: when the key is absent the operating system's `prefers-reduced-motion`
preference SHALL continue to apply, and an explicit stored value — either direction — SHALL override it. The surface SHALL offer no control it
does not implement, so a control with no outcome — a typeface choice the design system's role-assigned
faces do not support, an audio level with no audio subsystem, an interface-scale slider, or a key
remapping — SHALL NOT be rendered. The creation overlay SHALL implement a presets/custom/concept wizard
with the adult gate applied to BOTH the age and the apparent_age fields and an activate transition, and
SHALL emit `creation.*`. The `MapOverlay` SHALL re-render its available/unavailable branch whenever the
`local_map` OOB read model is updated, so a replaced payload never leaves a stale state; because the
overlay is mounted in the running client, this SHALL hold against live read-model replacement and not
only against a story's args. A surface with no backing OOB read model today — a dedicated Party/companion panel, the
event-log Toasts surface, the design draft's category-to-entry
game-help browser (the `help` command's output reaches the client only as narrative text; no committed
panel carries it), and a persistent objective tracker — MUST NOT be built or mocked to look real, and each
SHALL be named in the deferred-surface assertion together with the read model it waits on; the help overlay
SHALL therefore render the client's own control reference, which the client authoritatively knows, and no
authored game-help content. The held-item bag is
NOT among them: it is backed by the `services` panel's `inventory` section, which the server builds for
any actor in exploration mode independently of any service host, so the bag SHALL be built from
`services.inventory.rows`, bounded by the payload's row cap, with `pagination.inventory_total` surfaced
only as the count of rows actually shipped and never as a claim about untruncated holdings. The intimate/adult status collapsible is likewise NOT among the deferred surfaces: it is backed by the
`character` panel's `intimate` field (`webclient-exploration-menu`'s version-4 character-panel
requirement), and its completeness and absence-when-`null` behaviour are governed by
`webclient-contextual-hud`'s character-status drawer requirement, not this deferred-surface list. On completion of the contextual HUD redesign the required-component manifest SHALL
be re-frozen at the complete redesign set and the component-coverage gate SHALL enforce that frozen set.

#### Scenario: Creation gate rejects both underage fields
- **WHEN** the creation wizard submits an age or an apparent_age below 18
- **THEN** the adult gate rejects the record before activation

#### Scenario: Settings are client-local and honor reduced motion
- **WHEN** a settings control changes
- **THEN** no `ui_action` is dispatched for it, the change is applied to the app-wide presentation tokens immediately — reduced motion among them — and it is persisted through the versioned presentation-only browser store

#### Scenario: The settings surface renders nothing inert
- **WHEN** the settings overlay's controls are enumerated
- **THEN** every rendered control changes an outcome the client implements, and no typeface choice, audio level, interface-scale slider, or key-remapping control is present

#### Scenario: Every full overlay is reachable from a control
- **WHEN** the running application is enumerated for overlay entry points
- **THEN** each of the map, settings, help, and creation overlays is opened by a real control in the live surface tree, and none is present in the bundle without a trigger

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload while the mounted overlay is open
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no Party panel, event-log Toasts surface, authored game-help browser, or persistent objective tracker is present and none presents invented data

#### Scenario: The intimate/adult status collapsible is no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the intimate/adult status collapsible is absent from the deferred-surface list, because it now has a backing OOB read model (`character.intimate`), and its presence/absence behaviour is asserted by `webclient-contextual-hud`'s character-status drawer requirement instead

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `services` panel commits an `inventory` section
- **THEN** the bag renders that section's rows with their display names, held counts and equipped flags, bounded by the payload's row cap, and states the cap in words when the listing reaches it

#### Scenario: The manifest is re-frozen at the redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required-component manifest is re-frozen at the complete redesign set and the component-coverage gate enforces it

### Requirement: The frozen component set grows only through a governed redesign wave
The required-component manifest SHALL remain the authoritative frozen set, and it SHALL grow only
through a change named in the WebClient Contextual HUD Redesign roadmap's delivery table. A wave that
adds a component SHALL, in the same change, add its title to the manifest, ship its Storybook story
with deterministic offline args, and extend this capability's spec in lockstep — never a manifest edit
alone. A component SHALL NOT be wired into the live application before its story exists. On completion
of the redesign the manifest SHALL be re-frozen at the complete new set.

#### Scenario: A wave adds a component with its story in the same change
- **WHEN** a roadmap wave introduces a new component
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: A manifest edit without a story fails the gate
- **WHEN** a manifest title is added without a matching registered story
- **THEN** the component-coverage gate fails and the change cannot land

#### Scenario: A story without a manifest entry fails the gate
- **WHEN** a story is registered whose title is absent from the manifest
- **THEN** the component-coverage gate fails, so the frozen set cannot grow silently

