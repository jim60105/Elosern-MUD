## MODIFIED Requirements

### Requirement: Reference surfaces render in a bounded workspace drawer with one modal contract
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's
bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the
viewport bottom, so the workspace covers the stage, the bottom band, and the command-line row whether or
not that row is expanded, and only the band's lowest control strip stays exposed beneath it. A fine
border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage. The existing
modal drawer lifecycle and shared motion tokens SHALL be retained over a dimmed scrim covering the whole
viewport behind the drawer. Between its header and optional footer, a decorative art column MAY
accompany the scrolling content body; only the content body scrolls. The head SHALL be the shared
reference-surface header: the title in the serif heading face at the shared workspace scale with slight
tracking, and the subtitle as the small muted line beside it. Every reference drawer SHALL declare one
leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its
title). The drawer's close control SHALL carry an accessible name (e.g. an `aria-label`) but MAY be
rendered icon-only, with no visible text node; "labelled" in this requirement means an accessible name,
not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a
subtitle stating its owner's active and passive skill counts (`主動 {n} ‧ 被動 {m}`, computed from that
same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is
empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer
SHALL provide discoverable graphical skill-use and practice affordances under the
`webclient-skillbook-casting` contract, without requiring a cast-syntax footer or memorized skill/target
keys. The prescribed static `施放入口：cast <技法>[@威力]=<代號>` footer SHALL be removed. While the
declared-practice sub-screen replaces the book body, the head title SHALL read 修煉 and book-use
guidance SHALL be absent. Explicitly transferring from book use to dock-owned casting SHALL close
the modal book and transfer focus to that flow without leaving a drawer trap active; ordinary drawer
close paths SHALL retain their existing opener restoration.

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
- **WHEN** the skill-book drawer opens with the `character` panel available
- **THEN** its head carries a leading skill glyph and a `主動 {n} ‧ 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once, and graphical use/practice are discoverable without the old cast-syntax footer

#### Scenario: Book use transfers the modal focus owner
- **WHEN** the player deliberately activates book use and its authoritative flow is ready
- **THEN** the book closes, its scrim/trap retires, and focus moves to the sole dock-owned casting flow without a behind-drawer control becoming interactive

### Requirement: The skill book offers a bounded declared-practice sub-screen
The skill-book drawer SHALL offer a 修煉 affordance on each active skill row the committed
`character` panel supports, and activating it SHALL replace the book body with a practice
sub-screen inside the same drawer: the drawer title becomes 修煉, the body lists the panel's
active skills for selection, and one bounded-duration control starts the practice. The browser
SHALL compute nothing about eligibility, duration outcome, or progression: every row state comes
from the committed panel, the duration control reuses the waiting surface's bounded hours form, and
confirmation SHALL submit exactly one `explore.practice` with the selected `skill` and the
converted whole `seconds` through the shared dispatch/confirmation lock. While a submission is in
flight or its declared presentation revision is pending, the control SHALL be disabled. The
server-authored result line (success summary or rejection message) SHALL render as escaped text
inside the sub-screen and nowhere else, and closing the sub-screen SHALL restore the book body,
the original drawer title, and the book's graphical use/practice guidance without restoring the
removed cast-syntax footer. Casting SHALL NOT replace or bypass this practice workflow.

#### Scenario: Practice dispatches one server-trusted intent
- **WHEN** the player opens 修煉 from an active skill row, selects the skill, enters `2` hours, and confirms
- **THEN** exactly one `ui_action` is submitted, `explore.practice` with that `skill` and `seconds: 7200`, and the drawer controls stay locked until the result revision is adopted

#### Scenario: The result line is the server's
- **WHEN** a practice result arrives
- **THEN** its Traditional Chinese summary or rejection message renders verbatim as escaped text in the sub-screen, with no client-computed progression, elapsed-time, or eligibility claim

#### Scenario: The practice screen is gated by committed data only
- **WHEN** the `character` panel is unavailable or a row carries no practice support
- **THEN** no 修煉 affordance renders for that row and no practice state is invented

#### Scenario: Closing the practice screen restores the book
- **WHEN** the player closes the practice sub-screen
- **THEN** the drawer shows the skill book again with its original title and graphical use/practice guidance, no cast-syntax footer and no second drawer
