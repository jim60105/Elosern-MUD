## ADDED Requirements

### Requirement: CJK reading furniture follows the measured prose column
Prose SHALL have readable CJK line and paragraph spacing while preserving exact narrative content, the contracted reference font size, sentence-safe paging and map alignment. Page text SHALL use a line height of 1.5 times its font size and SHALL separate consecutive narrative lines by a gap of about half a line. Any CJK spacing treatment SHALL be presentation only (the rendered text content is unchanged) and SHALL NOT apply to box-drawing map lines, whose whitespace and alignment stay exact. Page measurement SHALL match displayed typography, so no page line is clipped at any viewport or prose scale. The page marker SHALL end at the prose column's right edge, or as close to it as the control strip's own controls allow, and SHALL stay inside the control strip. The dialogue name plate's underline SHALL start at the name's left edge. The message window's reading rule SHALL show only while the page surface holds keyboard focus. Decorative motion SHALL stop at the reduced and off motion levels.

#### Scenario: Resize preserves complete narrative
- **WHEN** mixed CJK and Latin prose is paged, then the viewport or reader scale changes
- **THEN** all content remains reachable without clipped lines, and the marker stays within the reserved strip at the prose edge, clear of the `日誌` control

#### Scenario: Maps preserve whitespace
- **WHEN** a response contains an ASCII map between prose blocks
- **THEN** the map retains its indentation and alignment while prose receives spacing treatment

#### Scenario: The marker follows the dialogue column
- **WHEN** a dialogue page is fully shown at 1920x1080
- **THEN** the marker's right edge lies within a few pixels of the left-aligned prose column's right edge, far from the band's right end

#### Scenario: Reduced motion keeps the marker still
- **WHEN** the motion level is reduced or off while a page marker is shown
- **THEN** the marker neither bobs nor fades

### Requirement: Pointer-open dialogue choices expose a local initial highlight
When an eligible dialogue choice list first opens through pointer interaction, it SHALL expose a non-activating initial highlight on its first enabled choice using the same active-descendant state as keyboard navigation. The highlight SHALL be visible even while the list does not hold focus; showing it SHALL NOT itself move focus (where focus goes when the list appears is unchanged) and SHALL NOT dispatch. When the list swaps to its exits, the first enabled exit SHALL be active; when no exit is enabled, the first exit SHALL stay active with its explanation reachable.

#### Scenario: Opening does not answer
- **WHEN** a pointer action leads to a fully-read response with enabled choices
- **THEN** the first enabled choice is highlighted and no choice dispatch occurs until deliberate activation

#### Scenario: A disabled first exit is skipped
- **WHEN** the player opens `↦ 移動…` and the first exit is disabled while a later one is enabled
- **THEN** the first enabled exit is active and nothing is dispatched
