## ADDED Requirements

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract
The action-dock components (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`,
`ChoicePointBlock`) SHALL present the `context_actions` v5 menus as a finite, framed grid with a guidance
line and focused/disabled states, and SHALL render the option and choice cards in the exact
server-authored shape. The action dock SHALL expose the preserved `action-` and `target-` item keys and the
focusable action-dock target, and SHALL expose a stable `data-testid` on every interactive cell. The
choice-point block SHALL show ready and generating states and remain movable. Every card and row SHALL be
backed only by the `context_actions` panel and SHALL emit the exact OOB action envelope; no action or
target SHALL be invented.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action envelope with no invented value

#### Scenario: Choice-point shows generating then ready
- **WHEN** a choice-point transitions from generating to ready
- **THEN** the block renders the generating state then the ready state and remains movable
