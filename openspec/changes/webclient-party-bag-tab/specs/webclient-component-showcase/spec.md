# Spec Delta

## MODIFIED Requirements

### Requirement: The map, art, and services surfaces render OOB-backed data truthfully
The `LocalMap`, `SceneBackdrop`, `ReferenceArtwork`, and services-backed panels (`ShopPanel`,
`QuestBoard`, and `LoreDrawer`) and the party window's `PartyBagTab` (backed by `party_inventory` and
`item_holdings`) SHALL render only committed OOB data.

#### Scenario: Art degrades to a truthful placeholder
- **WHEN** the art asset is missing, pending without a prior image, failed, invalid, or unavailable
- **THEN** the art surface renders a truthful scene placeholder with no invented image

#### Scenario: Art renders validated content when available
- **WHEN** the art payload is available
- **THEN** the backdrop renders the 16:9 scene with its external scene label and alternative text, and a framed-portrait surface renders a catalog entry it is given with the shared rect crop

#### Scenario: Services and inventory are backed only
- **WHEN** a services-backed panel renders
- **THEN** it renders only committed panel fields and locally mapped controls, with no invented world, item, or mechanic data

#### Scenario: Inventory inspection is equivalent for focus and hover
- **WHEN** a committed row with presentation is hovered or focused
- **THEN** both story states expose the same committed name, kind, rarity, summary, count, equipped marker, and action availability, and focus references the inspector through `aria-describedby`

#### Scenario: Unknown item metadata degrades visibly and safely
- **WHEN** an inventory row has `presentation` null and `action` null
- **THEN** its story renders the neutral unknown state with real name and quantity and no inferred metadata or action

#### Scenario: Inventory use confirmation is showcased
- **WHEN** the actionable healing-potion story activates its tile
- **THEN** the story opens the labelled confirmation and dispatches only after confirm

#### Scenario: Disabled item reasons are showcased
- **WHEN** the full-HP potion or sixth-accessory story activates its tile
- **THEN** the story displays the committed rejection reason without dispatch

#### Scenario: Equipment and five accessories are showcased
- **WHEN** the equipment stories render direct toggle and five-accessory states
- **THEN** committed equipped markers and the five-item accessory summary render without a locally inferred slot or replacement

#### Scenario: Services unavailable surfaces render only the registered reason
- **WHEN** the services OOB channel or the `party_inventory` panel is unavailable
- **THEN** shop, quest and lore stories, and the bag tab story respectively, render only the registered reason with no fabricated values or controls

#### Scenario: Local map stories pass the explicit variant and show no layout control
- **WHEN** the local map's showcase stories render
- **THEN** they pass the renderer's explicit variant parameter and SHALL NOT present a layout
  control

#### Scenario: The local map renders the v1 payload in its resolved variant
- **WHEN** the local map renders
- **THEN** it renders the `local_map` v1 payload with its states, actionable adjacent nodes,
  legend and detail line, and not-colour-only encoding, in the placement variant (coordinate
  lattice or radial connected graph) that the payload's `layer` resolves to, and invents no
  distance, bearing, or terrain geometry in either variant

#### Scenario: Portrait catalog entries stay inside their framed surfaces
- **WHEN** portrait catalog entries render
- **THEN** they render only inside the framed-portrait surfaces that consume them, never as a
  standalone catalog strip

#### Scenario: Shop, quest, and lore render only their services payload
- **WHEN** the shop, quest board, or lore drawer renders
- **THEN** it renders only its services payload

#### Scenario: The inventory renders its committed fields together
- **WHEN** the `PartyBagTab` renders
- **THEN** it renders committed `party_inventory` display name, held count, equipped count, nullable
  presentation, and the use, toggle and give descriptors together with the committed equipment doll
  and the selected item's committed holdings

#### Scenario: Presentation and action come only from committed descriptors
- **WHEN** an inventory row renders its icon map usage or action behavior
- **THEN** the inventory uses its local icon map only from committed icon keys and action behavior
  only from committed action descriptors

#### Scenario: The inventory interaction set invents no mechanic
- **WHEN** the inventory provides inspection and activation (keyboard-equivalent), confirmation for
  usable items, direct equipment toggle, and committed disabled-reason states
- **THEN** it does so without inventing an effect, recovery amount, condition, consumable flag,
  equipment slot, statistic, requirement, set bonus, client-computed comparison, sort, search,
  drag, or drop behavior; its only comparison is the server's `item_holdings` delta and its only
  filter is the selected doll slot

#### Scenario: No surface invents data, party panel included
- **WHEN** any map, art, or services surface renders
- **THEN** none invents data, including a dedicated party panel

#### Scenario: The manifest includes the inventory story set
- **WHEN** the showcase required-set manifest is enumerated
- **THEN** it SHALL include deterministic offline stories and tests for actionable use, use
  confirmation, full-HP rejection, direct equipment toggle, equipped state, five accessories,
  accessory-cap warning, unknown items, and services unavailability

### Requirement: The status, character, and skill surfaces present truthful, non-color-only state
The `StatusPanel`, the `CharacterStatusDrawer`, and the `SkillBook`
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
- **THEN** it presents the character details, disguise, guild rank/merit, and persona, and no field the payload does not carry is rendered; equipped items are presented by the party window's bag tab

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

### Requirement: Breakdown-state stories cover the frozen manifest components

Storybook SHALL provide breakdown-state stories for the character drawer and the
party window's bag tab, driven respectively by a character fixture and a
`party_inventory` fixture
mirroring the server contract's serialized sample — the fixture MUST carry
a worn bias-bearing item whose stored-base exposure differs from its
effective ordinal, at least one row at the 16-layer bound, and at least
one adjustment-bearing item — and the component coverage check SHALL pass
against the UNCHANGED frozen required-set manifest.

#### Scenario: v5 breakdown stories build

- **WHEN** `pnpm run build-storybook` builds the updated stories
- **THEN** the drawer and bag tab stories render their fixtures' layers (including the 16-layer-bound row, all rendered without
  truncation) and adjustment strings

#### Scenario: Coverage gate stays clean

- **WHEN** `pnpm run showcase-coverage` runs after the change
- **THEN** the required-set manifest differs only by this series' governed
  additions and deletions and coverage passes
