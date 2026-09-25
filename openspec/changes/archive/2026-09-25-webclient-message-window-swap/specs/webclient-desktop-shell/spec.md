## MODIFIED Requirements

### Requirement: Player input lines are part of the narrative stream with a divider

The narrative log SHALL retain, in addition to server text, one input line per deliberate player
action: a typed command send echoes the exact raw text the player sent, and a button-triggered
mutation echoes its resolved command line (see the `webclient-input-narrative` capability). Input
lines SHALL be inserted as literal text through the same single append path as narrative output,
forcing a new line, and SHALL be styled distinctly from server output (`.inp`) wherever they render.
An input line SHALL head the response it begins. It SHALL render in the full-log surface and SHALL NOT
be one of the message window's pages. In the full-log surface, a `.narrative-divider` hairline SHALL
separate each input line from the preceding server or input line, so system prose and player actions
never visually merge while re-reading. The divider SHALL NOT appear before the very first line of the
log. One input event (divider and input line together) SHALL begin exactly one response. An input
line SHALL never be executed, replayed, or sent back to the server. The append path SHALL handle an
input line exactly like a server line that fails to tokenize: degrade to literal text and never
suppress the log.

#### Scenario: A typed command appears with a divider
- **WHEN** the player types a command in the command line and sends it while a page of the
  previous response is on screen
- **THEN** the full-log surface shows one `.inp` line containing the raw sent text, preceded by a
  `.narrative-divider`; the message window shows no input line and presents the command's reply
  from its first page; and the text is never sent back to the server

#### Scenario: A button action appears with a divider
- **WHEN** the player submits `explore.move` via the dock or the minimap
- **THEN** the full-log surface shows one `.inp` line with its resolved command line, preceded by a
  `.narrative-divider`, with the server output that follows after it, and the message window shows
  that output as a new response

#### Scenario: The first line needs no separator
- **WHEN** a fresh log's first entry is an input line
- **THEN** the full-log surface renders it with the input style but without a preceding divider
  hairline

#### Scenario: Input lines are never executed
- **WHEN** the player re-reads the log and its input lines sit alongside server lines
- **THEN** no line is ever sent to the server, nothing is replayed, and the log content has no effect on
  game state

## ADDED Requirements

### Requirement: Narrative output remains the authoritative text surface and is read page by page
The shell SHALL route Evennia's existing narrative and command output to the retained narrative log
without parsing it to infer panel state. Because the portal converts server output to HTML before the
`text` message is sent, every surface that renders the log SHALL render that stream through the
`webclient-narrative-markup` allowlist pipeline rather than inserting it as a single text node. It
SHALL NOT display markup source to the player, and it SHALL NOT interpret anything outside that
pipeline's allowlist. The message window SHALL present the log one page of the current response at a
time (see `webclient-contextual-hud` and `webclient-input-narrative`). The complete retained log SHALL
stay readable, in order and through the same pipeline, in the full-log surface, one action away. New
output SHALL never force the reader off the page on screen, and no unread counter SHALL be rendered:
the page marker states that more pages remain, and a new action flushes unread pages to the log
rather than discarding them. Narrative output SHALL remain usable if every structured renderer is
unavailable. It SHALL remain usable if a message cannot be fully tokenized: such a message degrades to
readable literal text rather than suppressing the log.

#### Scenario: New text does not move the reader off the page
- **WHEN** the player is reading page 1 of the current response and more text of that response
  arrives
- **THEN** the page on screen is unchanged and the page marker reads `▼`

#### Scenario: Unread pages stay reachable in the complete log
- **WHEN** the player acts while pages of the previous response remain unread and then opens the
  full-log surface
- **THEN** every line of the previous response, including the unread pages' text, is present in the
  full-log surface in order

#### Scenario: Structured failure does not suppress narrative
- **WHEN** status validation and OOB initialization fail
- **THEN** ordinary text output continues to appear in the message window and the full-log surface

#### Scenario: Converted server output renders as text, not as markup source
- **WHEN** the server sends ordinary room, command, or narrator output that the portal converted to HTML
- **THEN** the message window's page and the full-log surface show the styled, line-broken prose and
  no element, attribute, or entity source characters are visible

## REMOVED Requirements

### Requirement: Narrative output remains the authoritative text surface
**Reason**: Its scroll-keep and unread-indicator clauses and scenarios describe the scrolling caption, which the AVG message window (design §6) replaces. The unread scenarios cannot survive a MODIFIED block, so the requirement is replaced.
**Migration**: "Narrative output remains the authoritative text surface and is read page by page" (this capability). Annotations re-anchor to it.
