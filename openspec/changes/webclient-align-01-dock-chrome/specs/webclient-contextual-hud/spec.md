# Delta spec: webclient-contextual-hud (webclient-align-01-dock-chrome)

## MODIFIED Requirements

### Requirement: The action dock renders as a floating panel in the stage's dock anchor
The action dock's band SHALL fill the stage's `dock` anchor at full stage width, drawn with the
stage's panel gradient, a hairline top border, and an upward shadow exactly as
`docs/design/elosern-redesign/index.html` (the binding visual reference) draws its full-width
`.dockwrap` band, so no stage background ever shows beside the band at any viewport width. Inside
the band, the dock content SHALL render as one horizontally centred column bounded to the
reference's maximum content width, and the combined band-plus-content surface SHALL read as the
dock surface floating above the scene. Its height SHALL come from the shared `--dock-h` token and
SHALL NOT grow with its content. The content column SHALL be laid out as a fixed-height tab bar,
an optional breadcrumb line, and one remaining region that holds the current frame's rows; that
region SHALL be the surface's only scrolling area, so no dock content is ever pushed outside the
anchor. The panel SHALL be the same single `#action-dock` element in every mode, carrying its
existing tab index, its `data-mode` attribute and its role as the surface's documented focus
target, and SHALL NOT be remounted when the mode changes.

The band's background gradient, top border, and shadow SHALL match the values
`docs/design/elosern-redesign/index.html` draws for its dock surface — the band reads as receding
into shadow toward its lower edge, not as a lit, tinted card.

#### Scenario: The band is full-width with a centred content column
- **WHEN** the shell renders at any viewport width from 1280x720 to 1920x1080 in exploration mode
- **THEN** the painted band spans the full stage width inside the dock anchor, the content column
  is centred within the reference's maximum width, and no unpainted stage background appears
  beside the band

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the tab bar and the breadcrumb stay fixed, and no
  row is rendered outside the dock anchor

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, and it is not removed and re-created

#### Scenario: The panel stays inside its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the dock anchor, and the frame's confirm control
  is reachable by scrolling the row region without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the dock band renders in any mode
- **THEN** the band element's background gradient, top border, and box-shadow are the same values
  `docs/design/elosern-redesign/index.html` draws for its dock surface

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry a shortcut-legend element matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: for the modes this
capability renders, the text `數字鍵 1–4 · ` followed by an `<kbd>` element naming `Enter` and the
verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`, rendered
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

#### Scenario: The legend renders once
- **WHEN** the dock renders in a mode where its chrome (tab bar) is shown
- **THEN** exactly one element carries the shortcut-legend text and test hook, and no duplicate
  copy is rendered

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock tab bar renders in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–4 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named
