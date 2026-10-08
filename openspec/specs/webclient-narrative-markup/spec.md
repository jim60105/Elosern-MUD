## Purpose

The strict allowlist pipeline that renders Evennia's converted ANSI-to-HTML narrative stream, the generated ANSI/xterm-256 palette with its contrast floor, and the upstream drift gate that keeps the pipeline honest.

## Requirements

### Requirement: The narrative renders the transport stream through a strict allowlist markup pipeline
The narrative surface receives markup rather than plain text, because Evennia's portal converts server output to HTML with `parse_html` before the `text` message is sent. The WebClient SHALL render that markup instead of displaying its source. The conversion SHALL be performed by a DOM-independent tokenizer module that accepts a source string and returns a bounded token list, and by a renderer that builds the nodes through the DOM constructors named below.

#### Scenario: Colored server output renders as styled text
- **WHEN** the server sends a `text` message whose `parse_html` output contains `<span class="color-014">南大道</span><br>` followed by escaped prose
- **THEN** the narrative shows `南大道` styled by the `color-014` class on its own line, the prose follows on the next line, and no markup source characters are visible

#### Scenario: The pipeline creates no node through an HTML-parsing API
- **WHEN** the shell's narrative modules are inspected
- **THEN** no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `createContextualFragment`, or `eval` appears on the narrative path, and every node is produced through an explicit element or text-node constructor

#### Scenario: The tokenizer runs without a DOM
- **WHEN** the tokenizer module is loaded and exercised under the Node test runner
- **THEN** the full grammar, its degradation rules, and its bounds are verified with no `document`, `window`, browser, or network access

#### Scenario: No HTML-parsing API and no added dependency
- **WHEN** the pipeline is examined
- **THEN** it uses no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `DOMParser`, `Range.createContextualFragment`, or `eval` at any point, and adds no third-party sanitizer or any other runtime dependency

#### Scenario: Nodes are built exclusively through the three DOM constructors
- **WHEN** the renderer constructs nodes for accepted markup
- **THEN** it does so exclusively with `document.createElement`, `document.createElementNS`, and `document.createTextNode`

#### Scenario: The accepted grammar is exactly the allowlist
- **WHEN** the tokenizer's accepted grammar is enumerated
- **THEN** it is exactly: literal text with entity decoding; the void element `<br>` in its `<br>`, `<br/>`, and `<br />` spellings; `<span>` and `</span>` whose `class` attribute is filtered to the exact allowlist `color-NNN`, `bgcolor-NNN` (three decimal digits), `underline`, and `blink`; an optional `style` attribute on a `span`; and `<a>`/`</a>`, handled by the anchor degradation rule
- **AND** no other element, attribute, entity, or value SHALL ever be constructed from the transport stream

#### Scenario: Entity decoding is limited to the named entities
- **WHEN** a literal-text run carries character references
- **THEN** decoding is limited to `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#x27;`, `&#39;`, and `&nbsp;`

#### Scenario: Span style attributes are restricted to hex colors
- **WHEN** a `span` carries a `style` attribute
- **THEN** it may contain only `color` and/or `background-color` declarations whose values are six-digit hexadecimal colors, applied through the element's style properties

#### Scenario: The tokenizer is DOM-free for the Node suite
- **WHEN** the tokenizer module runs
- **THEN** it accesses no `document` or `window` object, so the Node suite can exercise the complete grammar directly

### Requirement: Anything outside the allowlist degrades to visible literal text
The pipeline SHALL treat every input outside the accepted grammar as literal text rather than dropping it or interpreting it: the offending markup SHALL be rendered as the characters it is made of.

#### Scenario: Injected script markup is shown, never executed
- **WHEN** a `text` message reaches the client containing a literal `<script>` element, an `<img>` with an `onerror` attribute, or a `javascript:` URL that was not produced by the accepted grammar
- **THEN** those characters appear as readable literal text in the narrative, no element is created for them, no handler is attached, and no script executes

#### Scenario: A disallowed class or style value is dropped without dropping its text
- **WHEN** a span arrives carrying a class outside the allowlist or a `style` declaration outside the two permitted color properties
- **THEN** the span's text content still renders, the disallowed class or the entire disallowed `style` attribute is not applied, and no other attribute is created

#### Scenario: Oversized or pathologically nested input stays bounded
- **WHEN** a single message exceeds the token or nesting bound
- **THEN** parsing stops at the bound, the remainder renders as literal text, the browser stays responsive, and the narrative log continues to accept subsequent messages

#### Scenario: The degradation-triggering inputs
- **WHEN** the inputs that degrade to literal text are enumerated
- **THEN** they are: an unknown element, an unknown or disallowed attribute (including any `on*` handler attribute), a malformed or unterminated tag, an unbalanced closing tag, a class outside the class allowlist, a `style` declaration or value outside the color allowlist, nesting deeper than 32 levels, or a token count above 4096 in one message

#### Scenario: Degradation never discards or executes
- **WHEN** the pipeline degrades unrecognized input
- **THEN** it SHALL NOT silently discard content, SHALL NOT create an element from unrecognized markup, and SHALL NOT execute or attach any handler carried by the transport stream

### Requirement: Anchors degrade to their text content
The pipeline SHALL consume `<a>` and `</a>`, discard every attribute they carry, and render their inner content as ordinary narrative text. It SHALL NOT create an anchor element, SHALL NOT create any navigable or activatable control, and SHALL NOT reconstruct or send a command from an anchor's attributes.

#### Scenario: An MXP command link cannot send a command
- **WHEN** the stream contains an MXP command anchor whose `onclick` would call `Evennia.msg`
- **THEN** only the link's label text appears in the narrative, no clickable element exists for it, and clicking anywhere on that text sends no message

#### Scenario: A linked URL cannot navigate the client away
- **WHEN** the stream contains an auto-linked or MXP URL anchor
- **THEN** the URL renders as readable text, no anchor element is created, and no navigation or outbound request is possible from the narrative

#### Scenario: Anchors arrive in three upstream forms
- **WHEN** the anchor sources in the transport stream are enumerated
- **THEN** `parse_html` can emit MXP command links carrying an inline `onclick`, MXP URL links, and auto-linked bare URLs

#### Scenario: No transport content can act as a control
- **WHEN** any content in the transport stream is rendered
- **THEN** none of it is able to cause a navigation, an outbound request, or a client-to-server message

### Requirement: The narrative palette is generated with a contrast floor and honors reduced motion
The project SHALL ship a generated stylesheet defining `.color-000` through `.color-255` and `.bgcolor-000` through `.bgcolor-255` covering the 16 ANSI entries, the 6×6×6 color cube on the standard component levels `0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff`, and the 24-step grayscale ramp. Foreground entries SHALL use narrative tones rather than raw terminal colours. Every final foreground entry SHALL pass a deterministic contrast floor against the message band's ink reference `#141019`.

#### Scenario: Every emitted color class is legible on the ink background
- **WHEN** the generated palette is evaluated against the message band's ink background `#141019`
- **THEN** every `.color-NNN` rule meets at least a 3.0 contrast ratio, and no class that `parse_html` can emit is missing from the stylesheet

#### Scenario: Chromatic server colours read as narrative tones
- **WHEN** the server emits text in bright green, cyan, yellow, or red (`color-010`, `color-014`, `color-011`, `color-009`)
- **THEN** the text renders in the authored muted tone for that entry — bright yellow in the theme's gold accent — and not in the raw terminal colour

#### Scenario: No foreground entry is loud
- **WHEN** the generated palette's foreground entries are evaluated
- **THEN** every final entry's HSL saturation is at most 0.62, and every chromatic colour-cube entry keeps its source hue within 2° at the mapping stage before contrast flooring (which may shift hue)

#### Scenario: The committed palette cannot drift from its generator
- **WHEN** the repository palette test runs
- **THEN** regenerating the stylesheet reproduces the committed file byte-for-byte

#### Scenario: Reduced motion suppresses blinking output
- **WHEN** the browser reports `prefers-reduced-motion: reduce` and the server emits blinking text
- **THEN** the text is marked by a static non-animated indicator and no animation runs

#### Scenario: A stored reduced or off level suppresses blinking output
- **WHEN** the operating system does not request reduced motion, the stored motion level is `reduced` or `off`, and the server emits blinking text
- **THEN** the text is marked by the same static non-animated indicator and no animation runs

#### Scenario: Server map art within the pane width keeps its alignment
- **WHEN** a room description containing an ASCII or box-drawing map whose rows fit the narrative pane's content width is rendered
- **THEN** its rows align in columns and its leading indentation is preserved

#### Scenario: A row wider than the pane soft-wraps rather than clipping or scrolling the page
- **WHEN** a rendered row is wider than the narrative pane's content width
- **THEN** it soft-wraps inside the pane, the continuation is not required to stay column-aligned, no content is clipped, and the page itself does not scroll horizontally

#### Scenario: Chromatic ANSI entries take the authored ink-and-gold table
- **WHEN** the twelve chromatic ANSI entries (`001`–`006` and `009`–`014`) are generated
- **THEN** they take a fixed, authored table of muted tones that belongs to the client's ink-and-gold palette — the bright yellow entry SHALL equal the theme's gold accent `--gold-400`, and the bright red entry SHALL be a softened tone of its seal accent

#### Scenario: Achromatic entries and the grayscale ramp keep palette values before flooring
- **WHEN** the four achromatic ANSI entries and the grayscale ramp are mapped
- **THEN** they keep their palette values before contrast flooring

#### Scenario: Cube entries are saturation-capped at the mapping stage
- **WHEN** colour-cube entries are mapped, before contrast flooring
- **THEN** each entry's HSL saturation is capped at 0.62, chromatic cube hue remains within 2° of its source hue and lightness within 1/255, using inward integer rounding to keep saturation at most 0.62

#### Scenario: The contrast floor blends low-contrast entries toward paper
- **WHEN** the mapping stage finishes and the deterministic contrast floor runs against `#141019`
- **THEN** while an entry's WCAG contrast ratio against that background is below 3.0, it is blended 10% toward the theme's paper foreground, for at most 9 steps, and no final foreground entry exceeds an HSL saturation of 0.62
- **AND** contrast flooring MAY change hue and lightness

#### Scenario: Background entries use unmodified palette values
- **WHEN** the `.bgcolor-NNN` rules are generated
- **THEN** each uses the unmodified palette value

#### Scenario: A pure generator produces the stylesheet
- **WHEN** the stylesheet is produced
- **THEN** it comes from a pure generator, and a repository test regenerates it and compares it byte-for-byte with the committed file

#### Scenario: Blinking is neutralized under both motion signals
- **WHEN** the `blink` class is styled
- **THEN** it is neutralized to a non-animated indicator under `prefers-reduced-motion: reduce`, and also whenever the client's effective motion level is `reduced` or `off` (`webclient-contextual-hud` "The motion level is a client-local preference that governs every client animation")

#### Scenario: The narrative surface is monospace-first with preserved wrapping
- **WHEN** the narrative surface is styled
- **THEN** it uses a monospace-first font stack while preserving `white-space: pre-wrap`, so server-rendered ASCII and box-drawing map art keeps its column alignment and its leading indentation

### Requirement: The pipeline is verified against the real upstream converter
A repository test SHALL feed a fixture corpus through Evennia's real `parse_html` and then run the tokenizer over its output, asserting that no token is a literal-text fallback caused by an unrecognized element or attribute. If upstream begins emitting markup outside the allowlist, this test SHALL fail rather than the narrative silently regressing to displaying markup source.

#### Scenario: Upstream drift fails the gate instead of the player's screen
- **WHEN** the real `parse_html` produces an element or attribute the tokenizer does not accept
- **THEN** the contract test fails and identifies the unrecognized production

#### Scenario: Hostile player input survives the round trip as text
- **WHEN** player-authored input containing markup and event-handler syntax is passed through the real converter and then the tokenizer
- **THEN** the resulting tokens contain only literal text, no element token is produced from the player's characters, and the rendered output is readable text

#### Scenario: The corpus spans hostile input and the full color space
- **WHEN** the fixture corpus is enumerated
- **THEN** it includes hostile player-authored input (script elements, event-handler attributes, `javascript:` URLs, quote and entity sequences, unbalanced tags, and oversized input), every ANSI and xterm-256 foreground and background combination, truecolor output, blink, underline, tabs, and line breaks

### Requirement: The converted-stream assumption is bounded and enforced
The pipeline's safety argument rests on the transport stream having been converted and escaped by the portal, but the tokenizer cannot distinguish a converted string from an arbitrary one. That assumption SHALL therefore be bounded rather than asserted globally. The project SHALL NOT send narrative text with Evennia's `raw` or `client_raw` output options, and a repository test SHALL fail if any project code path sets either option.

#### Scenario: No project code path bypasses conversion
- **WHEN** the repository test inspects project code for narrative output options
- **THEN** no call site sets `raw` or `client_raw`, and the test fails if one is introduced

#### Scenario: Client-synthesized notices are inert
- **WHEN** the transport reports a closed connection or a reconnection attempt and the shell inserts its notice into the narrative
- **THEN** the notice renders as plain readable text and produces no element

#### Scenario: The raw options bypass conversion and escaping
- **WHEN** the banned output options are examined
- **THEN** Evennia's `raw` and `client_raw` options bypass conversion and escaping, which is why no narrative send may use them

#### Scenario: Unconverted notices are fixed markup-free strings
- **WHEN** the shell synthesizes a notice it inserts into the narrative without conversion
- **THEN** it is a fixed literal string containing no markup characters, so it tokenizes to a single text token

#### Scenario: Non-transport content is inserted as text
- **WHEN** content whose source is not the converted transport stream reaches the narrative
- **THEN** it is inserted as text
