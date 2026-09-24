## MODIFIED Requirements

### Requirement: The message window's reading controls advance pages and a new action flushes unread pages
A pointer activation on the message window SHALL act on the current page, except when it lands on a
control inside the window or ends a text selection inside it. While the page is still typing, the
activation SHALL show the page in full and SHALL NOT advance. Once the page is fully shown, the
activation SHALL advance to the next page of the current response. The window's page surface SHALL
be focusable and in the tab order. Enter or Space SHALL act the same way, and only while keyboard
focus is on that page surface. Such a key SHALL be consumed by the window and SHALL NOT reach the
action dock's keyboard routing, and a held key's auto-repeat SHALL NOT act. While focus is anywhere
else (the action dock, a drawer, an overlay, the command line, or a control in the band), Enter and
Space SHALL keep their existing meaning and SHALL NOT complete or advance a page. Advancing on a fully
shown last page SHALL do nothing. How a page is revealed is defined by "A page types in at the
reader's text speed and auto-advance is opt-in".

The player SHALL be able to act at any time while a page is typing or pages remain. When an action
records its response mark or appends its input line, the window SHALL stop typing and SHALL stop
presenting the previous response's unread pages. It SHALL show that response's last page, fully
shown, until the new response's first line is retained. It SHALL then show the new response's first
page. The unread pages SHALL remain in the full-log surface. Lines appended to the response being read
SHALL NOT move the reader off the page on screen. A change of the window's box or of the prose scale
SHALL re-page the current response and SHALL keep the reader on the page that holds the typing
position. The typing position is the next character to reveal while a page is typing, or the last
character shown once the page is complete. On that page, the text before the typing position SHALL
show at once, and the rest SHALL keep typing.

Paging SHALL wait until the client's fonts have loaded. Until then the window SHALL show the current
response's first block in full, scrollable. When the window mounts, including after a reconnect, it
SHALL show the last page of the last response fully shown, and SHALL NOT type or replay earlier pages.

A polite live region SHALL announce each page's full text once, at the moment the page starts to
show, and never per typed character. It SHALL announce each line later appended to the page on screen
once. It SHALL announce nothing when typing completes, on a re-page, or on a mount. The page surface
itself SHALL NOT be a live region. None of this SHALL change the narrative log, the dispatch path, or
any request.

#### Scenario: A click advances the page
- **WHEN** the current response has three pages shown at the `instant` text speed and the player
  clicks the window twice
- **THEN** the window shows page 2 and then page 3, and the marker reads `■`

#### Scenario: A press while typing completes the page
- **WHEN** page 1 of a two-page response is still typing and the player clicks the window, then
  presses Enter on the page surface
- **THEN** the click shows page 1 in full with the marker `▼` and does not advance, and the Enter
  advances to page 2

#### Scenario: Enter on the page surface advances
- **WHEN** the page surface has keyboard focus on a fully shown page and the player presses Enter,
  then Space, with each following page fully shown before the next key
- **THEN** each key advances one page, and the action dock's focused item is not activated and
  its multi-select state does not change

#### Scenario: Enter on the dock does not advance
- **WHEN** the current response has further pages, its page is typing, and the player presses
  Enter with focus on the action dock
- **THEN** the dock activates its focused item exactly as before, the page keeps typing, and the
  window's page does not change

#### Scenario: A held key does not skip pages
- **WHEN** the player holds Enter on the page surface of a four-page response whose first page is
  typing
- **THEN** the first key event completes page 1, the auto-repeated events do nothing, and the
  window stays on page 1

#### Scenario: Acting while reading flushes the unread pages
- **WHEN** the player is on page 1 of a three-page response while it types and activates a dock
  move whose echo and room text then arrive
- **THEN** typing stops, the window shows the move's response from its first page, and pages 2 and
  3 of the earlier response are still present in the full-log surface

#### Scenario: A silent action flushes before its reply arrives
- **WHEN** the player is on page 1 of a two-page response and activates the dialogue exit row,
  and no line has arrived yet
- **THEN** the window shows the earlier response's last page, fully shown with `■`, until the
  farewell line arrives, and then shows that line's page

#### Scenario: New lines do not move the reader
- **WHEN** the player is on page 1 of the current response and further lines of the same response
  arrive and form a second page
- **THEN** the window stays on page 1, and once page 1 is fully shown the marker reads `▼`

#### Scenario: A resize keeps the reader's text on screen
- **WHEN** the player is on page 2 with its typing position at a known character, and the viewport
  shrinks from 1920x1080 to 1280x720
- **THEN** the window shows the page of the new paging that holds that character, the text before
  it on that page is shown at once, and typing continues from it

#### Scenario: A prose-scale change keeps the reader's text on screen
- **WHEN** page 2 is fully shown and the player changes the prose scale in the settings surface
- **THEN** the current response is re-paged, and the window shows the page holding the last
  character that was shown, with that character and everything before it on the page shown

#### Scenario: Pages wait for fonts
- **WHEN** the client's fonts have not finished loading and a response arrives
- **THEN** the window shows that response's first block in full, scrollable, and pages it only
  after the fonts have loaded

#### Scenario: A reconnect shows the last page
- **WHEN** the transport drops and reconnects, or the window mounts with a retained log
- **THEN** the window shows the last page of the last response fully shown with no typing, and no
  earlier page is shown or announced

#### Scenario: Each page is announced once
- **WHEN** a two-page response arrives at the `normal` text speed, the player waits for page 1 to
  finish typing, advances once, and the viewport is then resized
- **THEN** the polite live region has announced page 1's full text once, when page 1 started
  typing, and page 2's full text once, when page 2 started typing. It announced nothing on the
  typed characters, on the completions, or on the resize.

## ADDED Requirements

### Requirement: A page types in at the reader's text speed and auto-advance is opt-in
Outside the dialogue variant, each page the message window starts to show SHALL reveal its text in
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

The dialogue variant SHALL NOT type and SHALL NOT auto-advance: its reply line, residual lines, and
rows appear in full at once. While mode is `dialogue` but the panel is unavailable, the paged
fallback SHALL type like any other page.

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
- **WHEN** mode is `dialogue`, the panel is available, and a new reply commits at the `slow` text
  speed with auto-advance on
- **THEN** the reply, the pick rows, and the exit row render in full at once, and nothing advances
  on its own
