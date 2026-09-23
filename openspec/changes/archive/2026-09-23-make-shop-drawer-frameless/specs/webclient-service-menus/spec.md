## MODIFIED Requirements

### Requirement: Reconnect rebuilds services without replaying intent
WebSocket loss SHALL preserve the last rendered services view under the foundation offline overlay and lock every service mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild host, player summary, guild, shop, and inventory sections from canonical persistence even when its revision is lower than the retired epoch. The browser SHALL discard old-epoch packets, SHALL NOT restore an unsubmitted quantity or selection as authority, and SHALL NOT resubmit an uncertain prior mutation. An action submitted but unconfirmed before transport loss SHALL be treated as unconfirmed with the approved notice, never retried.

#### Scenario: Reconnect restores a shop view
- **WHEN** the transport disconnects while the shop drawer holds a typed but unsubmitted quantity and reconnects without another game action
- **THEN** the shop drawer closes on the transport loss, the unsubmitted quantity is discarded, the new snapshot renders the current stock, wallet, and inventory the next time the shop drawer opens, with every quantity entry back at its row action's own lower bound, and no automatic replacement purchase is sent

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending `guild.quest_turnin` but before its result is observed
- **THEN** reconnect synchronizes canonical quest, wallet, merit, and claims state, shows the uncertain-result notice, and sends no automatic replacement turn-in

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost browser suite SHALL exercise, using keyboard controls at 1440x900 and 1280x720, all existing registration, quest, exam, shop, stale/duplicate, repeated-inventory, and reconnect journeys plus item-use confirmation at both viewports, full-HP refusal, combat item use through the frameless combat bag drawer, and direct equipment toggle. Singleton replacement and the five-accessory cap with its sixth-accessory warning SHALL be established by deterministic rule and action-adapter tests and rendered in the component showcase, because the shipped item registry publishes no accessory items and no second singleton weapon for a live browser journey to hold. Exploration guild service submenus SHALL retain their existing roots and drawer-hosted shared row renderer. The shop SHALL be reached through its frameless client-local drawer, and its journeys SHALL be driven by keyboard through that drawer's own quantity entries and buy and sell controls. The bag SHALL retain its frameless client-local drawer model in exploration and combat. Every pointer affordance SHALL emit the same server-authored action identifier and payload as keyboard activation through the same dispatch entry and gates. Tests SHALL use deterministic fixtures and make no remote, LLM, or image-generation request. No remote or ambiguous host control SHALL render, no inspect-only item SHALL gain an action, and no reference surface SHALL be present while its drawer is closed.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member uses arrows and Enter to reach and accept an eligible board offer
- **THEN** exactly one expected quest action is submitted and refreshed quest state appears without typed input

#### Scenario: Shop buy journey completes by keyboard in the frameless drawer
- **WHEN** a player opens the shop drawer from the merchant's navigate row, Tabs to the first stock row's quantity entry, types a quantity above the row's advertised maximum and Tabs away, then replaces it with a quantity within bounds, Tabs to the row's buy control, and presses Enter
- **THEN** leaving the entry clamps the out-of-bounds value to the advertised maximum and sends nothing, exactly one `shop.buy` is sent only on the buy control's activation with the row's `item_key` and the corrected quantity, the wallet decreases by exactly that quantity times the row's `buy_copper`, and no `dock-menu` or `dock-detail` element renders inside the shop drawer at any step

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses or points to active-quest abandon before confirmation
- **THEN** no mutation is sent, cancel or Escape returns without abandoning, and confirm is the only submit path

#### Scenario: Item use requires confirmation at both viewports
- **WHEN** an eligible potion tile is activated by keyboard at 1440x900 or 1280x720
- **THEN** the accessible confirmation remains fully operable, no request precedes confirm, and focus returns to the tile on cancel

#### Scenario: Equipment and cap behavior are enforced deterministically
- **WHEN** rule and adapter tests drive a singleton replacement and fill the accessory slots to the cap
- **THEN** singleton replacement dispatches once, five accessories can be equipped, a sixth refuses with the committed warning without dispatch, and the showcase renders the capped state

#### Scenario: Minimum viewport retains service essentials
- **WHEN** shop or bag is open at 1280x720 with a disabled action focused
- **THEN** committed values, disabled reason, controls, and close path remain readable and operable without overlap

#### Scenario: No service surface is mounted while its drawer is closed
- **WHEN** every reference drawer is closed in exploration or combat
- **THEN** no shop, quest-board, lore, or inventory surface exists in the DOM or tab order and no fabricated row renders
