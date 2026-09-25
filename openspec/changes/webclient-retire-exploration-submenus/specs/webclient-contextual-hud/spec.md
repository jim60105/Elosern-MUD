## MODIFIED Requirements

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration, dialogue, and combat mode (never in creation mode), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–9 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no tab bar SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
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
The slots address the frame's rendered entries, disabled ones included. While the message window
presents the dialogue variant with at least one pick, the slots address the window's pick rows
instead of the dock's entries — the trailing free-dialogue and exit rows never take
a digit slot — and the dock's own entries claim no digit while that hold applies.
A digit whose entry does not exist (a frame with fewer rendered entries, a dialogue variant with no
picks, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in exploration, dialogue, or combat mode, at the overview, in a child frame, or at the combat root
- **THEN** exactly one element carries the shortcut-legend text and test hook, it is the dock's
  legend strip, and no tab bar or pane renders a duplicate copy

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration, combat, or dialogue mode
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
- **WHEN** the dialogue variant renders six picks over the dock's scene overview and the player presses
  `6` and `7` from a non-editable focus
- **THEN** the `6` press activates pick six through the same dispatch entry, the `7` press
  is unclaimed and falls through, and no dock chip is focused or activated

### Requirement: Dock panes render a per-kind vocabulary from backed fields only

The dock's row region SHALL render the current frame in a form chosen for what that frame contains,
using one shared row renderer for every form so the focused marker, the disabled marker and its
`（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined
in exactly one place. The forms SHALL be: exit, person, object, and footer chips for the scene
overview; navigation rows for the scripted-keyword list; the verb popover's rows under a target head;
the waiting cards; suggestion cards for the suggestions frame; and the combat forms specified
elsewhere in this capability. No exploration frame SHALL render an exit-outlet grid: exits are chips
of the scene overview.

An exit chip SHALL render the exit's direction as a leading glyph, and, while the chip is enabled, its
primary text SHALL be the destination's display name — never a repetition of the direction word or the
exit's own label once a glyph already carries that meaning. The glyph SHALL be resolved from a fixed
client-side table of canonical direction words; an exit label outside that table SHALL render verbatim
as the chip's primary text (there being no glyph to carry it) rather than being mapped to a guessed
direction. The destination's display name SHALL be resolved by matching the exit's server-authored
destination node against the committed local-map nodes; when that node is not present in the committed
lattice, an enabled canonical-direction chip SHALL fall back to its own exit label as its primary text
rather than rendering blank — but SHALL NOT render both the destination name and the exit's own label
at once. A disabled exit chip SHALL always render its own exit label as its primary text, never the
destination name, followed by the shared disabled marker. An exit chip's focused state SHALL be
conveyed by its background and border fill together and SHALL NOT additionally render a focus-only
glyph beside its persistent direction glyph. A disabled exit chip's server-authored explanation SHALL
remain reachable by assistive technology directly from the chip and SHALL be shown in the overview's
reason strip while the chip is focused. The submitted move payload SHALL be unchanged.

A chip or navigation row SHALL render only fields the committed payload carries: its server-authored
name and, for a navigation row, an optional sub-line composed of such fields. No chip or row SHALL
render a statistics line, a portrait, or any other element for which the payload has no field; where
the design draft shows such an element it SHALL be absent rather than emptied or mocked. Icons and
glyphs SHALL be decorative, SHALL be hidden from assistive technology, SHALL always accompany a real
text label, and SHALL be selected only from stable server-authored keys or the direction table — never
from free text such as a display name.

A target's verb popover SHALL render a head naming the target it is scoped to, taken from the frame's
own server-authored display name, above that target's rows.

Every row and chip in every form SHALL keep the existing disabled contract: a disabled entry SHALL
remain focusable by arrow keys and by pointer, SHALL keep its accessible disabled state and its
server-authored explanation, and SHALL submit nothing.

#### Scenario: A move row names where it goes
- **WHEN** the scene overview renders an enabled exit chip whose label is a canonical direction and whose destination node is present in the committed local map
- **THEN** the chip renders that direction's glyph together with the destination node's display name as its primary text, with no separate rendering of the exit's own direction-word label, and activating it submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** an exit chip's label is a named door or a dynamic wilderness exit rather than a canonical direction
- **THEN** the chip renders that label verbatim as its primary text and no direction is guessed for it

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** an enabled canonical-direction exit chip's destination node is absent from the committed local map
- **THEN** the chip renders its glyph together with the exit's own label as a fallback primary text, and no destination name is invented

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** a canonical-direction exit chip is disabled and its destination node is present in the committed local map
- **THEN** the chip renders its own exit label followed by the shared disabled marker as its primary text, not the destination's display name, and its server-authored explanation remains reachable by assistive technology from the chip itself

#### Scenario: A focused move row is not double-marked
- **WHEN** an exit chip carrying a direction glyph is focused
- **THEN** the chip's background and border change together to mark focus, and no additional focus-only glyph renders alongside its existing direction glyph

#### Scenario: The move frame has no companion panel
- **WHEN** the scene overview renders with any chip focused
- **THEN** no detail aside or other side panel renders beside the overview, the overview occupies the pane's full available width, and no exit-outlet grid exists anywhere in the dock

#### Scenario: A row renders only backed fields
- **WHEN** the scene overview renders a look-only chip for a present entity
- **THEN** the chip shows the entity's display name only, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's verb popover
- **THEN** the popover renders a head naming that target above the target's server-authored rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row or chip is focused in any form, by arrow key or by pointer
- **THEN** it keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

### Requirement: A breadcrumb derived from the router names the player's position at depth

The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root
frame, and SHALL hide it entirely at the root frame. The breadcrumb SHALL name the parent frame and
the current frame, with the current frame visually distinguished, and SHALL carry a back control.
Activating the back control SHALL perform exactly the same operation the Escape key performs — it
SHALL pop exactly one menu level and SHALL NOT dispatch any action.

The breadcrumb's contents and its visibility SHALL be derived from the keyboard router's own frame
stack and depth, published through the committed view in the same pass as the frame's rows. The
client SHALL NOT maintain a second navigation state — no local pane selection, no locally accumulated
crumb stack — so the breadcrumb can never disagree with what Escape will do. A frame's breadcrumb
label SHALL come from the frame itself; for a frame scoped to one target, that label SHALL be the
target's server-authored display name. Every frame's `back` item SHALL render as a row of that frame, so
a focused `back` item carries the same focused treatment as any other row (a background fill and
border change together); the breadcrumb's back control SHALL carry no focus state of its own that
mirrors the router's focus. Activating the back row with Enter or the pointer, or activating the
breadcrumb's back control, SHALL pop exactly one level, restore the parent frame's previously
focused entry, and dispatch no action.

#### Scenario: The breadcrumb appears only below the root
- **WHEN** the dock is at its root frame
- **THEN** no breadcrumb is rendered
- **WHEN** the player opens a submenu
- **THEN** the breadcrumb appears naming the parent frame and the current frame

#### Scenario: The back control is the Escape path
- **WHEN** the player activates the breadcrumb's back control at any depth
- **THEN** exactly one menu level closes, the parent frame's rows render with the previously focused row marked, and no `ui_action` is emitted

#### Scenario: A focused `back` row keeps a visible focus carrier
- **WHEN** keyboard focus moves onto the suggestions frame's or a verb popover's `back` item
- **THEN** that `back` item is rendered as a row carrying the focused state (fill and border change together, not color alone), the breadcrumb's back control carries no focused state, and Enter on the row or a click on the breadcrumb control pops exactly one level back to the parent frame

#### Scenario: The breadcrumb tracks a target frame's own name
- **WHEN** the player opens an interact target's affordance frame
- **THEN** the breadcrumb's current segment is that target's server-authored display name

#### Scenario: The breadcrumb cannot drift from the router
- **WHEN** a panel replacement pops or replaces the current frame
- **THEN** the breadcrumb's depth and labels match the router's frame stack in the same render, with no interval in which they describe a frame the router has already left

## ADDED Requirements

### Requirement: A fixed-column dock pane sizes its columns to content
When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count
SHALL govern only which cell each row occupies, never the rendered width of a column. A column's
rendered width SHALL fit the natural size of the tile or row content placed in it; a pane whose rows
are fewer or narrower than the panel's available width SHALL leave the remaining width empty rather
than stretching every column to consume it. When the pane's available width is narrower than the
combined natural content width of the fixed columns, the columns SHALL compress (each track can shrink
toward zero) rather than overflow the pane horizontally. This SHALL hold regardless of how many columns
the keyboard geometry fixes, and changing a column's rendered width SHALL NOT change which row occupies
which cell. The content-sized track rule SHALL apply to the nav pane, the only pane that lays out its
row region as a grid on the fixed column count. The combat skill, target, and scale panes lay out their
rows with their own flex forms, which the fixed column count does not size; they SHALL be bound by the
no-overflow rule above and the keyboard cell mapping, not by the content-sized track rule. The scene
overview is not a fixed-column pane (its chips wrap by width under the section geometry the exploration
dock requirement defines).

#### Scenario: Column-count-driven layout never invents equal-width stretching
- **WHEN** a fixed-column dock pane (a nav pane) applies a fixed column count for its keyboard geometry
- **THEN** no column in that pane stretches a narrower row's content to an equal share of the panel's width

#### Scenario: A narrow pane compresses the fixed columns instead of overflowing
- **WHEN** the pane's available width (e.g. the command region at the minimum supported 1280x720 viewport) is narrower than the combined natural width of the fixed columns
- **THEN** the columns compress to fit the pane without horizontal overflow, and each tile or row wraps long content within its width

## REMOVED Requirements

### Requirement: A fixed-column-count dock pane sizes its columns to content, never stretching to fill the panel
**Reason**: Its exit-outlet exemption, the outlet's width-adaptive grid, and the move frame's single-column geometry describe a frame that no longer exists after `webclient-scene-overview-swap`: exits are chips of the scene overview. A MODIFIED block cannot drop the outlet scenarios.
**Migration**: "A fixed-column dock pane sizes its columns to content" keeps the column-sizing and compression rules for the remaining fixed-column panes. The exit chips' wrapping is covered by "The exploration dock is keyboard-first and roots at the scene overview" (`webclient-exploration-menu`). Test annotations re-anchor accordingly.
