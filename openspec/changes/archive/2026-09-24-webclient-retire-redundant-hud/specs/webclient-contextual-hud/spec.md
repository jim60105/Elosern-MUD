## MODIFIED Requirements

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| narrative caption | visible | visible | visible (dialogue focus) | hidden |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective tracker island | visible | visible | visible | hidden |
| action dock | visible | visible | visible (regular exploration form) | visible (creation form) |
| command line | visible | visible | visible | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). When a mode change, or a committed revision that turns a
surface's data rule false, hides the surface that currently holds focus, the shell SHALL move focus to
the action dock before the surface is removed, using the existing focus-restore path.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration
- **THEN** the minimap island renders again with the committed `local_map` payload

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides
- **THEN** focus is moved to the action dock before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the narrative caption, the HUD island stack, the minimap, and the command line are absent, and the action dock renders the creation form

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the narrative caption, minimap, objective tracker, action dock, and command line all
  remain rendered, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the narrative presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces placed in the stage's `hud-left` and `hud-right` anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The left anchor SHALL
carry the vitals, the conditions, and the party quickbar as sibling islands in that fixed order, each
present only while its own requirement renders it; the left anchor SHALL carry no character head card
and no portrait catalog strip. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the vitals, the conditions, and the party quickbar render as three separately-chromed islands in that order, each with the translucent blurred panel chrome, none of them is a single opaque column card, and no head card or portrait catalog strip is rendered

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** the island stack's rendered box fits inside its anchor and does not intersect the action dock, the narrative caption, or the opposite anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

### Requirement: The command line is a permanently present bar in the stage's command-line anchor
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field, a hint cluster, the
command-history controls, and the overlay utility controls. The bar SHALL carry no quick-word chip and
no other control that only writes a fixed command word into the field. The overlay utility controls
SHALL include a labelled 角色肖像圖庫 control that renders only while the committed `gallery` panel is
available and opens the portrait gallery overlay through the same opener-captured path the other
utility controls use, so closing the gallery returns focus to that control. In the modes this
capability's visibility matrix renders the command line (exploration and combat), the input field SHALL
be present in the DOM, visible and focusable without any opening action: there SHALL be no entry
control, no `aria-expanded` state and no closed state. No stored presentation state SHALL be able to
remove it. (The command line is intentionally absent from the layout in creation mode, per H1's
visibility matrix and design D10.)

The bar SHALL NOT overlap the action dock, the narrative caption or any HUD anchor at 1440x900 or
1280x720. When horizontal space is insufficient, the hint cluster SHALL be dropped first; the input field, the history controls and the
utility controls SHALL never be dropped, because they are the only pointer path to their behaviour.

#### Scenario: The field is usable without an opening action
- **WHEN** the shell mounts in exploration mode
- **THEN** the command input field is present in the DOM and focusable, no entry control is rendered, and no element in the bar reports an `aria-expanded` state

#### Scenario: The bar keeps its geometry at the minimum viewport
- **WHEN** the stage renders at 1280x720 with every utility control rendered, including the gallery control
- **THEN** the bar's rendered box intersects no other stage anchor's box, and the input field, the history controls and the utility controls are all still rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first, and no input field, history control or utility control is removed

#### Scenario: The gallery control follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, the player activates the 角色肖像圖庫 utility control, closes the overlay, and a later revision commits the panel's unavailable form
- **THEN** the control opens the portrait gallery overlay, closing the overlay returns focus to the control, and after the unavailable form commits the control is absent from the bar and the tab order

#### Scenario: No quick-word chip is rendered
- **WHEN** the bar renders in exploration or combat mode
- **THEN** no quick-word chip, letter badge, or chip cluster is present in the bar

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 · Tab 補全` — and
Tab completion SHALL behave as named: pressing Tab inside the input field completes the current
draft against the client's candidate set (session command history and the committed exploration
panel's exit names and interact-target display names, deduplicated). With exactly one matching candidate the field SHALL hold the full completion with
the caret at its end; with several the field SHALL hold the longest common prefix and successive
Tab presses SHALL cycle the matching candidates, with Shift+Tab reversing the cycle. A draft that
matches no candidate SHALL leave the field untouched, and Tab SHALL never move focus away from the
field at all (the release path is Escape, which the dock's shortcut legend names). The completion
cycle SHALL reset when the draft text is edited manually, and a change to the committed candidate
sources SHALL drop any in-flight cycle.

The history controls SHALL be labelled controls that drive the same history-walk state the recall
keys drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command
line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and completion
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and the Tab-completion affordance, matching
  the draft wording, and both are implemented

#### Scenario: Tab completes a unique candidate
- **WHEN** the field holds a draft matching exactly one candidate and the player presses Tab
- **THEN** the field holds that candidate in full with the caret at its end, and focus stays in
  the field

#### Scenario: Tab cycles ambiguous candidates
- **WHEN** the field holds a draft matching several candidates and the player presses Tab
  repeatedly
- **THEN** the field first completes to the longest common prefix and then cycles through the
  matching candidates, with Shift+Tab reversing the cycle, and any manual edit of the draft
  resets the cycle

#### Scenario: An unmatched draft is left alone
- **WHEN** the field holds a draft that matches no candidate and the player presses Tab
- **THEN** the field text and focus are unchanged

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is preserved across the walk, and neither submits

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its
actionable nodes; the island's non-interactive body MAY additionally open the same surface on pointer
click, which SHALL NOT replace or wrap the labelled control. The command line's utility controls SHALL
open the settings and help surfaces.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly
committed payload resolves to the other layout variant, the surface follows the resolved value with no
control of its own. It SHALL open fitted, showing the whole drawing inside its body, and SHALL offer
exactly the view affordances the full-map fit-view requirement of the local-map capability defines —
wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a
labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens
the state legend in a popover — and it SHALL name those gestures in words in its guide row. Those
affordances change only the view of the drawing: none of them SHALL change the committed payload, the
resolved layout variant, or any geometry the surface declares, and none SHALL be persisted. It SHALL
render no bearing, compass angle, distance, or coordinate figure, on any layer, and no zoom level,
scale ratio, or other figure describing the view.

The map surface's body SHALL carry the redesign draft's map-canvas framing (the radial-gradient dark
terrain background painted as pure CSS inside a rounded ink border), and SHALL NOT fabricate terrain
geometry the payload does not claim.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL name no key binding
or control the client does not implement, and SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the command line carries labelled controls that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement map, and at no point shows a map or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** its only view controls are the labelled 縮小, 放大, and 置中 buttons and the 圖例 disclosure
  button, its guide row names the wheel, `+` / `-`, and drag gestures in words, the legend appears only
  inside the 圖例 popover, and no zoom level, scale ratio, bearing, compass angle, or distance figure
  appears anywhere on the surface

#### Scenario: The map surface frames the draft canvas without invented terrain
- **WHEN** the map surface renders an available payload
- **THEN** the map body shows the radial-gradient ink background inside the rounded ink frame, and no terrain, coastline, or route geometry is drawn that the payload does not carry

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one

### Requirement: The party quickbar island presents the committed party only
The left HUD SHALL carry a party island while the committed `party` panel is available with at
least one slot in exploration, combat, or dialogue mode, and SHALL render no party island — no header,
no count, and no invite cell — when the panel is unavailable, when its `slots` list is empty, or when
the committed mode is creation. The island's header SHALL read `同伴` with the slot count as
`N / 4`, where `N` equals the committed slot count. Each row of `party.slots` SHALL render one
cell carrying: the companion's display name; an avatar showing the bound portrait only when the
row's `portrait_ref` resolves through the client's art catalog, otherwise the display name's
initial letter in the reference's gold display face; an HP hairline bar whose fill ratio is
`hp_current / hp_maximum`; and a state row carrying the HP numerals and the row's bond stage
name. When the committed combat panel's participant rows carry a row with the same `identity`,
the state row SHALL additionally prefix the joined participant's session token (e.g. `a2`); a
companion not fighting SHALL show no token. The slot row SHALL be padded with dashed
`+ 邀請` cells — one per missing companion up to four. Activating the island or any cell SHALL open the 同伴 · 隊伍
drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

Because the island is absent for an empty party, the character-status drawer SHALL carry one
labelled `同伴 · 隊伍` control, rendered while the committed `party` panel is available, that opens
the 同伴 · 隊伍 drawer and dispatches nothing, so that drawer stays reachable at every party size.

#### Scenario: The quickbar mirrors the committed party
- **WHEN** a snapshot commits two party slots with HP 180/220 and 144/160 and bond stages 親睦
  and 信賴
- **THEN** the island reads `同伴 2 / 4` and renders both cells with their HP bars, numerals, and
  stage names, plus two dashed invite cells, and no numeric affinity appears

#### Scenario: The combat token is joined by identity
- **WHEN** the committed combat panel carries a participant row whose `identity` equals a party
  slot's `identity` with token `a2`
- **THEN** that companion's state row shows the `a2` prefix, and a party row with no matching
  participant shows no token

#### Scenario: No portrait falls back to the initial letter
- **WHEN** a party row carries `portrait_ref: null` for display name `蕾娜`
- **THEN** the avatar renders the gold initial `蕾`, not an invented image

#### Scenario: An unavailable party panel hides the island
- **WHEN** the committed `party` panel switches to the unavailable form
- **THEN** no party island is rendered anywhere in the HUD (not an emptied or dimmed island)

#### Scenario: The quickbar opens the drawer without mutating
- **WHEN** the player activates a party cell
- **THEN** the 同伴 · 隊伍 drawer opens and no `ui_action` or text command is sent

#### Scenario: An empty party renders no island
- **WHEN** the committed `party` panel is available with an empty `slots` list in exploration mode
- **THEN** no party island, header, count, or invite cell is rendered anywhere in the HUD, and nothing in the left anchor is focusable on its behalf

#### Scenario: The party drawer stays reachable with an empty party
- **WHEN** the committed party is empty and the player opens the character-status drawer and activates its `同伴 · 隊伍` control
- **THEN** the 同伴 · 隊伍 drawer opens with its 空位 row and follow rules, and no `ui_action` or text command is sent

## ADDED Requirements

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
The HUD SHALL show the vitals island — the vitals rows together with the conditions island beneath
them — only while at least one of these holds for the committed state: the committed mode is
`combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp)
carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries at least one
entry whose `severity` is `warning`, `harmful`, or `critical`. A condition whose `severity` is
`beneficial` or `informational` — including a passive `skill_owned` combat-modifier row — SHALL NOT
by itself make the island visible, and neither SHALL an entry with a missing or unknown `severity`.
While the island is visible its condition chips SHALL render every committed condition, whatever its
severity. Otherwise the island SHALL be hidden with `display:none`, so it leaves the accessibility tree and the
tab order and contributes no visible box. The rule SHALL be derived client-side from the committed
`status` panel and the committed mode alone: no server field, request, or timer is involved, and a
vital that is absent from the payload or carries a non-numeric field SHALL NOT count as below its
maximum. Dialogue mode SHALL follow the same rule as exploration; creation mode hides the island
through the visibility matrix; an unavailable `status` panel renders no vitals island at all.

While hidden, the island SHALL keep its trailing-bar memory, so the first committed revision that
lowers a vital from full shows the island with the trailing bar lagging from the previously committed
ratio exactly as an always-visible island would. When a committed revision turns the rule false while
focus is inside the island, focus SHALL move to the action dock before the island is hidden, through
the same focus-restore path a mode change uses.

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals island is hidden with `display:none`, is absent from the accessibility tree and the tab order, and no vitals, numerals, or low-HP marker are visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration mode carries `mp` at 40 of 60 with no condition
- **THEN** the vitals island renders with every vital's icon, label, and `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** a committed revision in exploration mode carries full vitals and one condition whose `severity` is `harmful`
- **THEN** the vitals island renders with its vitals rows and the condition chip

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** a committed revision in exploration mode carries full vitals and only conditions whose `severity` is `beneficial`, such as a passive `skill_owned` combat-modifier row
- **THEN** the vitals island stays hidden with `display:none` and none of its condition chips is visible or focusable

#### Scenario: Visible island renders every condition chip
- **WHEN** the vitals island is visible because a vital is below its maximum and the committed conditions carry one `beneficial` and one `informational` entry
- **THEN** the island renders both condition chips

#### Scenario: Combat always shows the island
- **WHEN** the committed mode is combat with every vital full and no condition
- **THEN** the vitals island renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the island is hidden at full health and the next committed revision in the same epoch lowers `hp`
- **THEN** the island renders, the hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is on a `harmful` condition chip outside combat with every vital full, and a committed revision clears that condition, leaving only `beneficial` conditions
- **THEN** focus moves to the action dock before the island is hidden, and no focus is lost to the document body

## REMOVED Requirements

### Requirement: The character head card renders only backed identity
**Reason**: The head card repeated identity the player already reaches elsewhere (the top-bar character switcher, the 角色 status drawer, and the 背包 inventory drawer) and occupied the stage permanently. The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §4) removes it outright.
**Migration**: The full title, true traits including `magic_power`, guild rank and merit, and the disguise comparison are presented by the character-status drawer ("The character-status drawer degrades section by section and never substitutes a disguise"); the wallet is presented only by the inventory drawer ("The drawer layer renders the wallet exactly once"); the character name is presented by the top-bar character switcher. No persistently visible wallet surface remains.

### Requirement: Quick-word chips prepare a command without submitting it
**Reason**: Every chip and its bound letter (`l g s t w`, `c` in combat) duplicated an action-dock entry, and the letter bindings claimed keys outside any text field. The AVG stage design (§4) removes the chips together with their bindings.
**Migration**: Typed commands remain available through the command line, whose field, history walk, and Tab completion are unchanged. The server's single-letter command aliases stay installed as typed shortcuts. The dock carries the look, get, talk, wait, and cast affordances.

### Requirement: Bound quickbar letters are pinned against the installed player cmdset
**Reason**: The pin existed only so the client's chip badge letters could not drift from the installed command set; with the chips and their key bindings removed the client binds no command letter.
**Migration**: None. The aliases themselves remain installed and continue to resolve as ordinary typed commands.
