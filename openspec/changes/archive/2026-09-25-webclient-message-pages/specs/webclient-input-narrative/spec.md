## ADDED Requirements

### Requirement: The narrative log is segmented into responses at each player action
The browser SHALL derive a sequence of responses from the retained narrative log as a client-local
presentation view. The view SHALL never mutate the log, SHALL never reach the server, and SHALL never
change what the full-log surface presents. A response SHALL begin at each retained player input line
and at each response mark. A response mark SHALL be recorded at the moment a deliberate mutation is
dispatched (a request id is returned), whether or not that dispatch appends an echo line, so an
action the echo catalog declares silent still begins a new response. A dispatch that appends its echo
line SHALL begin exactly one response, not two. A blocked dispatch, or one whose send fails
synchronously, SHALL record no mark. A response SHALL collect every following server, system, and
error line until the next response begins. Lines retained before any response begins (connection
notices, the first output after login) SHALL form a leading response with no input line. A line
arriving after its action's response has begun and before the next one (a late asynchronous reply)
SHALL belong to the current response. The input line SHALL be the response's header, SHALL be
presented only in the full-log surface, and SHALL NOT be one of the response's pageable blocks. A
response mark with no retained line after it yet SHALL begin no response. Every retained line SHALL
carry a monotonically increasing ordinal that survives the retention trim, so that trimming the oldest
lines leaves the segmentation of the lines still retained unchanged. Response marks older than the
oldest retained line SHALL be discarded with the trim.

#### Scenario: A typed command begins a response
- **WHEN** the player sends `look` from the command line and two server lines follow
- **THEN** the latest response has the `look` input line as its header and exactly those two
  server lines as its blocks

#### Scenario: A silent action begins a response
- **WHEN** the player activates the dialogue exit row, `explore.dialogue_leave` dispatches with no
  echo line, and the server's farewell line follows
- **THEN** the farewell line is the first block of a new response that has no input line, and it
  is not appended to the previous response

#### Scenario: An echoing action begins exactly one response
- **WHEN** the player activates a dock move row, the `explore.move` echo line is appended at
  dispatch, and room text follows
- **THEN** exactly one new response begins, its header is the echo line, and no empty response
  sits between the previous response and it

#### Scenario: A late line joins the current response
- **WHEN** a response has begun for the player's latest action and a further server line arrives
  before any other action
- **THEN** that line is appended to the latest response's blocks

#### Scenario: Output before any action forms a leading response
- **WHEN** the log holds only lines retained since login with no input line and no response mark
- **THEN** exactly one response exists, with no header, holding every retained line as a block

#### Scenario: A blocked dispatch records no boundary
- **WHEN** a dock activation is refused because a mutation is in flight and a server line then
  arrives
- **THEN** no response mark is recorded and the line joins the current response

#### Scenario: Trimming keeps segmentation stable
- **WHEN** the log exceeds its retention bound and its oldest lines are trimmed
- **THEN** every response whose lines are all still retained has the same header and blocks as
  before the trim, and no response mark refers to a trimmed line

### Requirement: A response is cut into pages that fit a measured box and never mid-sentence
The browser SHALL cut a response's pageable blocks into pages through a pure, deterministic function
of the blocks and an injected fit test. The fit test SHALL report whether a candidate page's content
fits the message box. Each server, system, or error line SHALL be one block, in log order. A page
SHALL hold as many whole blocks as fit. A system or error block SHALL always begin a new page. When a
block does not fit the room left on the page, it SHALL be split at the last point that fits, trying
in this order:

1. a hard line break inside the block, or the end of a sentence. A sentence end is `。`, `！`, `？`,
   `…`, or ASCII `.`, `!`, `?` followed by whitespace, taken together with any directly following run
   of end marks and closing quotes or brackets (`」`, `』`, `）`, `"`, `'`).
2. a clause mark: `，`, `、`, `；`, `：`, or ASCII `,`, `;`, `:` followed by whitespace.
3. a character boundary, which SHALL NOT separate a surrogate pair.

When no split point of the block fits the room left on a non-empty page, the whole block SHALL move
to a new page first. A continuation SHALL NOT begin with the hard line break it was split at.

Paging SHALL run on the markup pipeline's token stream, never on rendered HTML. A split inside a
styled span SHALL close the span at the end of the earlier page and SHALL open a span with the same
classes and style at the start of the later page. Paging SHALL NOT emit any markup the pipeline did
not produce.

A box-drawing block SHALL never be split. A block that fits no empty page after every split point (a
box-drawing block taller than the box, or a box too small for one character) SHALL get a page of its
own marked oversize, which the view SHALL present with internal scrolling. No content SHALL ever be
truncated or dropped: concatenating a response's pages SHALL reproduce its blocks' text in order, less
only the line breaks consumed at split points.

For any character offset into a response, the function SHALL identify the page that contains it, so
that re-paging the same response for a changed box can place the reader on the page holding a given
character.

#### Scenario: Whole blocks are packed first
- **WHEN** a response has three short prose blocks that together fit the box
- **THEN** the response has exactly one page holding all three blocks unsplit

#### Scenario: A system or error block begins a new page
- **WHEN** a response holds one prose block followed by an error block, and both would fit together
- **THEN** the response has two pages, and the error block is the first block of the second page

#### Scenario: A long block splits at a sentence end
- **WHEN** a prose block of several sentences does not fit the room left, and a sentence end falls
  inside the part that fits
- **THEN** the earlier page ends at the last sentence end that fits, including any closing quote
  after it, and the later page starts with the next sentence

#### Scenario: A block without a fitting sentence end splits at a clause mark
- **WHEN** no sentence end or hard break falls inside the part of a block that fits, but a `，`
  does
- **THEN** the earlier page ends at the last clause mark that fits

#### Scenario: A block without any mark splits at a character
- **WHEN** neither a sentence end, a hard break, nor a clause mark falls inside the part that fits
- **THEN** the block is split at the last character that fits, and no surrogate pair is divided

#### Scenario: A split inside a styled span keeps its style
- **WHEN** a split point falls inside a span carrying a colour class
- **THEN** the earlier page's text ends inside a span with that class, the later page's text
  begins inside a new span with the same class and style, and no other markup is emitted

#### Scenario: A box-drawing block too tall for the box gets its own scrolling page
- **WHEN** a response holds a box-drawing map taller than the box
- **THEN** the map is not split, sits alone on a page marked oversize, and every row of it is
  present on that page

#### Scenario: Paging is lossless
- **WHEN** any response is paged for any box
- **THEN** the pages' text, concatenated in order, equals the blocks' text less only the line
  breaks consumed at split points

#### Scenario: A re-page finds the reader's character
- **WHEN** a response paged for one box is paged again for a narrower box
- **THEN** for any character offset, the function names the page of the new paging that holds
  that character
