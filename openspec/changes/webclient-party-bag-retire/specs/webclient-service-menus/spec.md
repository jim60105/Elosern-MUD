# Spec Delta

## MODIFIED Requirements

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost browser suite SHALL exercise, using keyboard controls at 1451x790 and 2560x1440, all
existing registration, quest, exam, shop, stale/duplicate, repeated-inventory, and reconnect journeys plus
item-use confirmation at both acceptance viewports, full-HP refusal, combat item use through the party
window's 背包 tab, and direct equipment toggle for a named member.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member opens the quest drawer from the guild clerk's navigate row and uses Tab and Enter to reach and activate an eligible board offer's accept control
- **THEN** exactly one expected quest action is submitted, refreshed quest state appears in the quest book without typed input, and no `dock-menu` or `dock-detail` element renders inside the drawer at any step

#### Scenario: Shop buy journey completes by keyboard in the frameless drawer
- **WHEN** a player opens the shop drawer from the merchant's navigate row, Tabs to the first stock row's quantity entry, types a quantity above the row's advertised maximum and Tabs away, then replaces it with a quantity within bounds, Tabs to the row's buy control, and presses Enter
- **THEN** leaving the entry clamps the out-of-bounds value to the advertised maximum and sends nothing, exactly one `shop.buy` is sent only on the buy control's activation with the row's `item_key`, the corrected quantity and the recipient's `recipient_id`, the wallet decreases by exactly that quantity times the row's `buy_copper`, and no `dock-menu` or `dock-detail` element renders inside the shop drawer at any step

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses or points to active-quest abandon before confirmation
- **THEN** no mutation is sent, cancel or Escape returns without abandoning, and confirm is the only submit path

#### Scenario: Item use requires confirmation at both viewports
- **WHEN** an eligible potion row's 使用… is activated by keyboard in the party window's 背包 tab at 1451x790 or 2560x1440
- **THEN** the accessible confirmation remains fully operable, no request precedes confirm, and focus returns to the control on cancel

#### Scenario: Equipment and cap behavior are enforced deterministically
- **WHEN** rule and adapter tests drive a singleton replacement and fill the accessory slots to the cap
- **THEN** singleton replacement dispatches once, five accessories can be equipped, a sixth refuses with the committed warning without dispatch, and the showcase renders the capped state

#### Scenario: Minimum viewport retains service essentials
- **WHEN** shop, quest, or the party window's 背包 tab is open at the 1451x790 reference viewport with a disabled action focused
- **THEN** committed values, disabled reason, controls, and close path remain readable and operable without overlap

#### Scenario: No service surface is mounted while its drawer is closed
- **WHEN** every reference drawer is closed in exploration or combat
- **THEN** no shop, quest-board, lore, or party window surface exists in the DOM or tab order and no fabricated row renders

#### Scenario: Registry gaps move to rule tests and the showcase
- **WHEN** singleton replacement and the five-accessory cap with its sixth-accessory warning are validated
- **THEN** they are established by deterministic rule and action-adapter tests and rendered in the component
  showcase, because the shipped item registry publishes no accessory items and no second singleton weapon for a
  live browser journey to hold

#### Scenario: Services ride the frameless drawers only
- **WHEN** any acceptance journey opens guild services or the shop
- **THEN** guild services are reached through the frameless quest drawer and the shop through the frameless shop
  drawer, and neither drawer renders a `dock-menu` or `dock-detail` element in any journey

#### Scenario: Journeys assert the dispatch and layout invariants
- **WHEN** any acceptance journey runs
- **THEN** it asserts the single dispatch entry, in-flight locking, mode gating, honest wallet rendering, and
  bounded drawer dimensions
