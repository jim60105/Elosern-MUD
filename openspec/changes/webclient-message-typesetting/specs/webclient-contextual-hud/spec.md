## ADDED Requirements

### Requirement: CJK reading furniture follows the measured prose column
Prose SHALL have readable CJK line and paragraph spacing while preserving exact narrative content, the contracted reference font size, sentence-safe paging and map alignment. Page measurement SHALL match displayed typography. The page marker and name decoration SHALL align with the prose column, and decorative motion SHALL stop at reduced/off.

#### Scenario: Resize preserves complete narrative
- **WHEN** mixed CJK and Latin prose is paged, then the viewport or reader scale changes
- **THEN** all content remains reachable without clipped lines, and the marker stays within the reserved strip at the prose edge

#### Scenario: Maps preserve whitespace
- **WHEN** a response contains an ASCII map between prose blocks
- **THEN** the map retains its indentation and alignment while prose receives spacing treatment

### Requirement: Pointer-open dialogue choices expose a local initial highlight
When an eligible dialogue choice list first opens through pointer interaction, it SHALL expose a non-activating initial highlight on its first enabled choice using the same active-descendant state as keyboard navigation.

#### Scenario: Opening does not answer
- **WHEN** a pointer action leads to a fully-read response with enabled choices
- **THEN** the first enabled choice is highlighted and no choice dispatch occurs until deliberate activation
