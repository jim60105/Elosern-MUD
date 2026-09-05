# Delta: webclient-contextual-hud

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
| action dock | visible | visible | visible (regular exploration form) | visible (creation form) |
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
  dock, and command line all remain rendered, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the narrative presentation changes

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
head row SHALL be a static sibling ABOVE the card's scroll viewport, never an element inside the
scrolled content, so no narrative line can ever render between the card's border and the head row at
any scroll offset. Only the content region below the head SHALL scroll, and the card's bounded height
SHALL bound that scroll region. The
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

#### Scenario: No content renders above the head row
- **WHEN** the caption is scrolled to any offset in any mode
- **THEN** no narrative line is visible between the card's border and the head row, and the head
  row itself never scrolls out of the card

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

### Requirement: The feed presents the dialogue variant from the committed panel
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the
narrative caption SHALL be the ONE dialogue surface and SHALL present the reference's dialogue
variant: a dialogue box carrying the
host's avatar (the bound portrait through the client's art catalog when the row's `portrait_ref`
resolves, otherwise the display name's initial letter in the reference's gold display face), a
gold speaker line carrying the host's `display_name` plus ` · 羈絆 <stage>` only when
`bond_stage` is non-null, and the serif reply line carrying the panel's `line` verbatim; below
the box, one numbered pick row per `dialogue.choices` entry in payload order with its mono
digit badge and bounded label, laid out in a compact row grid (at most two pick columns) so the
whole exchange — box, picks, and trailing rows — fits the caption's bounded height for normal
lines, followed by a trailing free-dialogue row (`⌨` badge,
`自由對話（輸入任意話語）→ 指令列`) and, after it, a trailing exit row (`✕` badge, label
`結束對話`). Activating a pick row SHALL dispatch
`explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` under the existing dispatch
contract; activating the free-dialogue row SHALL focus the borrowed command line through the
existing freeform-borrow path and SHALL dispatch nothing itself; activating the exit row SHALL
dispatch `explore.dialogue_leave` with `{npc_id: host.identity}` under the same dispatch contract
and nothing else. The variant SHALL render the
session line exactly once — the box replaces the caption's duplicate stream tail for that
exchange while the polite live region announces each new committed line exactly once — and SHALL
NOT render picks the panel does not carry, reason tags, or disabled-row states. While mode is
`dialogue` but the panel is unavailable (the transient window between a clear seam and its
commit), the caption SHALL fall back to its plain narrative presentation with the `對話` head
label and no dialogue box. The dialogue variant SHALL NOT depend on any dock frame or router
descriptor: its rows derive from the committed panel alone.

#### Scenario: The dialogue box mirrors the committed panel
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, a line, and four
  keyword choices
- **THEN** the caption shows the initial-letter gold avatar, the speaker line
  `灰婆婆 · 羈絆 親睦`, the reply line, four numbered pick rows, the free-dialogue row, and the
  exit row — with the reply line visible without scrolling while the picks render

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer or Enter
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that
  row's `keyword_id` is submitted through the existing dispatch contract

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates the trailing free-dialogue row
- **THEN** the command line receives focus for a freeform utterance and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates the exit row
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is
  submitted and no other action is dispatched

#### Scenario: The session line announces once
- **WHEN** a new reply commits while the dialogue variant renders
- **THEN** the reply appears once in the caption and the polite live region names its text exactly
  once

#### Scenario: A transiently unavailable panel falls back plainly
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no dialogue box, picks, or exit row render and the caption shows plain narrative with
  the `對話` label

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend element matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook. The dock SHALL NOT carry a dialogue-mode legend variant.

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
cell as a row (the exit-outlet pane), that cell takes no slot. While the narrative caption
presents the dialogue variant with at least one pick, the slots address the caption's pick rows
instead of the dock's pane rows — the caption's trailing free-dialogue and exit rows never take
a digit slot — and the dock's own rows claim no digit while that hold applies.
A digit whose row does not exist (a frame with fewer rendered rows, a caption variant with no
picks, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carries the shortcut-legend text and test hook, and no duplicate
  copy is rendered

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock tab bar renders in exploration, combat, or dialogue mode
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

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue variant renders three picks over a dock root frame and the player presses
  `2` and `4` from a non-editable focus
- **THEN** the `2` press activates caption pick two through the same dispatch entry, the `4` press
  is unclaimed and falls through, and no dock row is focused or activated

## REMOVED Requirements

### Requirement: The dock presents the dialogue form as a mirror of the same picks
**Reason**: The dock dialogue mirror (`對話選項` tab over a pane duplicating the caption's pick
rows) made entering a conversation hide every other dock affordance, duplicated the same rows in
two surfaces, and left the player with no exit except leaving the room — the reported unplayable
UX this change fixes. The narrative caption becomes the ONE dialogue surface.
**Migration**: The pick rows live only in the caption's dialogue variant (see the modified feed
requirement). While mode is `dialogue` the dock keeps its regular exploration form (see the
added requirement below). The mirror's `→` command-line borrow is replaced by the caption's
free-dialogue row; the legend's dialogue variant is deleted (see the modified legend
requirement); the `dialogue.root` descriptor family is removed from the frame-resolution
contract.

## ADDED Requirements

### Requirement: The dock keeps its regular exploration form in dialogue mode
While the committed mode is `dialogue`, the action dock SHALL render its ordinary exploration
root — the same root items, tab bar, panes, digit bindings outside the caption-retarget rule, and
router behaviour as exploration mode — derived from the committed `exploration` panel, which keeps
shipping its ordinary payload in dialogue mode. The dock SHALL NOT present a dialogue-specific
root, SHALL NOT duplicate the dialogue panel's pick rows in any pane, and SHALL NOT remove any
ordinary affordance while mode is `dialogue`. A mode switch into or out of `dialogue` SHALL
re-home the router stack to the ordinary exploration root descriptor through the existing teardown
decision point.

#### Scenario: The dock stays usable during a conversation
- **WHEN** mode commits to `dialogue` with the exploration panel's ordinary payload
- **THEN** the dock tab bar shows the ordinary exploration root entries (move/look/interact/…)
  with no `對話選項` tab and no pick-row pane anywhere

#### Scenario: Movement stays one action away
- **WHEN** the player opens the move frame while a dialogue session is live and activates an exit
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the
  session through the existing seam, and the committed mode returns to `exploration`

#### Scenario: Mode flips re-home the stack
- **WHEN** a committed snapshot switches the mode from exploration to dialogue while exploration
  submenus are open
- **THEN** the stack holds exactly the ordinary exploration root descriptor and no stale submenu
  row remains activatable
