# Spec Delta

## Purpose

The party window: one quest-drawer-styled window that presents the whole party through a member rail and first-level tabs, with the 成員 tab for bond, membership, persona and member actions.

## ADDED Requirements

### Requirement: The party window presents the whole party through one rail
The party window SHALL be built on `WindowFrame` with the first-level tabs 成員, 背包, 狀態, 技能, 系譜 in that order, the party purse in the header, and a `MemberRail` listing the `party` v3 rows (commander first) plus a 空位 entry while the general quota has room. Selecting a rail entry SHALL dispatch `party.view_member` with the current tab.

#### Scenario: Selecting a member dispatches the selection
- **WHEN** the player selects 艾拉 on the rail while the 狀態 tab is open
- **THEN** exactly one `party.view_member` with 艾拉's id and `tab: status` is sent and the tab stays 狀態

#### Scenario: Possession leaves the window identical
- **WHEN** the same party state is rendered while possessing 艾拉 and while not possessing
- **THEN** the rail, the tabs and every tab's content render identically, with no "you" marker

### Requirement: The window remembers its tab and member for the session
The selected member SHALL persist across tab changes, the window SHALL reopen on its last tab for the session, and when the server's `viewed_member_id` differs from the local selection (the member left or was deleted) the window SHALL adopt the server value and reset its local item selection and quantity.

#### Scenario: A departed member falls back to the commander
- **WHEN** the viewed companion leaves the party while the window is open on 背包
- **THEN** the rail selects the commander, the bag shows the commander's items, and no item stays selected

### Requirement: The member tab presents bond, membership, persona and actions
For a companion the 成員 tab SHALL show the bond stage with its pips, membership tags and intimate state, and an action bar with 請其離隊 (two-step confirmation like the quest drawer's abandon), 人物卡 (opens `NpcPersonaEditor`) and 附身 or 解除附身; for the commander it SHALL show the four persona fields, the intimate state and 編輯人物設定; for 空位 it SHALL show the invite target and its enabled or disabled descriptor from the existing `explore.party_invite` affordance.

#### Scenario: Leaving takes two steps
- **WHEN** the player activates 請其離隊 once
- **THEN** nothing is sent until the second confirming activation, and Escape cancels without sending

#### Scenario: The empty slot shows the invite descriptor
- **WHEN** 空位 is selected and the present innkeeper's invite affordance is disabled
- **THEN** the tab names the innkeeper and shows the committed disabled reason, and no invite is sent

### Requirement: Windows show state, never rule explanations
The party window SHALL render values, states and committed disabled reasons only, and SHALL NOT render explanatory rule text (follow rules, transfer rules, combat restrictions or legend prose).

#### Scenario: No rule prose in the member tab
- **WHEN** the 成員 tab renders a temporary escort member
- **THEN** it shows the commission tag and the leave descriptor's committed reason, and no prose explaining escort rules
