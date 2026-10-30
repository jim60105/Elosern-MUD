## MODIFIED Requirements

### Requirement: The message window presents the current response one page at a time in the band's message region
Outside travel presentation, the narrative SHALL retain its bounded current-response message window and paging behavior; active travel presentation SHALL use a typed travel log in that region while preserving every ordinary narration line in the full log.

#### Scenario: The window wears the reference caption panel chrome
- **WHEN** the message window renders
- **THEN** it is drawn with the reference's caption panel treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow

#### Scenario: Paging follows the narrative and combat contracts
- **WHEN** the window presents the current response, including while that response carries a combat round the client presents
- **THEN** pages follow `webclient-input-narrative` and are revealed as its typing requirement defines , or, for a presented combat round, as that round's beat pages followed by the response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines , and earlier responses are not presented: they remain readable in the full-log surface

#### Scenario: The clear layer is the one paging exception
- **WHEN** a new response replaces the previous one
- **THEN** the previous page MAY remain only as an opaque layer over the new page that fades out within the clear duration of the client's motion level (at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility tree and pointer hit-testing from the moment the new response starts

#### Scenario: Page typography is bounded at the reference size
- **WHEN** page text renders at the 1451x790 reference size and the default prose scale
- **THEN** it is set in the bundled monospace reading face , the same Jim Mono TC family the monospace type role ships , at 18px, scales once with the desktop chrome factor and with the client's prose scale, and holds at most 42 CJK characters per line in every mode, including the whole-band width of dialogue mode

#### Scenario: The control strip carries the marker and the log control
- **WHEN** any page renders
- **THEN** the window's lower edge keeps a control strip in which no page text renders, holding a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle

#### Scenario: The marker names the page state decoratively
- **WHEN** the on-screen page is fully shown, typing, or a combat round plays by itself
- **THEN** the marker renders only while the page is fully shown and is absent while it types and while a combat round plays by itself; when rendered it reads `▼` while the current response has further pages and `■` on its last page; it is decorative (hidden from assistive technology) and blinks only through the client's motion tokens, so reduced motion stops the blink

#### Scenario: An oversize page scrolls without growing the window
- **WHEN** a page is taller than the window's text area
- **THEN** it scrolls inside the text area; it is never truncated and never grows the window

#### Scenario: The log control and scroll-up open the full log
- **WHEN** the player activates the `日誌` control, or scrolls up over a page that has nothing left to scroll up
- **THEN** the full-log surface opens in one action; its content, markup renderer, focus trap, Escape close, focus restore to the opening control, and opening at its latest line are unchanged

#### Scenario: The window carries no reading chrome beyond the plate
- **WHEN** the window renders in any mode
- **THEN** it renders no unread indicator, no jump-to-latest control, and no head row other than the dialogue name plate; in creation mode the window, its marker, and the `日誌` control are hidden with the message region

#### Scenario: The dialogue name plate names the host truthfully
- **WHEN** the committed mode is `dialogue` and the committed `dialogue` panel is available
- **THEN** the window plate names the current explicit actor or host, with bond-stage suffix only for host speech; narration has no speaker plate; native freeform retains host-name behavior; the text area pages/types the current attributed scene line or native response unchanged, with no separate reply box, rows, avatar or rewritten narrative; choices remain in the dialogue choice list

#### Scenario: A transient panel shows no plate, and reader state drives the choice list
- **WHEN** mode is `dialogue` but the panel is unavailable (the transient window between a clear seam and its commit)
- **THEN** the window renders no name plate, and the window makes known to the shell, from its own reader state and never from narrative prose, whether an authored scene has received its final explicit finish activation, or a native response last page is fully shown, with no pending action mark

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box , the band's height and two thirds of its
  width, or the whole band in dialogue mode , and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1451x790 with the default prose scale and a long prose response, in ordinary non-travel exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 18px (±0.5px) in the bundled monospace reading face and no rendered text line holds more
  than 42 CJK characters in either mode

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages, page 1 types to its end, and the player advances
  once and page 2 types to its end
- **THEN** no marker renders while either page is typing, the marker reads `▼` once page 1 is fully
  shown and `■` once page 2 is fully shown, and it is absent from the accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

#### Scenario: The dialogue line is paged under the name plate
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1451x790
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 ‧ 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode dialogue presents host speech with bond_stage null
- **THEN** host speech names the host alone, actor speech names the acting body alone, and narration has no speaker plate or bond text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

#### Scenario: Narration and actor plate change with text
- **WHEN** an actor speech begins after a host line and then narration begins
- **THEN** text/name/portrait transition synchronously to actor and then to no speaker, with no host plate retained for narration

#### Scenario: Travel band replaces paging without losing prose
- **WHEN** wilderness exploration enters travel and ordinary room narration arrives
- **THEN** only typed events enter the travel band, the full log retains raw prose and leaving travel restores the existing message reader
