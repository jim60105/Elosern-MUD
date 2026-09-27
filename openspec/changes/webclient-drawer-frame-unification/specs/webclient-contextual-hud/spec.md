## ADDED Requirements

### Requirement: Reference surfaces share an opaque accessible frame
Reference drawers and overlays SHALL present a consistent icon/title/subtitle/close header and fully opaque body over a stage-dimming scrim. Content behind the body SHALL NOT show through, including when backdrop blur is unsupported. Existing modal focus, close and restore behavior SHALL remain unchanged; reference workspace bounds SHALL continue to clear the navigation and command line.

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
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying a header naming
the surface and a labelled close control, with its body as its only scrolling region. Utility overlays SHALL use the shared opaque reference workspace bounded below navigation and above the expanded command-line row, or above its reserved band-top edge when collapsed. The scrim SHALL recess any exposed stage/band content; no behind-surface command control is reachable while the modal trap is active. The mode-owned creation workspace is excluded from these utility-frame bounds. While an overlay
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
