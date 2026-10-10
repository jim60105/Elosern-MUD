## MODIFIED Requirements

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract

The action-dock family (`ActionDock`, `DockMenu`/`DockMenuItem`, `OptionCard`/`ChoiceCardRow`, `ExitCompass`,
`ExplorationReadout`, `SceneOverview`, `DockVerbPopover`) SHALL present the `context_actions` v5 menus and, in
exploration, the `exploration` panel's scene overview as an exit compass beside finite people/object/footer
rows or chips sharing one readout, with the mode's guidance line, focused/disabled states, and the exact
server-authored option and choice card shape.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render
- **THEN** each option and choice card is the exact server-authored shape and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: The scene overview renders only its non-empty rows
- **WHEN** the scene overview renders objects and the footer, with no people section, beside a compass with exits
- **THEN** only the 物件 row and footer render in that order, with no 人物 or 出口 row or label, and each chip carries its row key and row id

#### Scenario: A disabled exit chip explains itself without submitting
- **WHEN** a disabled compass target is aimed or clicked
- **THEN** the shared readout shows its unchanged server reason and no move intent is emitted

#### Scenario: The verb popover closes on an outside press
- **WHEN** the verb popover is open inside its host and the pointer presses inside the host but outside the popover card
- **THEN** the popover emits its back intent once and emits no activation

#### Scenario: The dock exposes its keys, target, and test ids
- **WHEN** the action dock renders
- **THEN** it exposes the preserved `action-` and `target-` item keys and the focusable
  action-dock target, and a stable `data-testid` on every interactive cell

#### Scenario: Every cell is panel-backed and emits only real intents
- **WHEN** any action-dock card, row, or chip activates
- **THEN** it is backed only by the `context_actions` or `exploration` panel and emits, on
  activation, the exact OOB action intent — the `action_id` and `payload` fields of the
  `ui_action` envelope (the transport-level fields are owned by the C1 store) — or the local
  frame-opening intent its row carries, so no action or target is invented

#### Scenario: Overview chips wrap inside the command panel
- **WHEN** a scene-overview row's chips exceed its width
- **THEN** they wrap onto further lines inside the command panel rather than overflow it
  horizontally

#### Scenario: An exit chip follows the move row form's rules
- **WHEN** the compass resolves and aims a committed move row
- **THEN** its target and readout obey `webclient-exit-compass`, including bearing, direction and portal resolution, destination fallback, and disabled reason presentation

#### Scenario: The verb popover names its target and its rows
- **WHEN** the verb popover renders for a target
- **THEN** it renders a head naming its target and that target's rows in the menu's order

#### Scenario: A disabled chip exposes its reason to assistive technology
- **WHEN** the scene overview renders a disabled chip
- **THEN** the chip stays focusable, carries its disabled marker in text, and exposes its
  server-authored reason to assistive technology and, while focused, in the overview's reason
  strip

