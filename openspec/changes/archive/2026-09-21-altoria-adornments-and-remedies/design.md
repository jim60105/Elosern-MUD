## Context

The capital's goods were one thirty-five-key bundle because there was one shop. Three specialist shops have since taken the weapons, the armour and the food. What is left is a mixture: eleven things you wear, six things you drink, five tools and twelve raw materials, all still labelled 王都雜貨.

The source document has been carrying the promise since the split began — line 146 says flatly that jewellery and potions stay with the sundries **until the jeweller and the alchemist land**.

## Goals / Non-Goals

**Goals.** Two shops. A partition rule that survives the next item added to the capital. Prices that do not move when goods do.

**Non-Goals.** No new mechanism — both are `merchant` places on the existing path. No rebalancing: this change must not be an opportunity to adjust a price, because a price change hidden inside a large move is a price change nobody reviews.

## Decisions

### The adornments bundle is defined by a rule, not a list

The obvious implementation is "put these eleven keys in a bundle". The obvious failure follows a month later: someone adds a twelfth accessory to the capital, drops it in `general_sundries` because that is where new things go, and the split silently rots back toward one shop.

So the contract is a set equality — the adornments bundle **is** the capital's accessory-slot goods — and the test computes both sides. A new accessory in the wrong bundle fails; a non-accessory in the adornments bundle fails. The line is drawn by the item registry's own `equipment_slot`, which is data that already exists and that nobody can drift by accident.

This is why the bundle takes all eleven, including the ones that read oddly as jewellery. 儲物袋 and 滑翔斗篷 equip to the accessory slot, so they are the jeweller's. A rule that holds is worth more than a shelf that reads perfectly.

### The remedies bundle is not defined by its band

`capital_remedies` takes six of the seven `potion`-band goods and is **not** stated as "the potion band", because the seventh is 受洗聖水 and it belongs to the sanctuary. A band is a pricing constraint, not a shop's inventory, and conflating them would force the sanctuary's holy water into the alchemist's shop to satisfy a rule that never should have been written that way.

### 受洗聖水 stays put, on purpose

It could move here and be moved again by the sanctuary change. It will not. The union scenario — that the split never narrows what the capital sells — is checked per change, and moving an item out with nowhere to put it would break that check for as long as the two changes are apart. Each change leaves the capital's offering whole.

### Prices move verbatim

Seventeen offer rows relocate between YAML sections. Every field is copied unchanged, and a scenario pins it: an item's resolved offer before and after the move is identical. The alternative — retuning while reorganising — makes the diff unreviewable, because a reviewer cannot tell a deliberate rebalance from a transcription slip.

## Risks

**A transcription slip during the move.** Seventeen rows copied by hand is the kind of edit where one digit changes. The before-and-after offer comparison catches it, and it is the first test to write, not the last.

**The accessory rule may be wrong for a future good.** A capital good that equips to the accessory slot but has no business in a jeweller's — a quest token, say — would be forced into the bundle. Accepted: no such good exists today, and the rule failing loudly when one appears is better than the partition quietly dissolving. The fix then is to state the exception in the spec, not to abandon the rule.
