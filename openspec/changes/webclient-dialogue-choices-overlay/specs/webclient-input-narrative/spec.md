## MODIFIED Requirements

### Requirement: A page types in at the reader's text speed and auto-advance is opt-in
In every mode, dialogue included, each page the message window starts to show SHALL reveal its text in
reading order, one character at a time, at the reader's text speed. The speeds are `slow` 20
characters per second, `normal` 45, `fast` 90, and `instant`, which shows the page in full at once.
A hard line break SHALL count as one character. A box-drawing map line SHALL appear whole when the
reveal reaches it. The reveal SHALL keep every character's final position from the first frame: text
not yet revealed SHALL occupy its place invisibly, so no line re-wraps and nothing moves while a page
types. Text not yet revealed SHALL be hidden from assistive technology. The reveal SHALL render the
same markup, spans, and classes as the fully shown page, SHALL emit no markup the narrative pipeline
does not produce, and SHALL run that pipeline no more than once per line.

Typing SHALL be instant, whatever the text speed, while the reduced-motion preference is on, or while
no reduced-motion preference is stored and the operating system requests reduced motion. An explicit
reduced-motion preference of off SHALL let pages type even when the operating system requests
reduced motion. A change of text speed or of the effective reduced-motion state SHALL apply from the
next page, except that a change to `instant` or to reduced motion SHALL also complete the page that
is typing. The page marker SHALL render only once the page is fully shown. Time the page spends in a
hidden browser tab SHALL NOT count toward typing.

When auto-advance is on and the page on screen is fully shown, the window SHALL advance to the next
page after `1.2s + 60ms × the page's characters`. The wait SHALL be counted from the later of the page
becoming fully shown and a next page existing. Auto-advance SHALL NOT advance past the last page of a
response. It SHALL NOT advance an oversize page or a page that holds a box-drawing map, which wait for
the player. The wait SHALL pause while any drawer, overlay, or the full-log surface is open, and while
the browser tab is hidden. A manual advance, a flush by a new action, or a re-page SHALL restart or
cancel the wait for the page then on screen. Auto-advance is off by default.

There is no separate dialogue presentation: in dialogue mode the session line is part of the current
response and SHALL type and auto-advance like any other page, and the conversation's choices appear
only once the response's last page is fully shown, as `webclient-contextual-hud` "Dialogue choices
appear centred over the stage after the line is fully read" defines. Auto-advance SHALL NOT advance
past the last page into the choices: the choices are not a page.

#### Scenario: A page types at the normal speed
- **WHEN** a one-page response of 90 characters arrives at the `normal` text speed with no
  reduced-motion preference and the operating system not requesting reduced motion
- **THEN** after about one second about 45 characters are visible, the page is fully shown after
  about two seconds, the marker is absent until then, and the text's rendered line boxes do not
  change between the first frame and the last

#### Scenario: Styled spans survive the reveal
- **WHEN** a page whose text carries a coloured span across the typing position is typing
- **THEN** the visible part of the span and its hidden remainder carry the same colour class, and
  the fully shown page's markup equals the markup of the same page at the `instant` speed

#### Scenario: Reduced motion forces instant pages
- **WHEN** the text speed is `slow` and the operating system requests reduced motion with no
  reduced-motion preference stored, or the reduced-motion preference is on
- **THEN** each page is fully shown with its marker as soon as it is shown

#### Scenario: An explicit off lets pages type
- **WHEN** the operating system requests reduced motion and the reduced-motion preference is off
- **THEN** pages type at the chosen text speed

#### Scenario: Auto-advance waits in proportion to the page and stops at the last page
- **WHEN** auto-advance is on and a three-page response arrives whose first page holds 100
  characters
- **THEN** page 2 starts about 7.2 seconds after page 1 is fully shown, page 3 follows the same
  rule, and the window stays on page 3 with `■`

#### Scenario: Auto-advance holds while a surface is open
- **WHEN** auto-advance is on, page 1 of two is fully shown, and the player opens the full-log
  surface for ten seconds and then closes it
- **THEN** the window is still on page 1 when the surface closes, and it advances only after the
  rest of the wait has passed

#### Scenario: Auto-advance leaves maps to the player
- **WHEN** auto-advance is on and the page on screen is an oversize box-drawing map with a next
  page behind it
- **THEN** the window stays on the map page until the player advances

#### Scenario: The dialogue variant does not type
- **WHEN** mode is `dialogue`, the panel is available, and a two-page reply commits at the `slow` text
  speed with auto-advance on
- **THEN** no unpaged dialogue presentation renders: page 1 types at 20 characters per second with no
  choice row visible, the window advances to page 2 after the auto-advance wait, page 2 types, and
  the window stays on page 2 with `■` while the dialogue choice list appears over the stage
