## ADDED Requirements

### Requirement: The narrative renders the transport stream through a strict allowlist markup pipeline
Evennia's portal converts server output to HTML with `parse_html` before the `text` message is sent, so the narrative surface receives markup rather than plain text. The WebClient SHALL render that markup instead of displaying its source. The conversion SHALL be performed by a DOM-independent tokenizer module that accepts a source string and returns a bounded token list, and by a renderer that constructs the corresponding nodes exclusively with `document.createElement`, `document.createElementNS`, and `document.createTextNode`. The pipeline SHALL NOT use `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `Range.createContextualFragment`, or `eval` at any point, and SHALL NOT add a third-party sanitizer or any other runtime dependency. The tokenizer SHALL access no `document` or `window` object so the Node suite can exercise the complete grammar directly.

The accepted grammar SHALL be exactly: literal text with entity decoding limited to `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#x27;`, `&#39;`, and `&nbsp;`; the void element `<br>` in its `<br>`, `<br/>`, and `<br />` spellings; `<span>` and `</span>` where the `class` attribute is filtered to the exact allowlist `color-NNN`, `bgcolor-NNN` (three decimal digits), `underline`, and `blink`; an optional `style` attribute on a `span` containing only `color` and/or `background-color` declarations whose values are six-digit hexadecimal colors, applied through the element's style properties; and `<a>`/`</a>`, which SHALL be handled by the anchor degradation rule. No other element, attribute, entity, or value SHALL ever be constructed from the transport stream.

#### Scenario: Colored server output renders as styled text
- **WHEN** the server sends a `text` message whose `parse_html` output contains `<span class="color-014">南大道</span><br>` followed by escaped prose
- **THEN** the narrative shows `南大道` styled by the `color-014` class on its own line, the prose follows on the next line, and no markup source characters are visible

#### Scenario: The pipeline creates no node through an HTML-parsing API
- **WHEN** the shell's narrative modules are inspected
- **THEN** no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `createContextualFragment`, or `eval` appears on the narrative path, and every node is produced through an explicit element or text-node constructor

#### Scenario: The tokenizer runs without a DOM
- **WHEN** the tokenizer module is loaded and exercised under the Node test runner
- **THEN** the full grammar, its degradation rules, and its bounds are verified with no `document`, `window`, browser, or network access

### Requirement: Anything outside the allowlist degrades to visible literal text
The pipeline SHALL treat every input outside the accepted grammar as literal text rather than dropping it or interpreting it. An unknown element, an unknown or disallowed attribute (including any `on*` handler attribute), a malformed or unterminated tag, an unbalanced closing tag, a class outside the class allowlist, a `style` declaration or value outside the color allowlist, nesting deeper than 32 levels, or a token count above 4096 in one message SHALL cause the offending markup to be rendered as the characters it is made of. The pipeline SHALL NOT silently discard content, SHALL NOT create an element from unrecognized markup, and SHALL NOT execute or attach any handler carried by the transport stream.

#### Scenario: Injected script markup is shown, never executed
- **WHEN** a `text` message reaches the client containing a literal `<script>` element, an `<img>` with an `onerror` attribute, or a `javascript:` URL that was not produced by the accepted grammar
- **THEN** those characters appear as readable literal text in the narrative, no element is created for them, no handler is attached, and no script executes

#### Scenario: A disallowed class or style value is dropped without dropping its text
- **WHEN** a span arrives carrying a class outside the allowlist or a `style` declaration outside the two permitted color properties
- **THEN** the span's text content still renders, the disallowed class or the entire disallowed `style` attribute is not applied, and no other attribute is created

#### Scenario: Oversized or pathologically nested input stays bounded
- **WHEN** a single message exceeds the token or nesting bound
- **THEN** parsing stops at the bound, the remainder renders as literal text, the browser stays responsive, and the narrative log continues to accept subsequent messages

### Requirement: Anchors degrade to their text content
`parse_html` can emit MXP command links carrying an inline `onclick`, MXP URL links, and auto-linked bare URLs. The pipeline SHALL consume `<a>` and `</a>`, discard every attribute they carry, and render their inner content as ordinary narrative text. It SHALL NOT create an anchor element, SHALL NOT create any navigable or activatable control, and SHALL NOT reconstruct or send a command from an anchor's attributes. No content in the transport stream SHALL be able to cause a navigation, an outbound request, or a client-to-server message.

#### Scenario: An MXP command link cannot send a command
- **WHEN** the stream contains an MXP command anchor whose `onclick` would call `Evennia.msg`
- **THEN** only the link's label text appears in the narrative, no clickable element exists for it, and clicking anywhere on that text sends no message

#### Scenario: A linked URL cannot navigate the client away
- **WHEN** the stream contains an auto-linked or MXP URL anchor
- **THEN** the URL renders as readable text, no anchor element is created, and no navigation or outbound request is possible from the narrative

### Requirement: The narrative palette is generated with a contrast floor and honors reduced motion
The project SHALL ship a generated stylesheet defining `.color-000` through `.color-255` and `.bgcolor-000` through `.bgcolor-255` covering the 16 ANSI entries, the 6×6×6 color cube on the standard component levels `0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff`, and the 24-step grayscale ramp. Foreground entries SHALL pass a deterministic contrast floor against the theme's ink background: while an entry's WCAG contrast ratio against the page background is below 3.0, it SHALL be blended 10% toward the theme's paper foreground, for at most 9 steps. Background entries SHALL use the unmodified palette value. The stylesheet SHALL be produced by a pure generator, and a repository test SHALL regenerate it and compare it byte-for-byte with the committed file. The `blink` class SHALL be neutralized to a non-animated indicator under `prefers-reduced-motion: reduce`. The narrative surface SHALL use a monospace-first font stack while preserving `white-space: pre-wrap`, so server-rendered ASCII and box-drawing map art keeps its column alignment and its leading indentation.

#### Scenario: Every emitted color class is legible on the ink background
- **WHEN** the generated palette is evaluated against the theme background
- **THEN** every `.color-NNN` rule meets at least a 3.0 contrast ratio, and no class that `parse_html` can emit is missing from the stylesheet

#### Scenario: The committed palette cannot drift from its generator
- **WHEN** the repository palette test runs
- **THEN** regenerating the stylesheet reproduces the committed file byte-for-byte

#### Scenario: Reduced motion suppresses blinking output
- **WHEN** the browser reports `prefers-reduced-motion: reduce` and the server emits blinking text
- **THEN** the text is marked by a static non-animated indicator and no animation runs

#### Scenario: Server map art within the pane width keeps its alignment
- **WHEN** a room description containing an ASCII or box-drawing map whose rows fit the narrative pane's content width is rendered
- **THEN** its rows align in columns and its leading indentation is preserved

#### Scenario: A row wider than the pane soft-wraps rather than clipping or scrolling the page
- **WHEN** a rendered row is wider than the narrative pane's content width
- **THEN** it soft-wraps inside the pane, the continuation is not required to stay column-aligned, no content is clipped, and the page itself does not scroll horizontally

### Requirement: The pipeline is verified against the real upstream converter
A repository test SHALL feed a fixture corpus through Evennia's real `parse_html` and then run the tokenizer over its output, asserting that no token is a literal-text fallback caused by an unrecognized element or attribute. The corpus SHALL include hostile player-authored input (including script elements, event-handler attributes, `javascript:` URLs, quote and entity sequences, unbalanced tags, and oversized input), every ANSI and xterm-256 foreground and background combination, truecolor output, blink, underline, tabs, and line breaks. If upstream begins emitting markup outside the allowlist, this test SHALL fail rather than the narrative silently regressing to displaying markup source.

#### Scenario: Upstream drift fails the gate instead of the player's screen
- **WHEN** the real `parse_html` produces an element or attribute the tokenizer does not accept
- **THEN** the contract test fails and identifies the unrecognized production

#### Scenario: Hostile player input survives the round trip as text
- **WHEN** player-authored input containing markup and event-handler syntax is passed through the real converter and then the tokenizer
- **THEN** the resulting tokens contain only literal text, no element token is produced from the player's characters, and the rendered output is readable text

### Requirement: The converted-stream assumption is bounded and enforced
The pipeline's safety argument rests on the transport stream having been converted and escaped by the portal, but the tokenizer cannot distinguish a converted string from an arbitrary one. That assumption SHALL therefore be bounded rather than asserted globally. The project SHALL NOT send narrative text with Evennia's `raw` or `client_raw` output options, which bypass conversion and escaping, and a repository test SHALL fail if any project code path sets either option. Client-synthesized notices that the shell or the stock plugins insert into the narrative without conversion SHALL be fixed literal strings containing no markup characters, so they tokenize to a single text token. Any content whose source is not the converted transport stream SHALL be inserted as text.

#### Scenario: No project code path bypasses conversion
- **WHEN** the repository test inspects project code for narrative output options
- **THEN** no call site sets `raw` or `client_raw`, and the test fails if one is introduced

#### Scenario: Client-synthesized notices are inert
- **WHEN** the transport reports a closed connection or a reconnection attempt and the stock handler inserts its notice into the narrative
- **THEN** the notice renders as plain readable text and produces no element
