## MODIFIED Requirements

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract

The action-dock family (`ActionDock`, `DockMenu`/`DockMenuItem`, `ExitCompass`, `ExplorationReadout`,
`RestForm`) SHALL present the `context_actions` v6 menus and, in exploration, the exit compass beside
the 建議 pill sharing one readout, with the mode's guidance line, focused/disabled states, and the
exact server-authored suggestion card shape on the centred suggestions card.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render on the suggestions card
- **THEN** each card row is the exact server-authored shape (label and optional hint) and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: The scene overview renders only its non-empty rows
- **WHEN** the exploration root renders for a room with people, objects, and exits beside a compass
- **THEN** no chip row renders, with no 人物, 物件, 出口, or footer row or label: the people and objects stand on the presence rail and the room actions on the place card and the 建議 pill

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
- **WHEN** the command panel's right column holds the 建議 pill and the readout
- **THEN** both stay inside the command panel and neither overflows it horizontally

#### Scenario: An exit chip follows the move row form's rules
- **WHEN** the compass resolves and aims a committed move row
- **THEN** its target and readout obey `webclient-exit-compass`, including bearing, direction and portal resolution, destination fallback, and disabled reason presentation

#### Scenario: The verb popover names its target and its rows
- **WHEN** the choice card renders a target's verb rows
- **THEN** it renders that target's rows in the menu's order with digit badges, followed by the trailing `✕ 返回` row under a hairline rule

#### Scenario: A disabled chip exposes its reason to assistive technology
- **WHEN** a dock row or a card row is disabled
- **THEN** it stays focusable, carries its disabled marker, and exposes its reason to assistive
  technology; in the exploration screen a server-authored disabled reason appears in the shared
  readout

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, the `CharacterStatusDrawer` (housing the `EquipmentDoll`), and the `SkillBook`
components SHALL present the `status` panel payload (schema version 1), the `character` panel
payload (schema version 3), and the character's skill data, each surface rendering only its
OOB-backed payload and inventing no field.

#### Scenario: Status is never color-only
- **WHEN** a gauge, counter, or condition is displayed
- **THEN** the gauge pairs an icon and a text label with an explicit current/maximum numeric value, each counter and static trait renders its numeric value, and each condition pairs a distinct non-color severity glyph with its label plus every numeric or derived-modifier value the payload provides — no value is conveyed by color alone

#### Scenario: Disguised stats are display-only and distinct from true traits
- **WHEN** the character payload carries disguised statistics
- **THEN** the drawer shows them as display values distinct from the true traits, every true trait row keeps its true value, and no disguised value alters combat resolution

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
  presented by the character status drawer and the wallet only by the inventory drawer, and no
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
