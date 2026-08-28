# webclient-contextual-hud — delta

## MODIFIED Requirements

### Requirement: Reference surfaces render in a right-anchored drawer with one modal contract
The client's reference surfaces SHALL render inside a drawer anchored to the right edge of the stage, spanning the stage from the top edge of the persistent command-line strip to the stage bottom, bounded to a width that never exceeds the viewport, drawn on the solid panel background with a left border so it reads as a surface laid over the stage rather than a region of it. The drawer SHALL enter and leave by a horizontal slide expressed through the shared motion tokens, over a blurred scrim that covers the whole stage. Its header, its scrolling body and its optional footer SHALL be one column, and the body SHALL be the drawer's only scrolling region. The head SHALL render the reference's display type scale: the title in the display face at the reference's 20px scale with slight tracking, and the subtitle as the small muted line beside it. A drawer MAY declare one leading head icon (a decorative, `aria-hidden` glyph rendered before its title); a drawer that declares none renders its title with no icon, unchanged. The drawer's close control SHALL carry an accessible name (e.g. an `aria-label`) but MAY be rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name, not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim, and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL register itself as an open surface so the stage recession this capability already requires applies without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a subtitle stating its owner's active and passive skill counts (`主動 {n} · 被動 {m}`, computed from that same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer SHALL always carry a footer stating the client's own cast-command syntax (`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB protocol carries, so its presence does not depend on any panel's availability.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the drawer slides in against the right edge, its top edge sits at the top of the persistent command-line strip and its bottom edge at the stage bottom, over a blurred scrim that covers the whole stage, its body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the display face at the reference's 20px scale with slight tracking and the subtitle renders as the small muted line beside it

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
- **THEN** its head carries a leading skill glyph and a `主動 {n} · 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once (not duplicated inside the body), and its footer states the client's `/cast` syntax as static copy
