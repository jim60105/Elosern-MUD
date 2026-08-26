## MODIFIED Requirements

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be complete,
and SHALL each be reachable from a real control in the running application — a built, tested,
manifest-listed overlay that nothing imports is not complete. The settings overlay SHALL expose the
narrative prose scale, the reduced-motion preference, the text-to-HTML narrative toggle, and the
colourblind-safe status palette as **client-local presentation state**. It SHALL NOT dispatch a
`ui_action` for any of them: `options.dismiss` — the suggestions dismissal — is the only allowlisted
`options.*` action, and widening the action allowlist is a server-side change that no showcase or
redesign wave makes. Each setting SHALL be applied to the document's presentation tokens immediately,
SHALL be persisted through the client's versioned, presentation-only browser store as a harmless display
preference, and SHALL be re-applied at load and reset with that store when its stored version is
unrecognised. The reduced-motion preference SHALL be optional in the stored wrapper: when the key is
absent the operating system's `prefers-reduced-motion` preference SHALL continue to apply, and an explicit
stored value — either direction — SHALL override it. The surface SHALL offer no control it does not
implement, so a control with no outcome — a typeface choice the design system's role-assigned faces do
not support, an audio level with no audio subsystem, an interface-scale slider, or a key remapping — SHALL
NOT be rendered. The creation overlay SHALL implement a presets/custom/concept wizard with the adult gate
applied to BOTH the age and the apparent_age fields and an activate transition, and SHALL emit
`creation.*`. The `MapOverlay` SHALL re-render its available/unavailable branch whenever the `local_map`
OOB read model is updated, so a replaced payload never leaves a stale state; because the overlay is
mounted in the running client, this SHALL hold against live read-model replacement and not only against a
story's args. A surface with no backing OOB read model today — a dedicated Party/companion panel, the
intimate/adult status collapsible, the event-log Toasts surface, the design draft's category-to-entry
game-help browser (the `help` command's output reaches the client only as narrative text; no committed
panel carries it), and a persistent objective tracker — MUST NOT be built or mocked to look real, and each
SHALL be named in the deferred-surface assertion together with the read model it waits on; the help overlay
SHALL therefore render the client's own control reference, which the client authoritatively knows, and no
authored game-help content. The held-item bag is NOT among them: it is backed by the `services` panel's
`inventory` section, which the server builds for any actor in exploration mode independently of any service
host, so the bag SHALL be built from `services.inventory.rows`, bounded by the payload's row cap, with
`pagination.inventory_total` surfaced only as the count of rows actually shipped and never as a claim about
untruncated holdings. On completion of the contextual HUD redesign the required-component manifest SHALL
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
- **THEN** no Party panel, intimate/adult collapsible, event-log Toasts surface, authored game-help browser, or persistent objective tracker is present and none presents invented data

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `services` panel commits an `inventory` section
- **THEN** the bag renders that section's rows with their display names, held counts and equipped flags, bounded by the payload's row cap, and states the cap in words when the listing reaches it

#### Scenario: The manifest is re-frozen at the redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required-component manifest is re-frozen at the complete redesign set and the component-coverage gate enforces it

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

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, the `CharacterStatusDrawer` (housing the `EquipmentDoll`), and the `SkillBook`
components SHALL present the `status` panel payload (schema version 1), the `character` panel payload
(schema version 3), and the character's skill data: gauges (hp/mp/sp), counters (magic_level,
guild_merit), static traits, wallet, and conditions with their derived modifiers; character
details, the equipment doll's equipped items, disguise, guild rank/merit, and persona; and a skill
book with active/passive tabs, categories, search, and per-skill cost/target/cast detail. The
gauges and conditions come from the `status` payload; the counters, static traits, wallet, character
details, equipment, disguise, guild, and persona come from the `character` payload. Per-skill cost,
target, and cast detail fields are rendered only when the character's skill data provides them (a
row the data gives without detail renders without detail cells, so nothing is invented); where the
slice carries them they are the display subset of the `context_actions` v5 skill descriptor (a
`cost` object — the empty object is the free form —, `target_spec`, and the optional
`freeform_scales` / `shorthands`).

`StatusPanel` SHALL present its share of that data as the stage's left HUD island stack rather than
as a single boxed column card: a character head card, a vitals island, and a conditions island,
composed from the `CharacterHead`, `VitalsTrack`, and `ConditionChips` components. The head card
SHALL render only identity the payloads carry — the display name, the numeric magic level with its
client-derived display rank title, the guild rank and merit, the wallet, and the disguise marker —
with a glyph portrait rather than an image, and SHALL render no race, subrace, class, or faction
line, because no such field exists in either payload. The wallet SHALL have exactly one
persistently-visible surface.

Status and health information SHALL never be conveyed by color alone: gauges SHALL pair an icon and
a text label with an explicit current/maximum numeric value, each counter and static trait SHALL
render its numeric value, and each condition SHALL pair a non-color severity glyph — one distinct
glyph shape per severity, so two severities are never separated by color alone — with its label plus
every numeric or derived-modifier value the payload provides. Where a condition renders as an
icon-only chip, that label, duration, and modifier text SHALL be carried in the chip's accessible
name and SHALL also be presented visibly when the chip is focused or hovered, and any bounded
overflow SHALL keep every committed condition reachable in one action. A gauge's trailing damage
indicator SHALL be decorative, absent from the accessibility tree, and SHALL never display a value
that was not previously committed for that same gauge. Disguised statistics are display-only and
SHALL be shown distinct from true traits, and a disguised displayed value SHALL NOT be substituted
for a true trait on the head card.

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
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field, and any race, subrace, class, or faction line) is invented

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
