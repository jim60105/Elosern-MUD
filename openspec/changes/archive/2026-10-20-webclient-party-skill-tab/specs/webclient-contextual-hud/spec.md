# Spec Delta

## MODIFIED Requirements

### Requirement: Reference surfaces render in a bounded workspace drawer with one modal contract
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the viewport bottom, so only the band's lowest control strip stays exposed beneath it. A fine border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage.

#### Scenario: The workspace covers the stage and keeps the modal lifecycle
- **WHEN** a reference drawer opens
- **THEN** the workspace covers the stage, the bottom band, and the command-line row whether or not that row is expanded, and the existing modal drawer lifecycle and shared motion tokens are retained over a dimmed scrim covering the whole viewport behind the drawer

#### Scenario: The workspace body and art column
- **WHEN** a reference drawer renders between its header and optional footer
- **THEN** a decorative art column MAY accompany the scrolling content body, and only the content body scrolls

#### Scenario: The shared reference-surface head
- **WHEN** a reference drawer renders its head
- **THEN** it is the shared reference-surface header: the title in the serif heading face at the shared workspace scale with slight tracking, and the subtitle as the small muted line beside it; every reference drawer declares one leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its title); and the drawer's close control carries an accessible name (e.g. an `aria-label`) but MAY be rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name, not necessarily visible text

#### Scenario: One drawer, focus-trapped and restorative
- **WHEN** a second drawer is opened while one is open, or the open drawer is closed by Escape, its labelled close control, or the scrim
- **THEN** at most one drawer is open at any time and opening a second closes the first; while open the drawer traps keyboard focus, so no surface behind it is reachable by sequential navigation; every close path restores focus to the control that opened it; and an open drawer registers itself as an open surface so the stage recession this capability already requires applies without a second mechanism

#### Scenario: The skill-book drawer states its counts honestly
- **WHEN** the party window's 技能 tab renders while the `character` panel is available, and when it is unavailable
- **THEN** the tab carries the viewed member's active and passive skill counts (`主動 {n} ‧ 被動 {m}`, computed from that same payload the tab renders); when the panel is unavailable the counts are empty, matching the degrade-without-inventing-data contract

#### Scenario: Skill use is graphical and practice retitles the head
- **WHEN** the party window's 技能 tab offers skill use and practice booking
- **THEN** its action bar provides discoverable 施放 and 排入修煉 under the `webclient-skillbook-casting` contract, without requiring a cast-syntax footer or memorized skill/target keys, the prescribed static `施放入口：cast <技法>[@威力]=<代號>` footer is removed, and booking opens no sub-screen and never retitles the window

#### Scenario: Book use hands the modal focus owner over
- **WHEN** the player explicitly transfers from book use to dock-owned casting
- **THEN** the modal book closes and focus transfers to that flow without leaving a drawer trap active, while ordinary drawer close paths retain their existing opener restoration

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the workspace is bounded below the navigation and above the band's lowest control strip, covering the command-line row, as an opaque panel over a dimmed scrim, its content body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the serif heading face with slight tracking and the subtitle renders as the small muted line beside it

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

#### Scenario: The close control is icon-only but keeps its accessible name
- **WHEN** a reference drawer's close control renders
- **THEN** it carries no visible text node, renders a decorative close glyph, and exposes the same accessible name (e.g. `aria-label="關閉"`) an assistive technology would have read from the previous visible text

#### Scenario: The skill-book drawer states its skill counts and cast syntax
- **WHEN** the party window opens on 技能 with the `character` panel available
- **THEN** the 技能 tab carries its skill glyph and a `主動 {n} ‧ 被動 {m}` count matching the panel's active/passive row counts, the window title renders exactly once, and graphical 施放/排入修煉 are discoverable without the old cast-syntax footer

#### Scenario: Book use transfers the modal focus owner
- **WHEN** the player deliberately activates book use and its authoritative flow is ready
- **THEN** the book closes, its scrim/trap retires, and focus moves to the sole dock-owned casting flow without a behind-drawer control becoming interactive

## REMOVED Requirements

### Requirement: The skill book offers a practice booking control
**Reason**: `SkillBook` is deleted; booking moves to the party window's 技能 tab action bar (排入修煉).
**Migration**: See `webclient-party-window` requirement "The skill tab casts and books for the viewed member".
