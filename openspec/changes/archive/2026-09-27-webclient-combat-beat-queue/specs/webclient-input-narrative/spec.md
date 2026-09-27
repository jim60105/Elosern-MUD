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
reader's text speed and auto-advance is opt-in". While a combat round plays by itself, as
`webclient-combat-menu` "A combat round plays beat by beat" defines, the same pointer activation or key
SHALL instead end the round at once and SHALL NOT complete or advance a page.

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

#### Scenario: A click during a playing round ends it
- **WHEN** a combat round is playing its second of three beats and the player presses Enter on the page
  surface
- **THEN** the round ends, the window shows the response's page after the beat pages, and no beat page is
  skipped in the full log

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
