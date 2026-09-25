## MODIFIED Requirements

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (dialogue variant) | hidden |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait | visible | visible | visible | hidden |
| action dock (band command region) | visible | visible | visible (regular exploration form) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
When a mode change, a committed revision that turns a surface's data rule false, or a collapse of the
command line hides the surface that currently holds focus, the shell SHALL move focus to the action
dock before the surface is removed, using the existing focus-restore path. A mode change into creation
SHALL also collapse the command line, so leaving creation never reveals an expanded row.

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
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the place card, message window, minimap, player standing portrait, action dock, command-line toggle, and log control all
  remain rendered, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the message window's presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

#### Scenario: The objective line shows only in exploration
- **WHEN** a non-empty committed `objectives` panel stays committed while the mode changes from exploration to combat, then to dialogue, then back to exploration
- **THEN** the objective line renders in exploration, is hidden with `display:none` in combat and in dialogue, and renders again on the return to exploration

#### Scenario: The command line starts collapsed in every playing mode
- **WHEN** the shell mounts in exploration mode, and later the committed mode changes to combat and then to dialogue without the player opening the command line
- **THEN** in each mode the command-line toggle is rendered with `aria-expanded="false"`, the command-line row is hidden with `display:none`, and the input field is outside the tab order

#### Scenario: Entering creation collapses an expanded command line
- **WHEN** the command line is expanded with focus in its field and the committed mode changes to creation, and later back to exploration
- **THEN** focus moves to the action dock before the row is hidden, and on the return to exploration the command line is collapsed

### Requirement: The feed presents the dialogue variant from the committed panel
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the
message window SHALL be the ONE dialogue surface and SHALL present the reference's dialogue
variant, unpaged: a dialogue box carrying the
host's avatar (the bound portrait through the client's art catalog when the row's `portrait_ref`
resolves, otherwise the display name's initial letter in the reference's gold display face), a
gold speaker line carrying the host's `display_name` plus ` · 羈絆 <stage>` only when
`bond_stage` is non-null, and the serif reply line carrying the panel's `line` verbatim; below
the box, one numbered pick row per `dialogue.choices` entry in payload order with its mono
digit badge and bounded label, laid out in a compact row grid (at most two pick columns),
followed by a trailing free-dialogue row (`⌨` badge,
`自由對話（輸入任意話語）→ 指令列`) and, after it, a trailing exit row (`✕` badge, label
`結束對話`). The box SHALL follow the current response's lines (see `webclient-input-narrative`);
earlier responses SHALL NOT be presented and remain in the full-log surface. The exchange SHALL keep
the window's fixed box in the band's message region: when the response's lines, the box, picks, and
trailing rows exceed it they SHALL scroll inside the window's text area, with the dialogue box at the
top of that area when a new reply commits, and SHALL NOT grow the window or the band. While the
variant renders, the window SHALL show no page marker, a pointer activation on the window SHALL NOT
advance a page, and Enter and Space SHALL keep their meaning for the focused row. Activating a pick row SHALL dispatch
`explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` under the existing dispatch
contract; activating the free-dialogue row SHALL focus the borrowed command line through the
existing freeform-borrow path and SHALL dispatch nothing itself; activating the exit row SHALL
dispatch `explore.dialogue_leave` with `{npc_id: host.identity}` under the same dispatch contract
and nothing else. The variant SHALL render the
session line exactly once — the box replaces the current response's duplicate final line for that
exchange, keeping any residual text of that line, while the polite live region announces each new
committed line exactly once — and SHALL
NOT render picks the panel does not carry, reason tags, or disabled-row states. While mode is
`dialogue` but the panel is unavailable (the transient window between a clear seam and its
commit), the window SHALL fall back to its paged presentation of the current response with no
dialogue box. The dialogue variant SHALL NOT depend on any dock frame or router
descriptor: its rows derive from the committed panel alone.

#### Scenario: The dialogue box mirrors the committed panel
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, a line, and four
  keyword choices
- **THEN** the window shows the initial-letter gold avatar, the speaker line
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
- **THEN** the reply appears once in the window and the polite live region names its text exactly
  once

#### Scenario: A transiently unavailable panel falls back plainly
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no dialogue box, picks, or exit row render and the window shows the current response's
  pages with their page marker

## ADDED Requirements

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, at the band's fixed height — drawn with the reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. Outside the dialogue
variant, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines, and SHALL NOT present earlier responses: they remain readable in
the full-log surface. Page text SHALL be set in the serif reading face at 28px at the 1920x1080
reference size and the default prose scale, SHALL scale with the viewport height and with the
client's prose scale, and SHALL hold at most 42 CJK characters per line.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL read `▼` while the current response has further pages and `■` on its last page.
It SHALL be decorative (hidden from assistive technology), and it SHALL blink only through the
client's motion tokens, so reduced motion stops the blink. An oversize page SHALL scroll inside the
window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no head row, no unread indicator, and no jump-to-latest control. In
creation mode the window, its marker, and the `日誌` control are hidden with the message region.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and no line of the two
  earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages and the player advances once
- **THEN** the marker reads `▼` on the first page and `■` on the second, and it is absent from the
  accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

## REMOVED Requirements

### Requirement: The narrative is a bounded caption whose complete log is reachable in one action
**Reason**: The AVG stage design (§6) replaces the scrolling caption card, its head row, its `完整日誌` capsule, and its unread indicator with a paged message window. The subject changes from a scrollable caption to one page of the current response, so the requirement is replaced.
**Migration**: "The message window presents the current response one page at a time in the band's message region" (this capability) and "The message window's reading controls advance pages and a new action flushes unread pages" (`webclient-input-narrative`). Annotations re-anchor to the former.
