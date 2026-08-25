## ADDED Requirements

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces placed in the stage's `hud-left` and `hud-right` anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The left anchor SHALL
carry the character head card, the vitals, and the conditions as three sibling islands in that fixed
order. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with the `status` and `character` panels available
- **THEN** the head card, the vitals, and the conditions render as three separately-chromed islands in that order, each with the translucent blurred panel chrome, and none of them is a single opaque column card

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** the island stack's rendered box fits inside its anchor and does not intersect the action dock, the narrative caption, or the opposite anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

### Requirement: The character head card renders only backed identity
The character head card SHALL render exactly the identity the committed payloads carry: a glyph
portrait tile derived from the display name in `status.actor.name`, a numeric badge from the
`magic_level` trait row's current value, that display name, a rank line pairing the magic rank title
derived from the numeric magic level with the guild rank and merit from `character.guild`, the wallet
from `character.wallet` formatted as thousands-grouped integer copper, and an explicit disguise marker
when `status.disguise_active` is true.

The portrait tile SHALL be a glyph and SHALL NOT contain an image element: the player is never a
present focusable subject of their own exploration catalog, so no portrait asset exists for them and
none SHALL be invented. An empty or absent display name SHALL render an empty tile rather than a
substitute character.

The card SHALL NOT render a race, subrace, class, or faction line in any form — not as a value, not as
a placeholder, and not as an unknown marker — because no such field exists in the `status` or
`character` payload. The magic rank title SHALL be a pure function of the numeric magic level, derived
client-side for display only, and SHALL NOT be requested from, or invented as, a payload field. When a
disguise is active, the badge and the rank line SHALL render the **true** trait value; a displayed
disguise value SHALL NOT be substituted for it.

The head card SHALL be the client's single persistent wallet surface.

#### Scenario: The head card renders the backed identity fields
- **WHEN** the `status` and `character` panels are committed for an actor with a magic level, a guild rank and merit, and a wallet balance
- **THEN** the card shows the glyph portrait tile with the numeric magic-level badge, the display name, the derived magic rank title paired with the guild rank and merit, and the thousands-grouped wallet in copper

#### Scenario: No race, class, or faction line is rendered
- **WHEN** the head card renders for any actor
- **THEN** no race, subrace, class, or faction value, placeholder, or unknown marker appears anywhere on the card

#### Scenario: The portrait is a glyph, never an image
- **WHEN** the head card renders outside combat
- **THEN** the portrait tile contains a glyph derived from the display name and contains no image element and no asset URL

#### Scenario: An active disguise leaves the true magic level on the card
- **WHEN** a disguise is active and the `character` payload's displayed rows carry a magic-level value that differs from the true trait
- **THEN** the badge and the rank line render the true trait value, and the displayed disguise value does not replace it

#### Scenario: The wallet has one persistent surface
- **WHEN** the HUD renders with the `character` panel available
- **THEN** the wallet is present on the head card and no other persistently-visible HUD surface renders a second wallet figure

### Requirement: Vitals pair an icon, a label, and numerals with a trailing damage bar
Each of hp, mp, and sp SHALL render as one vital row carrying an icon, a Traditional Chinese label,
and the `current / maximum` numerals from `status.resources`, above a track containing a trailing bar
and a fill. The numerals SHALL render at every value, so no vital state is conveyed by the coloured
fill alone. The sp fill SHALL carry a non-colour texture distinguishing it from the hp and mp fills.

The trailing bar SHALL exist to make damage taken visible: it SHALL lag the fill when the ratio falls
and SHALL be overtaken by the fill when the ratio rises. It SHALL be decorative — hidden from the
accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already
carry on the same revision. It SHALL NOT render any value that was not a previously committed ratio of
that same gauge, SHALL NOT be interpolated or extrapolated from narrative text or an action result,
and SHALL reset to the current ratio when the epoch changes, so no trail is drawn across a reconnect.
Its motion SHALL be token-gated so the reduced-motion block disables it.

A vital at or below the client's display threshold SHALL be marked by both a recolour and an explicit
text marker, never by the recolour alone.

#### Scenario: Each vital is legible without colour
- **WHEN** the vitals island renders with the `status` panel committed
- **THEN** each of hp, mp, and sp shows an icon, a text label, and its `current / maximum` numerals, and the sp fill is distinguishable from hp and mp by texture rather than by hue

#### Scenario: Damage leaves a visible trailing bar
- **WHEN** a committed revision lowers a gauge's ratio
- **THEN** the fill moves to the new ratio and the trailing bar follows behind it, so the gap between them shows the amount lost, and the numerals show the new value immediately

#### Scenario: Healing shows no trailing bar
- **WHEN** a committed revision raises a gauge's ratio
- **THEN** the fill overtakes the trailing bar and no lagging gap is drawn

#### Scenario: The trailing bar never shows an uncommitted value
- **WHEN** the trailing bar renders at any point
- **THEN** its width corresponds to a ratio that was previously committed for that same gauge, and it is absent from the accessibility tree

#### Scenario: A reconnect does not draw a trail across epochs
- **WHEN** a new epoch's snapshot commits after a reconnect
- **THEN** the trailing bar resets to the current ratio and no gap is drawn between the pre-reconnect and post-reconnect values

#### Scenario: A low vital is marked by text as well as colour
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** the row carries both the low recolour and an explicit text marker, and the numerals continue to render

### Requirement: The low-HP presentation state is derived client-side and drives the stage hook
The client SHALL derive a low-HP presentation state from the committed `status.resources.hp` ratio
alone, against a single display-only threshold, and SHALL expose it on the stage root through the
shell's existing low-HP hook so the stage renders its red vignette and the hp fill renders its pulse.

The threshold SHALL be a presentation constant: no server field, trait, or condition expresses "low
health", and the client SHALL NOT request one, invent one on the wire, or treat the derived state as
canonical. The state SHALL NOT be load-bearing — the numerals and the low text marker SHALL convey the
same information at every value, so a viewer who perceives neither the vignette nor the pulse loses
nothing. When the `status` panel is unavailable the state SHALL be false rather than true by default.
The pulse and the vignette transition SHALL be token-gated so the reduced-motion block disables the
motion while the marker and the numerals still apply.

#### Scenario: Crossing the threshold lights the stage
- **WHEN** a committed revision takes the hp ratio to or below the display threshold
- **THEN** the stage root carries the low-HP state, the stage renders its red vignette, and the hp fill renders its pulse

#### Scenario: Recovering clears the stage state
- **WHEN** a later committed revision takes the hp ratio back above the threshold
- **THEN** the low-HP state clears and the stage returns to its ordinary vignette

#### Scenario: An unavailable status panel is not low HP
- **WHEN** the `status` panel commits its unavailable form
- **THEN** the low-HP state is false, no red vignette is rendered, and no hp value is fabricated

#### Scenario: Reduced motion keeps the information and drops the motion
- **WHEN** `prefers-reduced-motion` is set and the hp ratio is below the threshold
- **THEN** the pulse animation is disabled while the low text marker, the numerals, and the recoloured row still render

### Requirement: Condition chips carry a severity glyph, a payload duration, and a bounded overflow
Each entry in `status.conditions` SHALL render as one chip pairing a per-severity shape glyph with an
accessible name carrying the condition's label, its remaining duration when the payload supplies one,
and every derived modifier the payload provides. The five severities SHALL each map to a distinct
glyph shape, so two severities are never separated by colour alone, and the beneficial and harmful
directions SHALL be readable from the glyph itself. Because the chip is icon-only, the island SHALL
also present that label, duration, and modifier text visibly when a chip is focused or hovered, so the
information the chip moves into its accessible name stays reachable by pointer and by keyboard.

The duration badge SHALL render only when the payload carries `remaining_seconds` for that condition;
a condition without one SHALL render no badge and no substitute value. The badge SHALL show the
payload's integer verbatim and SHALL NOT be decremented, animated down, or otherwise advanced by the
client between committed revisions.

Visible chips SHALL be bounded, and the remainder SHALL be reachable in one action through an overflow
chip stating how many are hidden. The overflow surface SHALL be bounded and scrollable and SHALL close
on Escape, so no committed condition becomes unreachable at any condition count the payload permits.
An empty condition list SHALL render an explicit text statement rather than an empty island.

#### Scenario: A chip carries its label, duration, and modifiers
- **WHEN** a condition with a label, a remaining duration, and a derived modifier is committed
- **THEN** its chip renders the severity glyph and a duration badge, and its accessible name states the label, the remaining duration, and the modifier and its value

#### Scenario: Two severities are distinguishable without colour
- **WHEN** a warning condition and a harmful condition are committed together
- **THEN** their chips carry different glyph shapes and remain distinguishable with colour removed

#### Scenario: A condition without a duration renders no badge
- **WHEN** a committed condition carries no `remaining_seconds`
- **THEN** its chip renders no duration badge and no substitute value in its place

#### Scenario: The duration does not tick between revisions
- **WHEN** a chip with a duration badge is displayed and no new revision commits
- **THEN** the badge continues to show the payload's value unchanged, and the client runs no countdown

#### Scenario: Overflowing conditions stay reachable
- **WHEN** more conditions are committed than the island shows as chips
- **THEN** an overflow chip states the hidden count and reveals every remaining condition in one action, within a bounded scrollable surface that closes on Escape

#### Scenario: No conditions renders an explicit statement
- **WHEN** the committed condition list is empty
- **THEN** the island renders an explicit text statement that there are no conditions

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's right anchor, beneath the top-meta
surface, carrying the committed `local_map` payload's title. Where the payload's layer places nodes on
coordinates, the island MAY state the renderer's own axis convention as an orientation legend; where
the layer is coordinate-free, it SHALL omit that legend rather than assert one. The island SHALL NOT
render a bearing, a compass angle, or a distance in any form, because node coordinates are
renderer-local presentation geometry and not canonical world coordinates.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. The minimap's existing
per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates
- **THEN** the island may render the renderer's axis orientation legend alongside the map title

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation legend rather than asserting a direction the payload does not support

#### Scenario: No bearing or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing, or distance figure appears anywhere in the island

#### Scenario: No control opens an unmounted surface
- **WHEN** the full-map surface is not mounted in the application
- **THEN** the island presents no full-map control, and the per-node movement submission continues to work unchanged
