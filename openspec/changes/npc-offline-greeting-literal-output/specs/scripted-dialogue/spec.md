## ADDED Requirements

### Requirement: Editable offline greeting text is literal at every speech output boundary
A non-empty per-instance offline greeting SHALL be plain text on all no-keyword and degraded speech surfaces: scripted and componentless text commands, browser conversation-open narrative/action messages, and degraded generative-NPC speech. Its literal tokens, including color, newline and MXP command/URL markers and repeated pipes, SHALL NOT create formatting, extra lines or interactive links. Escaping SHALL occur only for the text-output surface, exactly once; storage, private editor fields, dialogue-session/OOB lines and settled-line observer values SHALL retain the normalized raw text. An editable override SHALL remain literal even if its text equals an authored default. Clearing the override SHALL restore the trusted authored table/profile default with its existing formatting. Known keywords and misunderstanding replies SHALL remain authored-only.

#### Scenario: Markup-like override displays as literal speech
- **WHEN** an author saves a valid greeting containing `|/`, `|r`, repeated pipes, an MXP command link and an MXP URL link, then uses each no-keyword or degraded speech surface
- **THEN** the displayed override contains those literal tokens with no token-induced linebreak, color or actionable link and all raw storage/session/editor values remain unchanged

#### Scenario: A degraded reply retains raw observer state
- **WHEN** generative dialogue degrades for an NPC with an editable markup-like greeting and its existing completion gates pass
- **THEN** speech is literal, the settled dialogue observer receives raw text, and persona/version, affinity and intents are unaffected by escaping

#### Scenario: Matching default text does not grant formatting trust
- **WHEN** an editable greeting equals a trusted default containing a color token
- **THEN** the override displays that token literally, but clearing the field restores the authored default's normal color behavior

#### Scenario: Browser republishing does not double escape
- **WHEN** conversation-open stores a markup-like override and the dialogue panel is refreshed or restored after reconnect
- **THEN** the raw OOB line displays as literal text without adding extra escape characters or interactive markup
