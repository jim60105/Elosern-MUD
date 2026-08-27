## MODIFIED Requirements

### Requirement: The action dock renders as a floating panel in the stage's dock anchor
The action dock SHALL render inside the stage's `dock` anchor as one floating panel bounded to a
maximum width and horizontally centred, drawn with the stage's panel gradient, a hairline top border
and an upward shadow so it reads as a surface floating above the scene rather than a full-width page
row. Its height SHALL come from the shared `--dock-h` token and SHALL NOT grow with its content. The
panel SHALL be laid out as a fixed-height tab bar, an optional breadcrumb line, and one remaining
region that holds the current frame's rows; that region SHALL be the panel's only scrolling area, so
no dock content is ever pushed outside the anchor. The panel SHALL be the same single `#action-dock`
element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the
surface's documented focus target, and SHALL NOT be remounted when the mode changes.

The panel's background gradient and shadow SHALL match the values `docs/design/elosern-redesign/index.html`
(the binding visual reference) draws for its dock surface — the panel reads as receding into shadow
toward its lower edge, not as a lit, tinted card.

#### Scenario: The dock is one centred floating panel
- **WHEN** the shell renders at 1440x900 in exploration mode
- **THEN** the dock renders as a single centred panel inside the dock anchor with a bounded maximum width, a top border and an upward shadow, and its height equals the shared dock-height token

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the panel's row region can display
- **THEN** the row region scrolls internally, the tab bar and the breadcrumb stay fixed, and no row is rendered outside the dock anchor

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute switches to the new mode, and it is not removed and re-created

#### Scenario: The panel stays inside its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock panel's rendered box stays within the dock anchor, and the frame's confirm control is reachable by scrolling the row region without being clipped

#### Scenario: The panel's background matches the reference's shadowed gradient
- **WHEN** the dock panel renders in any mode
- **THEN** its background gradient and box-shadow are the same values `docs/design/elosern-redesign/index.html` draws for its dock surface

### Requirement: The dock's root frame renders as an icon tab bar with truthful count badges
The current dock surface's root menu frame SHALL render as a horizontal tab bar, one tab per root
item, each carrying a decorative glyph and its server-authored text label. The open root entry's tab
SHALL be marked with the accent fill, and the marking SHALL NOT be the only indication of state. When
the router is at the root frame the tab bar SHALL be the surface's row container: it SHALL carry the
listbox role, be the surface's single tab stop, name the focused tab through an active-descendant
association, and carry each root item's preserved row identity attribute and row id. When a deeper
frame is open the tab bar SHALL become inert ancestor chrome that marks which root entry is open and
SHALL NOT be a second tab stop.

A tab's decorative glyph SHALL match the icon `docs/design/elosern-redesign/index.html` (the binding
visual reference) draws for that same tab concept, for every root or combat-root key the reference
itself draws an icon for. A key with no counterpart in the reference (a client-local entry the
reference's static draft never modelled, such as a sub-dock shortcut) SHALL carry whatever glyph best
represents it and is never required to match a reference that does not exist.

A tab SHALL carry a count badge only when the number of rows its frame will contain is derivable
from the committed payload before that frame is opened; the badge SHALL equal that count exactly. A
tab whose count is zero or not derivable SHALL carry no badge. A badge SHALL NEVER be rendered from
an estimate, from a value the panel does not carry, or for rows the frame will not list.

The root menu's focus geometry SHALL match the rendered tab order: the root frame's column count
SHALL equal its item count, so the horizontal arrow keys traverse the visible tabs and the vertical
arrow keys are a no-op on the root.

#### Scenario: The root renders as tabs and owns the listbox
- **WHEN** the dock is at its root frame
- **THEN** each root item renders as a tab with a glyph and its label, the tab bar carries the listbox role with a single tab stop and an active-descendant reference, and each tab carries its preserved row identity attribute

#### Scenario: A tab glyph matches the reference design's icon for the same concept
- **WHEN** the exploration root renders the 移動/查看/互動/建議 tabs, or the combat root renders the 攻擊/技能/道具/防禦/逃跑/投降 tabs
- **THEN** each tab's glyph is the same pictogram `docs/design/elosern-redesign/index.html` draws for that tab's concept

#### Scenario: Badges equal a real count
- **WHEN** the committed exploration panel carries two interact targets and the committed suggestions payload carries four ready cards
- **THEN** the interact tab shows the badge `2`, the suggestions tab shows the badge `4`, and the look and move tabs show no badge

#### Scenario: A zero or unknowable count shows no badge
- **WHEN** a tab's frame would contain no rows, or its row count cannot be derived from the committed payload
- **THEN** that tab renders no badge at all rather than a zero or a placeholder

#### Scenario: Tab focus geometry matches the rendered order
- **WHEN** the player presses the horizontal arrow keys on the root frame
- **THEN** focus moves through the tabs in their rendered order and wraps at the ends, and the vertical arrow keys move focus nowhere

#### Scenario: An open deeper frame leaves the tab bar inert
- **WHEN** a deeper frame is open
- **THEN** the tab bar marks which root entry is open, the deeper frame's row container is the surface's only listbox and only tab stop, and no tab is reachable by sequential keyboard navigation

## ADDED Requirements

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend text naming the keyboard behaviour it actually implements.
The legend SHALL render exactly once as visible content; any additional copy kept only to satisfy a
test hook on a different element SHALL be rendered visually hidden (removed from the visual layout and
from the accessibility narration order a sighted-equivalent reading would follow) while remaining present
in the DOM and readable by its `data-testid`.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no longer
behaves as named. When a named affordance's behaviour changes (for example, a control that used to open
a surface and now only moves focus into an always-present one), the legend's wording SHALL be updated in
the same change that alters the behaviour.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carrying the shortcut-legend text is visible, and any other element carrying the same text is visually hidden

#### Scenario: The legend names the command line's real focus behaviour, not an open/close toggle
- **WHEN** the shortcut legend names the command-line-focus key
- **THEN** its wording states that the key focuses the command line, and does not state that the key opens or closes it
