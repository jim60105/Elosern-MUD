# Spec Delta

## MODIFIED Requirements

### Requirement: Service action completion updates canonical panels and preserves narrative

After an admitted service or inventory action settles, the server SHALL emit every returned message through the
ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before
sending the matching safe `ui_action_result`. Existing guild and quest actions SHALL retain their
established affected-panel sets; a settled `shop.buy` or `shop.sell` SHALL additionally republish the viewed member's
`party_inventory` beside `status`, `services` and `item_holdings`, and a read-only `exam_schedule` reply SHALL leave
mode and canonical state unchanged.

#### Scenario: Turn-in updates wallet and merit panels together
- **WHEN** a completed quest is turned in successfully
- **THEN** narrative carries the reward message and status/services reflect wallet, merit, claim, and quest-log state at one newer revision before unlock

#### Scenario: Item use updates HP and inventory atomically
- **WHEN** `inventory.use` succeeds for a consumable healing potion
- **THEN** narrative reports the safe result and one newer canonical commit shows HP, item count, mode, clock, and combat state from the same settlement

#### Scenario: Exam start hands off while retaining personal inventory
- **WHEN** `guild.exam_request` returns exam_started for the exact next rank
- **THEN** mode becomes combat, context actions become combat, guild and shop services disappear, and canonical personal inventory remains reachable from the combat affordance

#### Scenario: Mode change tears down exploration service state
- **WHEN** the browser adopts combat mode
- **THEN** exploration service menus discard local quantity, selection, confirmation, and speech state while the combat dock owns focus and can open a fresh combat inventory surface

#### Scenario: Rejected inventory action emits no fabricated prose
- **WHEN** deterministic item or equipment preflight rejects
- **THEN** only the stable safe rejection is emitted, canonical state remains unchanged, and refreshed inventory permits another legal choice

#### Scenario: Rejected purchase emits no fabricated prose
- **WHEN** deterministic economy rejects for insufficient funds
- **THEN** only the stable safe rejection is emitted, wallet and stock remain unchanged, and refreshed services permits another legal choice

#### Scenario: Schedule information does not enter combat
- **WHEN** guild.exam_request returns exam_schedule
- **THEN** exploration mode/services remain available, planned attendance renders and no combat panel/session is created

#### Scenario: Inventory actions publish a full snapshot
- **WHEN** `inventory.use` or `inventory.toggle_equip` settles
- **THEN** a full snapshot is published because the action may change inventory, contained mirrors, status,
  character equipment, clock-derived state, combat/context state, terminal mode, and art

#### Scenario: Combat retains services v3 personal data and its own affordance
- **WHEN** the actor enters combat
- **THEN** exploration service menus and their local forms are unloaded, services v5 retains personal
  player/inventory data, the combat UI owns a separate inventory affordance, and guild and shop actions remain
  absent in combat

#### Scenario: A trade republishes the viewed member's bag and purse
- **WHEN** `shop.buy` or `shop.sell` settles successfully while the recipient or seller is the viewed member
- **THEN** the same newer revision carries the refreshed `services` rows and wallet, the `item_holdings` answer and the viewed member's `party_inventory` with its new held count and party purse, so the party window's 背包 tab and header purse are never stale after a trade

#### Scenario: Prose never drives panel state
- **WHEN** any success or domain-rejection message is produced
- **THEN** it is emitted as text and never parsed by the browser to update panel state


### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost browser suite SHALL exercise, using keyboard controls at 1451x790 and 2560x1440, all
existing registration, quest, exam, shop, stale/duplicate, repeated-inventory, and reconnect journeys plus
item-use confirmation at both acceptance viewports, full-HP refusal, combat item use through the party
window's 背包 tab, and direct equipment toggle for a named member.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member opens the quest drawer from the guild clerk's navigate row and uses Tab and Enter to reach and activate an eligible board offer's accept control
- **THEN** exactly one expected quest action is submitted, refreshed quest state appears in the quest book without typed input, and no `dock-menu` or `dock-detail` element renders inside the drawer at any step

#### Scenario: Shop buy journey completes by keyboard in the frameless drawer
- **WHEN** a player opens the shop window from the merchant's navigate row, selects the first stock row, Tabs to the action bar's quantity entry, types a quantity above the row's advertised maximum and Tabs away, then replaces it with a quantity within bounds, Tabs to the 買給 control, and presses Enter
- **THEN** leaving the entry clamps the out-of-bounds value to the advertised maximum and sends nothing, exactly one `shop.buy` is sent only on the buy control's activation with the row's `item_key`, the corrected quantity and the recipient's `recipient_id`, the wallet decreases by exactly that quantity times the row's `buy_copper`, and no `dock-menu` or `dock-detail` element renders inside the shop window at any step

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
- **THEN** guild services are reached through the frameless quest drawer and the shop through the shop window,
  and neither renders a `dock-menu` or `dock-detail` element in any journey

#### Scenario: Journeys assert the dispatch and layout invariants
- **WHEN** any acceptance journey runs
- **THEN** it asserts the single dispatch entry, in-flight locking, mode gating, honest wallet rendering, and
  bounded drawer dimensions
