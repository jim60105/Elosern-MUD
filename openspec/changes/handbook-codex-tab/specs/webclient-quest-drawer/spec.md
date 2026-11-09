## MODIFIED Requirements

### Requirement: The quest drawer is a two-level icon-tabbed surface

The quest drawer (the handbook window) SHALL present a first-level icon tablist in its header: the quest book, guild counter, codex and titles tabs outside combat, and the codex and titles tabs alone in combat. A tab with sub-views SHALL add a vertical second-level tablist on its left edge. Every tab SHALL carry a text accessible name shown as a tooltip and SHALL be keyboard operable. The guild counter tab SHALL be disabled, yet focusable with its reason, while no usable guild section exists.

#### Scenario: The quest book is the first landing tab
- **WHEN** the player opens the quest drawer outside combat for the first time in a session
- **THEN** the quest book tab is selected

#### Scenario: The first-level tabs follow the mode
- **WHEN** the drawer renders outside combat, and separately in combat
- **THEN** outside combat the first-level tablist carries exactly the book, counter, codex and titles tabs in that order, and in combat it carries exactly the codex and titles tabs in that order

#### Scenario: A remembered book or counter tab yields in combat
- **WHEN** the remembered first-level tab is the quest book or the guild counter and the drawer opens in combat
- **THEN** the codex tab, the first combat tab, is selected and the remembered key is not overwritten

#### Scenario: The drawer remembers the last first-level tab
- **WHEN** the player selects the guild counter tab, closes the drawer, and reopens it in front of the same clerk
- **THEN** the guild counter tab is selected

#### Scenario: A remembered counter tab falls back when the counter is gone
- **WHEN** the remembered tab is the guild counter and the drawer reopens with no usable guild section
- **THEN** the quest book tab is selected and the guild counter tab is disabled

#### Scenario: The disabled counter tab explains itself
- **WHEN** the guild counter tab is disabled because the services panel is unavailable
- **THEN** keyboard focus can reach it, its tooltip and accessible description carry the panel's reason message, and activating it changes nothing

#### Scenario: The disabled counter tab names the missing clerk
- **WHEN** the guild counter tab is disabled because no guild section resolves while the services panel is available
- **THEN** its reason states that the counter needs a guild clerk

#### Scenario: Icon tabs are operable by keyboard
- **WHEN** focus is on a tab and the player presses an arrow key along the tablist's orientation, then Enter
- **THEN** focus moves to the adjacent tab and Enter selects it, and moving focus alone does not change the selection

#### Scenario: Opening in combat reads no counter services
- **WHEN** the drawer opens while the committed mode is combat
- **THEN** no guild counter services read is dispatched
