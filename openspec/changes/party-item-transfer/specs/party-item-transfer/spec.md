# Spec Delta

## Purpose

Move held items between the commander and present party members outside combat as one free, all-or-nothing reorganization, exposed to the WebClient through an exact action.

## ADDED Requirements

### Requirement: Transfers happen only outside combat
A member item transfer SHALL be rejected with `transfer_in_combat` while the acting character, the commander, the giver or the receiver is in an active combat session, before any other check, and SHALL write nothing.

#### Scenario: Transfer during combat is refused
- **WHEN** the commander, in an active combat session, asks to move a potion from 艾拉 to 卡恩
- **THEN** the request is rejected with `transfer_in_combat` and both bags are unchanged

### Requirement: Giver and receiver are distinct authorized members
The giver and the receiver SHALL each pass the member boundary for the organizing purpose (the commander or a present effective party member; a knocked-out member is admitted), and SHALL be different members; the same member on both sides SHALL be rejected with `transfer_same_member`.

#### Scenario: A knocked-out companion can receive
- **WHEN** the commander gives a potion to companion 卡恩 at stored HP 1 in the same room
- **THEN** the transfer succeeds

#### Scenario: An absent receiver is refused
- **WHEN** the receiver named is a companion in another room
- **THEN** the request is rejected with `member_not_present` and nothing changes

### Requirement: Equipped and locked items cannot be transferred
A transfer SHALL be rejected with `item_equipped` when the requested quantity can only be met by equipped copies, with `item_locked` when the item is guild property or either member is under an exam-kit restriction, and with `item_not_held` when the giver holds fewer copies.

#### Scenario: An equipped sword is refused
- **WHEN** 艾拉 holds exactly one sword and has it equipped, and the commander asks to give it to 卡恩
- **THEN** the request is rejected with `item_equipped` and the sword stays equipped in 艾拉's bag

#### Scenario: Guild property is refused
- **WHEN** the requested item is guild property
- **THEN** the request is rejected with `item_locked`

### Requirement: A transfer moves both bags atomically and costs nothing
A successful transfer SHALL remove the copies from the giver and add them to the receiver through the inventory planning boundary in one transaction, keeping contained objects and the key lists synchronized, advancing no world time and changing no affinity. Any failure SHALL restore both bags and their caches.

#### Scenario: Three potions move
- **WHEN** the commander moves three healing potions from her bag to 艾拉 and holds six
- **THEN** the commander holds three, 艾拉 holds three more, the tick is unchanged and 艾拉's affinity is unchanged

#### Scenario: Injected failure restores both bags
- **WHEN** the receiver's write raises after the giver's removal was applied
- **THEN** both members' key lists, contained objects and in-process caches equal their pre-transfer values

### Requirement: The party.transfer action carries exact member references
The production registry SHALL register `party.transfer` accepting exactly `{giver_id, receiver_id, item_key, quantity}`: positive safe-integer member ids, a bounded whitespace-free item key, and a quantity from 1 to 99. Any other field SHALL reject before the adapter runs. Success SHALL publish a full canonical snapshot.

#### Scenario: Extra fields are rejected
- **WHEN** a `party.transfer` payload also carries `slot`
- **THEN** exact payload validation rejects it and no rule runs

#### Scenario: A successful transfer republishes canonical state
- **WHEN** a valid transfer succeeds through the action
- **THEN** the result is a success with a fixed Traditional Chinese message naming the item, quantity and receiver, followed by a full canonical snapshot

### Requirement: Transfer rejections are stable and observable
Each transfer rejection SHALL return its stable code and fixed Traditional Chinese message, and each successful transfer SHALL emit one info event carrying the giver, receiver, item key and quantity in context.

#### Scenario: Rejection message is fixed
- **WHEN** a transfer is rejected with `transfer_in_combat`
- **THEN** the message is exactly 「戰鬥中無法交換物品。」
