## ADDED Requirements

### Requirement: Combat details follow the active command frame
The combat command window SHALL show detail for the currently highlighted root command, category, group or skill, never a stale previously selected skill. Command rows SHALL scroll inside a bounded region above the persistent legend. The Skills count SHALL remain the exact committed descriptor count rendered as neutral secondary text.

#### Scenario: Category does not show an old attack
- **WHEN** the player backs out of a skill and highlights a category
- **THEN** the detail shows that category label/count and no stale attack target or cost

#### Scenario: Last row stays reachable
- **WHEN** the player navigates beyond the visible list
- **THEN** the focused row scrolls into view above the unchanged hint strip

### Requirement: Basic attack starts focused on an eligible opposing candidate
Opening basic attack SINGLE targeting SHALL initially focus the first enabled opposing candidate already supplied by the server, without changing candidate order or legal explicit selection. If none exists it SHALL use the first enabled candidate, or the existing disabled explanatory focus when none is enabled.

#### Scenario: An ally precedes a foe
- **WHEN** the server lists an ally before an enabled foe for basic attack
- **THEN** the foe initially has focus, the ally remains selectable if allowed, and no request is sent before confirmation

#### Scenario: No eligible opposing candidate exists
- **WHEN** all opposing candidates are disabled or absent
- **THEN** focus falls back without constructing a candidate or dispatching

### Requirement: Playback lock is visible without inventing progress
While combat playback locks mutation controls, the command region SHALL communicate that it is waiting and expose the existing skip interaction clearly. A decorative activity line SHALL NOT imply a server completion percentage and SHALL be static at reduced/off.

#### Scenario: Skip settles the lock
- **WHEN** the player skips a locked playing round
- **THEN** the cue clears with playback and the existing canonical command state becomes available

## RENAMED Requirements

- FROM: `### Requirement: The combat dock's root frame renders as an icon tab bar with a truthful skills badge`
- TO: `### Requirement: The combat dock root renders as a vertical command window with a truthful skills count`

## MODIFIED Requirements

### Requirement: The combat dock root renders as a vertical command window with a truthful skills count
In combat mode the root SHALL render one vertical icon-and-label command list with a neutral inline Skills count equal to the committed descriptor count, omitted at zero. It SHALL preserve the existing resolver item order, identities, availability and confirmation routes. The active root SHALL be the only listbox/tab stop and expose its focused row by active descendant. Up/Down SHALL traverse and wrap in rendered order; Left/Right SHALL be no-ops at root. At deeper levels the root list SHALL be replaced by the current frame, with the existing breadcrumb/back path and only one active row container. No other mode SHALL render this combat root. Glyphs SHALL retain the existing concept mapping.

#### Scenario: The combat root renders as tabs and owns the listbox
- **WHEN** the dock is at the combat root frame
- **THEN** each root item renders as a vertical list row with a glyph and its label, the list carries the listbox role with a single tab stop and an active-descendant reference, and each row carries its preserved row identity attribute

#### Scenario: A combat tab glyph matches the reference design's icon for the same concept
- **WHEN** the combat root renders the 攻擊/技能/道具/防禦/逃跑/投降 rows
- **THEN** each row's glyph is the same pictogram `docs/design/elosern-redesign/index.html` draws for that concept's tab

#### Scenario: The skills badge equals the committed skill count
- **WHEN** the committed combat panel lists three skill descriptors across its categories, and later a panel with none
- **THEN** the 技能 row shows the neutral inline count `3`, then no count at all, and no other combat row shows a count or alert badge

#### Scenario: Combat tab focus geometry matches the rendered order
- **WHEN** the player presses the arrow keys on the combat root frame
- **THEN** focus moves through the rows in their rendered order with the vertical arrow keys and wraps at the ends, and the horizontal arrow keys move focus nowhere

#### Scenario: An open deeper combat frame leaves the tab bar inert
- **WHEN** a deeper combat frame is open
- **THEN** the root list is replaced by the current frame, the deeper frame's row container is the surface's only listbox and only tab stop, and no root row is reachable by sequential keyboard navigation

#### Scenario: Exploration renders no root tab bar
- **WHEN** the dock renders in exploration or dialogue mode at any depth
- **THEN** no combat root list is rendered, and no 移動, 查看, 互動, or 建議 root row exists anywhere in the dock

#### Scenario: Recovery root is bounded
- **WHEN** the resolver supplies only the recovery Forfeit path
- **THEN** one root row renders and still requires its existing explicit confirmation

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the
whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed
elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation
mode and for every frame: no frame (the scene overview, a target's verb popover, the waiting frame, the
combat frames, the skill master-detail, the destructive confirmation, or an empty pane host) SHALL
widen, heighten, shorten, or move it, and
no surface outside the band SHALL be positioned from the frame the dock currently carries. In dialogue
mode the command region is collapsed and the dock SHALL be hidden with `display:none` together with it,
as "The command region collapses in dialogue mode and the message window spans the band" states; it
SHALL NOT be rendered anywhere else in that mode. The
content column SHALL be laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar
in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the
bottom — around one remaining region that holds the current frame's rows or chips; that region SHALL
be the surface's only scrolling area, so no dock content is ever pushed outside the command region.
A target's verb popover SHALL render as a card laid over that region's visible box, inside the command
region, and SHALL scroll inside its own card when its rows exceed it. A frame whose content
does not fit the region's width SHALL wrap or collapse its own columns inside the region, never
overflow it horizontally. The panel SHALL be the same single `#action-dock` element in every mode,
carrying its existing tab index, its `data-mode` attribute and its role as the documented focus home
of every mode except dialogue, and SHALL NOT be remounted when the mode changes, including a change
into or out of dialogue.

The command region SHALL use the current charcoal-and-gold presentation, and the band that contains
it SHALL paint the reference's band chrome. Selected actions remain distinguishable by text and shape
as well as their gold or warm-red emphasis.

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1440x900 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb popover's card lies inside the command region

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the legend strip) stays fixed, and no row or chip is rendered outside the command region

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, dialogue, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, it is hidden with `display:none` exactly while the mode is dialogue, and
  it is not removed and re-created

#### Scenario: The panel stays inside its region at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the command region, no dock content overflows the
  region horizontally, and the frame's confirm control is reachable by scrolling the row region
  without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element's background gradient, top border, and box-shadow are the same values
  `docs/design/elosern-redesign/index.html` draws for its dock surface, and the `#action-dock`
  content column itself paints no background, border, or shadow


### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration and combat mode (never in creation mode, and never visibly in
dialogue mode, where the strip is hidden with the collapsed command region), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–9 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no root command list or pane SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`9` moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order —
for the scene overview, its first nine chips in reading order: exits, then people, then objects, then
the footer; a frame's `back` row takes the slot of its rendered position) and activates the entry through the
same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an
in-flight entry stays locked, and a held repeat is suppressed.
The slots address the frame's rendered entries, disabled ones included. In dialogue mode neither the
dock's entries nor the keyboard router claim any digit: the digits `1`–`N` belong to the dialogue choice
list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage
after the line is fully read" defines.
A digit whose entry does not exist (a frame with fewer rendered entries, dialogue mode, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in exploration or combat mode, at the overview, in a child frame, or at the combat root, and later the mode changes to dialogue
- **THEN** exactly one element carries the shortcut-legend text and test hook, it is the dock's
  legend strip, no root command list or pane renders a duplicate copy, and in dialogue mode the strip is hidden
  with the command region and no other element shows a legend

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–9 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the scene overview holds three exit chips, two person chips, and one object chip, and the
  player presses `5`, and later `6`, from a non-editable focus
- **THEN** the `5` press focuses the second person chip and opens its popover exactly as `Enter`
  would, once, and after Escape the `6` press focuses the object chip and submits its `explore.look`
  once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue choice list shows four picks with focus on the list, the command region is
  collapsed, and the player presses `4` and `5`
- **THEN** the `4` press activates pick four through the same dispatch entry, the `5` press is handled
  by neither the list nor the keyboard router and falls through, and the hidden dock's focus and frame
  are unchanged

