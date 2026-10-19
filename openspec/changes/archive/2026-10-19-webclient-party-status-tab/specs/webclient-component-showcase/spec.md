# Spec Delta

## MODIFIED Requirements

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, the party window's `PartyStatusTab`, and the `SkillBook`
components SHALL present the `status` panel payload (schema version 1), the `character` panel
payload (schema version 9), and the character's skill data, each surface rendering only its
OOB-backed payload and inventing no field.

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs an icon and a text label with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a distinct non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the status tab shows them as display values distinct from the true traits, every true trait row keeps its true value, and no disguised value alters combat resolution

#### Scenario: Only backed fields render
- **WHEN** the status, character, or skill surface renders
- **THEN** every shown field comes from the `status`/`character`/`skill` OOB payload and no field (including any intimate/adult field, any race, subrace, class, or faction line, and any `shorthands` value on a character-panel skill row) is invented

#### Scenario: The status surface renders as an island stack
- **WHEN** the `StatusPanel` renders with the `status` panel available, a vital below its maximum, and one condition
- **THEN** it renders the vitals and the conditions as separate HUD islands composed from `VitalsTrack` and `ConditionChips`, not as one boxed column card, and renders no identity card and no wallet

#### Scenario: An icon-only condition chip keeps its text reachable
- **WHEN** a condition renders as a chip whose name is ellipsised, with a duration badge
- **THEN** its full label, remaining duration, and every derived modifier are in its accessible name and are shown visibly when the chip is focused or hovered, and any hidden overflow is reachable in one action

#### Scenario: The trailing damage indicator carries no information of its own
- **WHEN** a gauge's trailing damage indicator renders
- **THEN** it is absent from the accessibility tree, shows only a previously committed ratio of that same gauge, and the numerals already carry the same information

#### Scenario: The character status drawer presents only the backed character fields
- **WHEN** the party window's status tab renders with the `character` panel available
- **THEN** it presents the viewed member's hero row, gauges, trait waterfall, conditions, disguise and guild rank/merit, and no field the payload does not carry is rendered; equipped items are presented by the bag tab and persona by the member tab

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

#### Scenario: Per-skill detail comes only from the v5 skill descriptor
- **WHEN** the skill book renders per-skill cost, target, cast, and out-of-combat-availability
  detail
- **THEN** those fields render only when the character's skill data provides them (a row the data
  gives without detail renders without detail cells, so nothing is invented), and where the slice
  carries them they are the display subset of the `context_actions` v6 skill descriptor (unchanged by version 6 for the skill book): a `cost`
  object — the empty object is the free form —, `target_spec`, the optional `freeform_scales`, and
  the boolean `usable_out_of_combat`

#### Scenario: The character panel's skill data never carries shorthands
- **WHEN** the character panel serializes skill data
- **THEN** it carries no `shorthands` field, because `shorthands` is a combat-only field whose set
  depends on a live battlefield/participant roster that does not exist outside combat

#### Scenario: The out-of-combat pill carries its own visible text
- **WHEN** a skill row renders its out-of-combat `combat` pill
- **THEN** the pill carries its own visible text, never a bare colour swatch

#### Scenario: Target and cast detail sits on the name side
- **WHEN** a skill row carries target or cast detail
- **THEN** that detail renders on the name side of the row, with the cost cell as the row's
  rightmost column (matching the reference's `.srow .cost` right-alignment via `margin-left:auto`)

#### Scenario: An unlabeled group keeps its top spacing
- **WHEN** a skill-book group without a label renders after the group-container margin was removed
- **THEN** it keeps the pre-change 8px top spacing, so removing the group-container margin does not
  regress ungrouped content

#### Scenario: The island stack follows the vitals visibility rule
- **WHEN** the stage renders its left HUD island stack
- **THEN** the vitals island and the conditions island are shown and hidden by
  `webclient-contextual-hud`'s vitals visibility rule

#### Scenario: Identity fields belong to the drawers, not the HUD
- **WHEN** identity information is presented
- **THEN** the display name, full title, true traits, guild rank and merit, and disguise are
  presented by the party window's status tab and the purse only by the party window's header, and no
  race, subrace, class, or faction line is rendered anywhere, because no such field exists in
  either payload

#### Scenario: No persistent HUD surface renders the wallet
- **WHEN** any persistently visible HUD surface renders
- **THEN** none of them renders the wallet

#### Scenario: The presented payload fields are the enumerated set
- **WHEN** the status, character, and skill surfaces present their data
- **THEN** the `status` payload contributes its gauges (hp/mp/sp) and conditions with their
  derived modifiers, the `character` payload contributes its counter (guild_merit), static traits
  (atk_phys/agility/defense/magic_power), wallet, character details, the equipment doll's
  equipped items, disguise, guild rank/merit, and persona, and the skill book presents
  active/passive tabs, categories, search, and per-skill cost/target/cast/availability detail

#### Scenario: The intimate/adult block is not built
- **WHEN** the status, character, and skill surfaces render
- **THEN** the intimate/adult block is not built, because it has no backing field

#### Scenario: Severity glyphs are distinct per severity
- **WHEN** conditions of different severities render
- **THEN** each condition's non-color severity glyph uses one distinct glyph shape per severity,
  so two severities are never separated by color alone

#### Scenario: The binding visual reference for group dots is named
- **WHEN** the skill book decides whether an elemental group's colour dot may render
- **THEN** the binding visual reference consulted is `docs/design/elosern-redesign/index.html`,
  and only an element that reference itself colour-codes may carry the dot

### Requirement: Breakdown-state stories cover the frozen manifest components

Storybook SHALL provide breakdown-state stories for the party window's status
tab and bag tab. The status tab stories SHALL be driven by a `character`
fixture mirroring the server contract's serialized sample, and that fixture
MUST carry a worn bias-bearing equipment row whose stored-base exposure differs
from its effective ordinal, at least one trait row at the 16-layer bound, and
at least one adjustment-bearing equipment row. The bag tab's breakdown story
SHALL be driven by a `party_inventory` fixture and an `item_holdings` answer
whose per-member deltas are the server's adjustment strings, because the
`party_inventory` v1 panel carries no trait layers. The component coverage
check SHALL pass against the UNCHANGED frozen required-set manifest.

#### Scenario: v5 breakdown stories build

- **WHEN** `pnpm run build-storybook` builds the updated stories
- **THEN** the status tab story renders the selected trait's waterfall layers
  (including the 16-layer-bound row, all rendered without truncation) and the
  bag tab story renders its holdings' adjustment strings

#### Scenario: Coverage gate stays clean

- **WHEN** `pnpm run showcase-coverage` runs after the change
- **THEN** the required-set manifest differs only by this series' governed
  additions and deletions and coverage passes

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
  wait, locked-wait, suggestions, generating, degraded-empty, and overflow states, the
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

### Requirement: The full overlays are complete, the deferred surfaces are absent, and the manifest is frozen
The full overlays `MapOverlay`, `SettingsOverlay`, `HelpOverlay`, and `CreationOverlay` SHALL be
complete, and SHALL each have a live mount path in the running application — a built, tested,
manifest-listed overlay that nothing imports is not complete.

#### Scenario: Creation gate rejects both out-of-range fields
- **WHEN** the creation wizard submits an age or an apparent_age outside the 0..10000 range
- **THEN** the age-range gate rejects the record before activation

#### Scenario: Settings are client-local and honor reduced motion
- **WHEN** a settings control changes
- **THEN** no `ui_action` is dispatched for it, the change is applied to the app-wide presentation tokens immediately — the motion level among them, which resolves every motion token for the whole document at once — and it is persisted through the versioned presentation-only browser store

#### Scenario: The settings surface renders nothing inert
- **WHEN** the settings overlay's controls are enumerated
- **THEN** every rendered control changes an outcome the client implements, and no typeface choice, audio level, interface-scale slider, or key-remapping control is present

#### Scenario: Every full overlay has a live mount path
- **WHEN** the running application is enumerated for overlay mount paths
- **THEN** each of the map, settings, and help overlays is opened by a real control in the live surface tree, the creation overlay is mounted on the committed `creation` panel's availability predicate, and none is present in the bundle without a live mount path

#### Scenario: The creation overlay renders no dismissal control
- **WHEN** the mounted creation overlay's chrome is enumerated
- **THEN** no close, exit, or dismiss control is rendered in its header or body, and the overlay stops rendering only when the committed `creation` panel stops being available

#### Scenario: The map overlay tracks read-model updates
- **WHEN** an OOB update replaces the `local_map` read-model payload while the mounted overlay is open
- **THEN** the map overlay re-renders the matching branch (the available lattice, or the registry-owned reason) and shows no stale state

#### Scenario: Deferred surfaces are absent, not mocked
- **WHEN** the complete component set is enumerated
- **THEN** no event-log Toasts surface or authored game-help browser is present and none presents invented data

#### Scenario: The objective tracker is no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the persistent objective tracker is absent from the deferred-surface list, because it now has a backing OOB read model (the `objectives` panel), its component is manifest-listed with a deterministic offline story, and its behaviour is asserted by `webclient-contextual-hud`'s objective tracker requirement instead

#### Scenario: The party surfaces are no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the party quickbar and the party window are absent from the deferred-surface list, because they now have backing OOB read models (the `party` and `party_member` panels), their components are manifest-listed with deterministic offline stories, and their behaviour is asserted by `webclient-contextual-hud`'s party requirements and `webclient-party-window` instead

#### Scenario: The action-feedback queue is built while the event-log queue stays deferred
- **WHEN** the complete component set and the deferred-surface assertion are enumerated
- **THEN** the client-local `ToastQueue` with its `feedback-` test-id family is present and manifest-listed, while the `event-log-`/`toast-` bound game-event queue remains named in the deferred-surface assertion waiting on the `event-log` read model

#### Scenario: The intimate/adult status collapsible is no longer deferred
- **WHEN** the complete component set and its deferred-surface assertion are enumerated
- **THEN** the intimate/adult status collapsible is absent from the deferred-surface list, because it now has a backing OOB read model (`character.intimate`), and its presence/absence behaviour is asserted by `webclient-party-window`'s member-tab requirement (the `party_member` panel's intimate section) instead

#### Scenario: The held-item bag is built from its backing section
- **WHEN** the `party_inventory` panel commits the viewed member's bag
- **THEN** the party window's 背包 tab renders that panel's rows with their display names, held counts and equipped counts, bounded by the payload's row cap

#### Scenario: The manifest is re-frozen at the redesign set
- **WHEN** the contextual HUD redesign completes
- **THEN** the required-component manifest is re-frozen at the complete redesign set and the component-coverage gate enforces it

#### Scenario: Overlay triggers follow the surface tree or panel availability
- **WHEN** the overlays' opening paths are enumerated
- **THEN** the map, settings, and help overlays each open from a real control in the live surface
  tree, and the creation overlay is mounted by the running client on the committed `creation`
  panel's availability predicate
- **AND** creation mode is entered by the server's snapshot rather than by a player-operated
  trigger, so no player control opens it

#### Scenario: Creation stories mount the live three-region workspace
- **WHEN** the `Overlays/CreationOverlay` stories render
- **THEN** they mount the same three-region creation workspace as the live client
- **AND** its `Storyboard` supplies an explicitly labelled, offline publication desk for
  save/confirmation, concept success/rejection and draft reconnect, and these controls are
  story-only and never ship as game controls

#### Scenario: The settings overlay exposes the client-local presentation settings
- **WHEN** the settings overlay renders
- **THEN** it exposes the narrative prose scale, the motion level (`完整` / `減少` / `關閉`),
  the text-to-HTML narrative toggle, and the colourblind-safe status palette as **client-local
  presentation state**

#### Scenario: Only options.dismiss stays on the action allowlist
- **WHEN** a settings change is considered for dispatch
- **THEN** no `ui_action` is dispatched for any setting: `options.dismiss` — the suggestions
  dismissal — is the only allowlisted `options.*` action, and widening the action allowlist is a
  server-side change that no showcase or redesign wave makes

#### Scenario: Settings reset with the store on an unrecognised version
- **WHEN** the client loads and the stored presentation-store version is unrecognised
- **THEN** each setting — applied to the document's presentation tokens immediately and persisted
  through the client's versioned, presentation-only browser store as a harmless display
  preference — is re-applied at load and reset with that store

#### Scenario: An absent motion-level key defers to the operating system
- **WHEN** the stored wrapper lacks the optional motion-level key
- **THEN** the operating system's `prefers-reduced-motion` preference continues to apply
  (`reduced` when it requests reduced motion, `full` otherwise)
- **AND** a stored level — any of the three — overrides the operating-system preference

#### Scenario: The creation wizard gates ages and emits creation actions
- **WHEN** the creation overlay runs its presets/custom/concept wizard
- **THEN** the age-range gate applies to BOTH the age and the apparent_age fields, the wizard has
  an activate transition, and it emits `creation.*`

#### Scenario: The dismissal bar leaves wizard actions untouched
- **WHEN** the creation overlay's actions are enumerated
- **THEN** no close, exit, or hide-the-surface affordance is rendered in its header or body and
  none is wired to a handler that only stops rendering the overlay
- **AND** this bars the dismissal affordance because the overlay's presence is owned by the
  committed `creation` panel and creation mode presents no surface behind it
- **AND** the wizard's own in-surface actions (the presets/custom/concept tab switch, the draft
  reset, the confirmation screen's cancel, and the activate transition) each carry a real outcome
  and are unaffected

#### Scenario: The map overlay holds against live read-model replacement
- **WHEN** the `local_map` OOB read model is updated while the `MapOverlay` is mounted in the
  running client
- **THEN** its available/unavailable branch re-renders so a replaced payload never leaves a stale
  state, and this holds against live read-model replacement and not only against a story's args

#### Scenario: The help overlay renders the client's own control reference
- **WHEN** the help overlay renders and the deferred-surface assertion is enumerated
- **THEN** the help overlay renders the client's own control reference, which the client
  authoritatively knows, and no authored game-help content
- **AND** the event-log Toasts surface and the design draft's category-to-entry game-help browser
  are named in the deferred-surface assertion together with the read model each waits on, and
  MUST NOT be built or mocked to look real
- **AND** the `help` command's output reaches the client only as narrative text and no committed
  panel carries it

#### Scenario: The held-item bag's total never claims untruncated holdings
- **WHEN** the 背包 tab renders from `party_inventory.rows`
- **THEN** the listing is bounded by the payload's row cap and the tab's count is only the count
  of rows actually shipped, never a claim about untruncated holdings
- **AND** the bag's backing is the `party_inventory` panel, which the server builds for the
  viewed member in exploration and in combat independently of any service host

#### Scenario: The deferred list's not-deferred exclusions name their governing specs
- **WHEN** the deferred-surface assertion excludes the intimate/adult status collapsible, the
  party quickbar and 同伴 ‧ 隊伍 drawer, the persistent objective tracker, and the client-local
  action-feedback toast queue
- **THEN** the intimate collapsible is backed by the `character` panel's `intimate` field
  (`webclient-exploration-menu`'s version-4 character-panel requirement) with completeness and
  absence-when-`null` behaviour governed by `webclient-party-window`'s member-tab requirement (the
  `party_member` panel's intimate section); the party surfaces by the `party` panel (`webclient-party-panel`) with rendering
  and mutation behaviour governed by `webclient-contextual-hud`'s party quickbar and party drawer
  requirements; the objective tracker by the `objectives` panel
  (`webclient-objectives-panel`) with rendering governed by `webclient-contextual-hud`'s
  objective tracker requirement; and the action-feedback queue (`webclient-action-feedback`)
  presents only client-composed or verbatim server-authored action messages rather than a backend
  read model, so its `ToastQueue` component and `feedback-` test-id family are built and
  manifest-listed
- **AND** the deferred event-log Toasts surface remains deferred by its own identity — the
  game-event toast queue bound to a not-yet-existing `event-log` read model, asserted absent by
  its `event-log-`/`toast-` test-id binding — and is distinct from the action-feedback queue
