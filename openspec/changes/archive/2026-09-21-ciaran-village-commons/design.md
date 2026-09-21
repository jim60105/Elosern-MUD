## Context

The village's four dwellings all sell something, so every villager a player can meet is someone they can trade with. That is a narrower village than the document describes, and it quietly reintroduces the thing the elven-village design was meant to avoid: the place reads as a set of shops with a forest theme.

The document's own list of what an elven village needs is four items, and three of them are not shops.

## Goals / Non-Goals

**Goals.** A room where nothing is sold. A sword instructor on the training ground. An elder who is a person rather than an office.

**Non-Goals.** No trade, no council mechanics, no teaching command, no gating. No shrine or temple: the document says elven faith is not shown to outsiders and warns specifically against inventing 「一座『精靈神殿』」.

## Decisions

### The shelter is host-less because the culture says so

共食棚 could have a cook. It must not. The document says eating together is 「族人共食棚裡的日常環節」 and that 「族人之間不存在『點餐付錢』」 — a host standing in it would either sell food, which contradicts the text, or stand there selling nothing, which is a stranger sight than an empty shelter.

This is the third distinct justification for a host-less place, and the three are worth distinguishing: the capital's palace is empty because its story is unwritten, the market stalls because the document says a market has no fixed staff, and the shelter because a transaction there would contradict the culture. Only the first is expected to change.

### The instructor shares the blade-smith's doorstep

海莉爾 the blade-smith already lives off 練刀場. Putting 泰莉爾 there too is not crowding — it is what a training ground is. The person who forges the blades and the person who teaches them live on the same clearing, which says more about 基亞蘭 sword culture than a paragraph of description would.

### The elder answers, she does not administer

The obvious elder is a quest-giver or a gatekeeper. Both are wrong here. The document says elves handle important matters by council 「但很少有『重要事務』」 and calls the elder's place symbolic.

So her content is memory. Her dialogue answers about the branch, the forest and the village's past — the things a very long-lived person would have. She grants nothing, gates nothing, and asks for nothing, and the spec pins all three, because "the elder should give you a quest" is the first thing anyone will want to add.

Mechanically she could not issue commissions anyway — `quest_issuer` is person-bound and cannot anchor a place row. The requirement states the intent rather than leaning on that constraint, which exists for an unrelated reason.

### Sword instruction is `practice`

`rest` plus `practice <skill>` is how proficiency is trained, everywhere. The instructor's dialogue names it. No teaching command, no trainer-grants-skill path — the same refusal the capital's academy makes, for the same reason: a second acquisition path would contradict the lineage tree rather than extend it.

## Risks

**An elder who gives nothing may read as unfinished.** Accepted, and mitigated by making her dialogue genuinely substantial — a century of the village's history is content even without a reward attached. If she later becomes a quest source it should be through a written story, which is the same position the palace is in.

**Two dwellings on the training ground need distinct doorway names.** The collision check the capital replan adds covers it; this is its village-side user.
