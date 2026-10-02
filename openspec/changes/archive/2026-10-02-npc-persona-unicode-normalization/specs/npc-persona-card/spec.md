## MODIFIED Requirements

### Requirement: Card text is normalized plain text
Every NPC card leaf SHALL first replace each CRLF pair with exactly one LF and every remaining CR with LF, then trim the maximal outer runs of exactly these boundary code points: U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000, U+FEFF. All interior text and all code points outside this finite set SHALL remain verbatim; no Unicode composition normalization or other line-separator conversion SHALL occur. Required emptiness and code-point/rendered budgets SHALL be evaluated after normalization. The same rule SHALL apply to editable offline greetings before the existing 300-code-point/no-LF/empty-allowed validation. Generic player persona normalization SHALL remain unaffected. Card text SHALL never be interpreted as markup, a template, a command, or an executable instruction; every output surface SHALL escape it for that surface.

#### Scenario: Line endings and outer whitespace normalize
- **WHEN** a leaf is submitted as `"  first\r\nsecond\r  "`
- **THEN** its normalized value is `"first\nsecond"`

#### Scenario: Template-like text is kept literally
- **WHEN** a leaf contains `{name}` or markup-like characters
- **THEN** the normalized value keeps those characters literally and no substitution occurs

#### Scenario: Previously divergent boundary characters agree
- **WHEN** a card leaf or greeting is submitted as `"\uFEFF\u0085text\u0085\uFEFF"`
- **THEN** its normalized value is `"text"` in both server and browser

#### Scenario: Interior and excluded characters remain literal
- **WHEN** a value includes interior U+0085/U+FEFF or boundary U+001C, U+180E, U+200B or U+2060
- **THEN** those characters are preserved and count toward the existing budgets

#### Scenario: Whitespace-only optional clears and required rejection agree
- **WHEN** hidden identity, social connection, greeting, or a required leaf contains only members of the explicit boundary set
- **THEN** optional values normalize to the empty string and clear, while required card leaves reject with their existing required-empty field reason

#### Scenario: Greeting newline validation follows normalization
- **WHEN** a greeting contains an interior CRLF or lone CR between words
- **THEN** it becomes an interior LF and rejects as greeting-invalid, whereas a trailing CRLF is trimmed and does not create a second paragraph
