# Spec Delta

## MODIFIED Requirements

### Requirement: The action-dock family presents a finite, keyboard-and-pointer-actionable contract

The action-dock family (`ActionDock`, `DockMenu`/`DockMenuItem`, `ExitCompass`, `ExplorationReadout`,
`RestForm`) SHALL present the `context_actions` v7 menus and, in exploration, the exit compass beside
the 建議 pill sharing one readout, with the mode's guidance line, focused/disabled states, and the
exact server-authored suggestion card shape on the centred suggestions card.

#### Scenario: Focused and disabled cells are distinct
- **WHEN** the active menu frame renders a focused cell and a disabled cell
- **THEN** the focused cell is the dispatch target (its activation emits the action intent) and the disabled cell emits nothing, and each exposes its `action-` or `target-` key and a stable `data-testid`

#### Scenario: Option and choice cards match the server shape
- **WHEN** the `context_actions` suggestions render on the suggestions card
- **THEN** each card row is the exact server-authored shape (label and optional hint) and its activation emits the exact OOB action intent (the `ui_action` envelope's `action_id` + `payload`) with no invented value

#### Scenario: The scene overview renders only its non-empty rows
- **WHEN** the exploration root renders for a room with people, objects, and exits beside a compass
- **THEN** no chip row renders, with no 人物, 物件, 出口, or footer row or label: the people and objects stand on the presence rail and the room actions on the place card and the 建議 pill

#### Scenario: A disabled exit chip explains itself without submitting
- **WHEN** a disabled compass target is aimed or clicked
- **THEN** the shared readout shows its unchanged server reason and no move intent is emitted

#### Scenario: The verb popover closes on an outside press
- **WHEN** the centred choice card is open and the player presses Escape or activates its trailing `✕ 返回` row
- **THEN** the card emits its back intent once and emits no activation

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
- **WHEN** the command panel's right column holds the 建議 pill and the readout
- **THEN** both stay inside the command panel and neither overflows it horizontally

#### Scenario: An exit chip follows the move row form's rules
- **WHEN** the compass resolves and aims a committed move row
- **THEN** its target and readout obey `webclient-exit-compass`, including bearing, direction and portal resolution, destination fallback, and disabled reason presentation

#### Scenario: The verb popover names its target and its rows
- **WHEN** the choice card renders a target's verb rows
- **THEN** it renders that target's rows in the menu's order with digit badges, followed by the trailing `✕ 返回` row under a hairline rule

#### Scenario: A disabled chip exposes its reason to assistive technology
- **WHEN** a dock row or a card row is disabled
- **THEN** it stays focusable, carries its disabled marker, and exposes its reason to assistive
  technology; in the exploration screen a server-authored disabled reason appears in the shared
  readout

