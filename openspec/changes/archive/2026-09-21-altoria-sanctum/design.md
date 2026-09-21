## Context

Twelve `intimacy_tool` goods are fully defined in the item registry and none is purchasable. The capital is named for the Church of Light and has no church. The two facts have one answer.

The design difficulty here is not mechanical — it is two merchant-shaped places on an existing path. It is tonal, and the source document spends a whole paragraph on it because the obvious framing is the wrong one.

## Goals / Non-Goals

**Goals.** A temple. A shop that finally sells the intimacy goods. Authored text and structure that match how the world actually regards this building.

**Non-Goals.** No new trade mechanism, no content gating, no age or consent gate at the location level — those are character-level systems that already exist elsewhere and this is a shop. No re-pricing of the intimacy goods; their bands were set when they were written.

## Decisions

### Two places, one doorstep

The document says worship, ministry and shop are 「同一信仰生活的三個櫃檯」 in one building. Two place records sharing 大神殿前 models that: one square, two doors, two interiors. The alternative — one place with one host — would force a choice between a priest who sells and a shopkeeper who blesses, and would lose the document's point that these are distinct offices within one institution.

The capital replan already establishes shared exteriors and adds the doorway-collision check, so this is using a pattern rather than inventing one.

### The priest talks, the deacon sells

Both hosts can converse by the time this lands — `merchant-dialogue` gives every shopkeeper a dialogue table, so a single host carrying both trade and dialogue would be technically possible. The split is a choice about the institution, not a workaround for a missing capability.

The document describes two offices: a 主祭 who presides over worship, and a 聖所執事 whose remit is 「公開經營的性修道服務與附設商店的調度」. Those are different jobs held by different people, and collapsing them into one shopkeeper-priest would lose the point that the sanctum's ministry is an administered institution rather than a sideline.

The affinity model follows the split rather than driving it. The document's table at line 87 gives each location a primary channel — 「商店走 `trade`、公會走 `guild`、其餘多數走 `talk`」 — so worship accrues through conversation and the shop through trade, which is what two hosts with different capabilities produce naturally.

### 受洗聖水 moves here, and the timing is deliberate

Holy water is the sanctuary's good. The adornments-and-remedies change deliberately left it in the general store rather than moving it to a counter that did not exist yet, so the capital never stopped selling it. This change is the counter, so it moves now — verbatim, same price, same stock.

That ordering means this change must land after that one. If it landed first, the two changes would both try to own the key.

### Openness is a spec requirement, not a style note

The requirement that nothing about the sanctuary is gated, and that its authored text never frames the ministry as concealed, is written into the spec rather than left to the design document. The reason is that this is the mistake the source document predicts, and an authoring mistake that a reviewer has to notice by reading tone is a mistake that eventually ships. A test can check that no lock is consulted; a test can check that the shop lists on first request. Those catch the structural half of the error, which is the half that matters mechanically.

## Risks

**The tonal requirement is only partly testable.** No test can confirm prose has the right register. The structural scenarios pin what they can — no gate, no lock, no reveal — and the rest is on review against the document's own paragraph, which the tasks quote directly rather than paraphrasing.

**Thirteen offer rows, twelve of them new.** The intimacy goods have never been priced into a shop. Each must fall inside its item's existing band, which is checked at load; the task writes them against the band rather than picking round numbers and discovering the rejection later.
