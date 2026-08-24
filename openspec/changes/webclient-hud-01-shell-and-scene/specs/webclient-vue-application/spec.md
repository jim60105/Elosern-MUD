## MODIFIED Requirements

### Requirement: The design system carries over from the design draft and stays offline
The Vue application SHALL render with the approved design system derived from the 設計稿
(`docs/design/elosern-redesign/`), and that draft SHALL be the binding reference for **both** the visual
system and the application's layout and information architecture — its palette, typefaces, and tokens,
and equally its stage composition, surface anchoring, and mode-gated visibility model. The application
SHALL render with the ink-night palette and its single seal-red accent, the self-hosted display, serif,
and sans typefaces, and the focus, selection, and motion tokens. Status and health information SHALL
never be conveyed by color alone (an icon or symbol plus a numeric value or an explicit text label is
required), SHALL honor `prefers-reduced-motion`, and SHALL remain legible for common color-vision
differences. No design asset or font SHALL be fetched from a remote origin at render time. Where this
capability and the draft are silent on a visual or navigational detail, the draft governs; a surface in
the draft that has no backing OOB read model SHALL NOT be built and SHALL NOT be mocked.

#### Scenario: Self-hosted fonts load offline
- **WHEN** the application loads with remote requests blocked
- **THEN** the display, serif, and body fonts render from the project origin

#### Scenario: Status is not color-only
- **WHEN** a gauge, condition, or health state is displayed
- **THEN** it pairs an icon or symbol with a numeric value or an explicit text label instead of relying on color alone

#### Scenario: Reduced motion is honored
- **WHEN** `prefers-reduced-motion` is set
- **THEN** non-essential animation transitions are disabled

#### Scenario: The draft is the binding layout reference
- **WHEN** the application composes its surfaces
- **THEN** it renders the draft's stage composition and mode-gated visibility model, not a fixed multi-column dashboard

#### Scenario: An unbacked draft surface is absent rather than mocked
- **WHEN** the draft shows a surface with no backing OOB read model
- **THEN** the application renders no such surface and presents no placeholder standing in for its data
