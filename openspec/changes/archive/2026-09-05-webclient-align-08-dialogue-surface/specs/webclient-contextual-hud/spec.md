# Delta spec: webclient-contextual-hud (webclient-align-08-dialogue-surface)

Chain note: the caption, quickbar, and tracker blocks below restate those requirements AS
MODIFIED by webclient-align-03-narrative-feed / webclient-align-05-party-hud /
webclient-align-09-objective-tracker-ui, and the legend block restates change 01's legend
requirement. The panel/mode contract this surface consumes lands in
webclient-align-10-dialogue-panel (not 07). Apply/merge those first (roadmap wave W3).

## MODIFIED Requirements

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| narrative caption | visible | visible | visible (dialogue focus) | hidden |
| HUD island stack (character/vitals/conditions) | visible | visible | visible | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | visible | visible | visible | hidden |
| objective tracker island | visible | visible | visible | hidden |
| action dock | visible | visible | visible (dialogue form) | visible (creation form) |
| command line | visible | visible | visible | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. When a mode change hides the surface that currently
holds focus, the shell SHALL move focus to the
action dock before the surface is removed, using the existing focus-restore path.

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
- **THEN** the narrative caption, HUD islands, minimap, party quickbar, objective tracker, action
  dock, and command line all remain rendered, and only the narrative presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified
### Requirement: The narrative is a bounded caption whose complete log is reachable in one action
The narrative SHALL render as a bounded caption card at the visual centre of the stage, constrained in
both measure and height so it never grows to fill the stage, drawn with the reference's caption panel
treatment: panel fill with backdrop blur, hairline border, shared radius and shadow, and the
reference's vertical hairline rule offset outside the card's left edge. The card SHALL carry a head
row styled as the reference's caption head (small uppercase letter-spaced label): on the left, a mode
label — `敘述` while the committed mode is exploration, `戰鬥日誌` while it is combat, and `對話`
while it is dialogue — and on the right, a single labelled capsule control that opens a full-log surface presenting the complete
retained narrative through the same markup renderer as the caption — never a second markup path. The
full-log surface SHALL be scrollable, SHALL trap focus while open, SHALL close on Escape, and SHALL
restore focus to the control that opened it. While the committed mode is dialogue and the
committed `dialogue` panel is available, the head label reads `對話` and the full-log capsule SHALL
NOT be rendered (the reference renders no log control in the dialogue variant); the unread
indicator, its polite live region, and its
jump-to-latest behaviour SHALL remain on the caption card beside the head label and SHALL otherwise
be unchanged.

#### Scenario: The caption card is bounded
- **WHEN** the narrative holds more lines than the caption card can show
- **THEN** the card scrolls internally within its bounded height and does not expand to fill the
  stage

#### Scenario: The head row names the mode and owns the log control
- **WHEN** the caption renders in exploration mode and then in combat mode
- **THEN** the head label reads `敘述`, then `戰鬥日誌`, and the `完整日誌` capsule is the card's only
  full-log control

#### Scenario: The complete log opens in one action
- **WHEN** the player activates the caption card's full-log control
- **THEN** the full-log surface opens showing the complete retained narrative, rendered through the
  same markup renderer as the caption

#### Scenario: The full-log surface returns focus on Escape
- **WHEN** the full-log surface is open and the player presses Escape
- **THEN** it closes and focus returns to the control that opened it

#### Scenario: The unread indicator is unchanged
- **WHEN** new narrative lines arrive while the caption card is scrolled away from the latest line
- **THEN** the unread indicator states its count and jump action and is announced through its polite
  live region exactly as before

#### Scenario: The dialogue head reads 對話 without the log capsule
- **WHEN** the committed mode is dialogue and the `dialogue` panel is available
- **THEN** the head label reads `對話` and no `完整日誌` capsule is rendered
### Requirement: The party quickbar island presents the committed party only
The left HUD SHALL carry a party island while the committed `party` panel is available in
exploration, combat, or dialogue mode, and SHALL render no party island when the panel is unavailable or the
committed mode is creation. The island's header SHALL read `同伴` with the slot count as
`N / 4`, where `N` equals the committed slot count. Each row of `party.slots` SHALL render one
cell carrying: the companion's display name; an avatar showing the bound portrait only when the
row's `portrait_ref` resolves through the client's art catalog, otherwise the display name's
initial letter in the reference's gold display face; an HP hairline bar whose fill ratio is
`hp_current / hp_maximum`; and a state row carrying the HP numerals and the row's bond stage
name. When the committed combat panel's participant rows carry a row with the same `identity`,
the state row SHALL additionally prefix the joined participant's session token (e.g. `a2`); a
companion not fighting SHALL show no token. The slot row SHALL be padded with dashed
`+ 邀請` cells — one per missing companion up to four — and an empty party SHALL render a row
of four dashed invite cells. Activating the island or any cell SHALL open the 同伴 · 隊伍
drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

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
### Requirement: The objective tracker island presents the committed objectives only
The HUD SHALL carry a bottom-right objective tracker island while the committed `objectives`
panel is available with a non-empty `rows` list in exploration, combat, or
dialogue mode, and SHALL render no
tracker island when `rows` is empty, when the panel is unavailable, or in creation mode. The
island's header SHALL read `目標` with the mono-gold count `N 追蹤`, where `N` equals the
committed row count. Each row of `objectives.rows` SHALL render, in payload order: a stage box
showing a completion check when `stage_progress >= objective_quantity` and an empty box
otherwise; the row's `objective_line`; a right-aligned mono-gold slot carrying
`stage_progress / objective_quantity` when `objective_quantity` is greater than one and the
row's `+reward_copper` when `objective_quantity` is one and `reward_copper` is non-null, and
carrying nothing otherwise; and, when `deadline_line` is non-null, a trailing muted line with
that text. The tracker is display-only: it SHALL render no accept, abandon, turn-in, or tracking
control and SHALL dispatch no action. It SHALL present no objective prose the panel does not
carry and no invented optional or previous-stage rows.

#### Scenario: Active objectives list in payload order
- **WHEN** a snapshot commits two objective rows, the first with progress 2 of quantity 5 and the
  second a single-count quest with an 80-copper reward
- **THEN** the island reads `目標 2 追蹤` and renders the first row's `2/5` progress tag and the
  second row's `+80` tag with their describe-seam objective lines, and no control is present

#### Scenario: A satisfied objective shows the done box
- **WHEN** a committed row carries `stage_progress` equal to `objective_quantity`
- **THEN** that row's stage box renders the completion check

#### Scenario: An empty or unavailable objective list hides the island
- **WHEN** the committed `objectives.rows` becomes `[]` or the panel becomes unavailable
- **THEN** no tracker island is rendered anywhere in the HUD

#### Scenario: The tracker dispatches nothing
- **WHEN** the player interacts with the tracker island
- **THEN** no `ui_action` or text command is sent and no mutation control is present

## ADDED Requirements

### Requirement: The feed presents the dialogue variant from the committed panel
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the
narrative caption SHALL present the reference's dialogue variant: a dialogue box carrying the
host's avatar (the bound portrait through the client's art catalog when the row's `portrait_ref`
resolves, otherwise the display name's initial letter in the reference's gold display face), a
gold speaker line carrying the host's `display_name` plus ` · 羈絆 <stage>` only when
`bond_stage` is non-null, and the serif reply line carrying the panel's `line` verbatim; below
the box, one numbered pick row per `dialogue.choices` entry in payload order with its mono
digit badge and bounded label, followed by a trailing free-dialogue row (`⌨` badge,
`自由對話（輸入任意話語）→ 指令列`). Activating a pick row SHALL dispatch
`explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` under the existing dispatch
contract; activating the free-dialogue row SHALL focus the borrowed command line through the
existing freeform-borrow path and SHALL dispatch nothing itself. The variant SHALL render the
session line exactly once — the box replaces the caption's duplicate stream tail for that
exchange while the polite live region announces each new committed line exactly once — and SHALL
NOT render picks the panel does not carry, reason tags, or disabled-row states. While mode is
`dialogue` but the panel is unavailable (the transient window between a clear seam and its
commit), the caption SHALL fall back to its plain narrative presentation with the `對話` head
label and no dialogue box.

#### Scenario: The dialogue box mirrors the committed panel
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, a line, and four
  keyword choices
- **THEN** the caption shows the initial-letter gold avatar, the speaker line
  `灰婆婆 · 羈絆 親睦`, the reply line, four numbered pick rows, and the free-dialogue row

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer or Enter
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that
  row's `keyword_id` is submitted through the existing dispatch contract

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates the trailing free-dialogue row
- **THEN** the command line receives focus for a freeform utterance and no action is dispatched

#### Scenario: The session line announces once
- **WHEN** a new reply commits while the dialogue variant renders
- **THEN** the reply appears once in the caption and the polite live region names its text exactly
  once

#### Scenario: A transiently unavailable panel falls back plainly
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no dialogue box or picks render and the caption shows plain narrative with the `對話`
  label

### Requirement: The dock presents the dialogue form as a mirror of the same picks
While the committed mode is `dialogue`, the action dock SHALL present the dialogue root form:
one tab `對話選項` whose pane lists the SAME committed `dialogue.choices` rows as the feed —
through one shared derived view model, never a second fetch or copy — with the same dispatch
semantics, and its legend SHALL carry the reference's dialogue hint through the shortcut-legend
requirement restated below. While mode is `dialogue` and the
panel is unavailable, the pane SHALL resolve to the shared degradation marker with the panel's
server-authored reason, like any unresolvable frame. Digit keys `1`–`4` SHALL activate the first
four rendered picks while the dialogue form is presented, and SHALL keep their command-line
semantics everywhere else, never intercepted from the input field. While the dialogue form is
presented, the `→` key SHALL focus the borrowed command line through the same freeform-borrow
path and SHALL dispatch nothing itself, never intercepted from the input field. Pointer, Enter,
and digit activation SHALL dispatch identically through the same router entry.

#### Scenario: Feed and dock mirror one committed list
- **WHEN** four choices commit while mode is dialogue
- **THEN** the feed and the dock pane render the same four rows from one derived model and both
  dispatch the same identifiers and payloads

#### Scenario: Digits pick in dialogue mode only
- **WHEN** the player presses `3` while the dialogue form renders, and separately while the
  command line has focus
- **THEN** the dialogue press activates pick three through the same dispatch entry, and the
  command-line press types into the input untouched

#### Scenario: The arrow key borrows the command line
- **WHEN** the player presses `→` while the dialogue form renders, and separately while the
  command line already has focus
- **THEN** the dialogue-mode press focuses the command line and dispatches nothing, and the
  focused press moves the caret normally with no focus change

#### Scenario: The unavailable dialogue frame degrades like any lost frame
- **WHEN** mode is dialogue and the panel is unavailable
- **THEN** the dock pane shows the shared degradation marker with the server-authored reason and
  no pick renders

## MODIFIED Requirements

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend element matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: while the dock
presents its regular form, the text `數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`;
while the dock presents the dialogue form, the text `數字鍵 1–4 選 · ` followed by an `<kbd>`
element naming `→` and the verb phrase `指令列自由對話`. Both variants render
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable, and the bounded services quantity form has not captured the digit first), pressing
`1`–`4` moves the current dock frame's focus onto the first four rows (1-indexed, rendered order)
and activates the row through the same confirm path `Enter` uses — a disabled row shows its
explanation and submits nothing, an in-flight row stays locked, and a held repeat is suppressed.
The slots address the pane's rendered rows: where a pane does not render the standard `back`
cell as a row (the exit-outlet pane), that cell takes no slot. While the dock presents the
dialogue form, the slots address only the rendered scripted picks — the trailing free-dialogue
row never takes a digit slot, and a degraded dialogue form (no rendered picks) claims no digit.
A digit whose row does not exist (a frame with fewer rendered rows, a degraded dialogue form, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carries the shortcut-legend text and test hook, and no duplicate
  copy is rendered

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock tab bar renders in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–4 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the current dock frame has at least two rows and the player presses `2` from a
  non-editable focus
- **THEN** the second row becomes the frame's focus and its action submits exactly as `Enter`
  would, once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rows than the pressed digit and the command field is
  not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: The dialogue legend swaps to the reference dialogue hint
- **WHEN** the dock tab bar renders while the dialogue form presents
- **THEN** the legend reads `數字鍵 1–4 選 · → 指令列自由對話` with `→` rendered as a styled `<kbd>`
  element, and the legend element is the same single instance, not a second copy
