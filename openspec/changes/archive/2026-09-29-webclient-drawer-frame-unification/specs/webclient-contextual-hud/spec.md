## ADDED Requirements

### Requirement: Reference surfaces share an opaque accessible frame
Reference drawers and full-screen overlays SHALL present one shared header: a decorative leading glyph,
the surface title, an optional subtitle, and one icon-only close control of at least 36x36px carrying an
accessible name, in the same order and position on every surface. The header SHALL be presentational
only: it SHALL emit a close request and own no focus trap, Escape handling, opener record, or
open-surface registration, all of which stay with the drawer or overlay host that renders it. The
header glyph SHALL come from the same glyph registry the top navigation draws its entries from, so a
surface opened from a navigation control shows that control's glyph, and every reference drawer and
every utility overlay SHALL declare one; no surface SHALL fall back to a generic placeholder glyph. A
surface whose body used to render its own title and close control SHALL render them only through the
shared header, so each surface carries exactly one title and one close control.

The body of every reference drawer and utility overlay SHALL be a fully opaque ink panel over a
stage-dimming scrim, so no stage, band, or command-line text shows through it; a backdrop blur MAY
decorate the scrim, but opacity SHALL NOT depend on `backdrop-filter` support. The recession and the
scrim SHALL dim only what lies behind the panel, never the panel itself. Existing modal focus, close,
and restore behavior SHALL remain unchanged, and the workspace bounds SHALL remain those of the
reference drawer and overlay requirements.

#### Scenario: Blur is unavailable
- **WHEN** a reference surface opens in a browser without backdrop-filter
- **THEN** stage text is still invisible through the opaque panel and body content remains readable

#### Scenario: One owner handles closing
- **WHEN** a gallery nested editor closes and then the gallery closes
- **THEN** each close is handled by its existing modal owner, focus returns to the correct opener and no duplicate header or focus trap is introduced

#### Scenario: Headers agree
- **WHEN** the same tool is opened from navigation
- **THEN** the header uses the matching glyph and has one named close control in the shared position

## MODIFIED Requirements

### Requirement: A full-screen overlay is one focus-trapped surface, and only one is open at a time
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying the shared
reference-surface header naming the surface and a labelled close control, with its body as its only
scrolling region. Utility overlays SHALL use the same opaque reference workspace as the reference
drawers: 12px below the top navigation's bottom edge, 16px inside each side of the viewport, and one
command-line row height plus 12px above the viewport bottom, so the workspace covers the stage, the
bottom band, and the command-line row whether or not that row is expanded, and only the band's lowest
control strip stays exposed beneath it. A scrim SHALL cover everything below the top navigation behind
the overlay, recessing that exposed strip, and SHALL absorb pointer activation without closing the
overlay, so no command control behind the overlay is reachable by pointer; the scrim starts at the top
navigation's bottom edge and does not cover it, so the navigation stays operable and activating another
overlay or drawer trigger replaces the open overlay as below. The mode-owned creation workspace is excluded from these utility-frame bounds. While an overlay
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It
SHALL close on Escape and on activation of its close control, and both paths SHALL restore focus to the
control that opened it. It SHALL use the shared focus trap the client already owns rather than a second
implementation.

At most one overlay SHALL be open at any time; opening a second SHALL close the first, and the opener
recorded for the replacement is the control that opened it, so closing restores focus to the most recent
trigger, never to the trigger of the closed overlay. An overlay and a
reference drawer SHALL NOT be open together: opening either SHALL close the other, so at most one
focus-trapped surface exists at any moment. An open overlay SHALL register itself as an open surface so
the stage recession this capability already requires applies without a second mechanism.

Escape SHALL be resolved by a single precedence order, topmost first — a popover open inside the open
overlay, then the open overlay, then an open drawer, then the focused command field, then the dock's
current menu level — with each level consuming the key and stopping. A popover open inside an overlay
SHALL close on Escape without closing the overlay, keeping focus inside the overlay, and the next
Escape SHALL close the overlay; while no such popover is open, Escape closes the overlay as above.

A mode change into creation, a presentation-epoch reset and a loss of the transport SHALL each close
every open overlay. The mode-driven character-creation surface SHALL NOT be part of this single-open
stack, because it is not opened by the player and a utility control must never dismiss it.

#### Scenario: An overlay opens, traps focus, and returns it
- **WHEN** the player activates an overlay trigger, cycles focus forward past the overlay's last control and backward past its first, and then presses Escape
- **THEN** focus stays inside the overlay in both directions, the overlay closes on Escape, and focus returns to the trigger that opened it

#### Scenario: Only one overlay is open at a time
- **WHEN** an overlay is open and the player activates a different overlay's trigger
- **THEN** the first overlay closes as the second opens, and exactly one overlay is present

#### Scenario: An overlay and a drawer are never open together
- **WHEN** a reference drawer is open and the player activates an overlay trigger
- **THEN** the drawer closes as the overlay opens, and exactly one focus-trapped surface is present

#### Scenario: Escape resolves at exactly one level
- **WHEN** an overlay is open above a focused command field and a dock frame at depth two, and the player presses Escape once
- **THEN** the overlay closes, focus returns to its trigger, the command field's content is untouched, and the dock's menu depth is unchanged

#### Scenario: Closing the last overlay clears the recession
- **WHEN** the open overlay closes and no drawer remains open
- **THEN** the stage's recession mark is cleared

#### Scenario: A creation transition closes the overlays
- **WHEN** the committed mode changes to creation while an overlay is open
- **THEN** that overlay closes, focus is routed to the action dock, and the character-creation surface is not itself treated as one of the single-open overlays

#### Scenario: An overlay's own popover takes Escape first
- **WHEN** the full-map overlay is open with its legend popover expanded, and the player presses Escape twice
- **THEN** the first Escape closes only the popover and focus stays inside the overlay, and the second Escape closes the overlay and returns focus to the trigger that opened it

### Requirement: Reference surfaces render in a right-anchored drawer with one modal contract
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's
bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the
viewport bottom, so the workspace covers the stage, the bottom band, and the command-line row whether or
not that row is expanded, and only the band's lowest control strip stays exposed beneath it. A fine
border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage. The existing
modal drawer lifecycle and shared motion tokens SHALL be retained over a dimmed scrim covering the whole
viewport behind the drawer. Between its header and optional footer, a decorative art column MAY
accompany the scrolling content body; only the content body scrolls. The head SHALL be the shared
reference-surface header: the title in the serif heading face at the shared workspace scale with slight
tracking, and the subtitle as the small muted line beside it. Every reference drawer SHALL declare one
leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its
title). The drawer's close control SHALL carry an accessible name (e.g. an `aria-label`) but MAY be
rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name,
not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a
subtitle stating its owner's active and passive skill counts (`主動 {n} · 被動 {m}`, computed from that
same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is
empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer
SHALL carry a footer stating the client's own cast-command syntax
(`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB
protocol carries, so its presence does not depend on any panel's availability — whenever the drawer
presents the skill book itself; while the declared-practice sub-screen replaces the book body, that
footer is absent and the head title reads 修煉, because the cast syntax belongs to the book view the
sub-screen replaced.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the workspace is bounded below the navigation and above the band's lowest control strip, covering the command-line row, as an opaque panel over a dimmed scrim, its content body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the serif heading face with slight tracking and the subtitle renders as the small muted line beside it

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

#### Scenario: The close control is icon-only but keeps its accessible name
- **WHEN** a reference drawer's close control renders
- **THEN** it carries no visible text node, renders a decorative close glyph, and exposes the same accessible name (e.g. `aria-label="關閉"`) an assistive technology would have read from the previous visible text

#### Scenario: The skill-book drawer states its skill counts and cast syntax
- **WHEN** the skill-book drawer opens with the `character` panel available
- **THEN** its head carries a leading skill glyph and a `主動 {n} · 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once (not duplicated inside the body), and its footer states the client's `/cast` syntax as static copy
