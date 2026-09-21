## Context

These three finish the capital. Two of them are the locations the document says only a capital gets, and both are designated future homes for systems that do not exist — apprenticeship at the academy, escort commissions at the merchant hall. The third needs nobody in it at all.

## Goals / Non-Goals

**Goals.** Three rooms. An academy whose host is worth talking to. A second host-less place, this one justified by the document rather than by the room being unwritten.

**Non-Goals.** No apprenticeship, no escort quests, no stall merchants. The stalls are scenery with a roof.

## Decisions

### The academy's dialogue is its content

The other attendant hosts teach commands. The academy host has no command to teach — 「拜師」 is not a mechanism and the document says so. What he has is subject matter: the magic-rank ladder and the element system are both closed vocabularies that already exist in lore, and the document names the academy as their natural reveal site.

So the academy's dialogue is written as substance rather than orientation: ask about ranks, get the ladder; ask about elements, get the affinities. That makes it the one location in the capital where talking to someone is the point rather than the signpost, which is what an academy should be.

The spec pins that both topics answer, so a later rewrite cannot hollow it into flavour.

### Two refusals, for the same reason as the last change

The merchant hall is where escort commissions will live, and `guild request` already tells players escort work is closed. The temptation is to open it here. It cannot be opened here: escort work is a quest type, and a commission surface without a quest type behind it offers work that cannot be completed.

The academy is the same shape. An apprenticeship command that grants a skill would bypass the lineage tree's proficiency model entirely — not an addition but a second, contradictory acquisition path.

Both refusals are written as requirements rather than scope notes, matching how the crown-and-watch change handles the bounty board, because these are the three places in the capital where a well-meaning future change would add a system sideways.

### The stalls are host-less on the document's authority

The palace is host-less because its story is unwritten. The stalls are host-less because the document says a market street should be: 「市場街本身不需要一位固定的『街長』型功能性 NPC，遊戲性功能都掛在各個攤販身上」. That is a design statement about what a market is, not a placeholder.

The distinction matters for what happens later. The palace's emptiness is expected to end. The stalls' is not — when stallholders arrive they will be transient scene NPCs on the quest path, not a permanent roster host.

## Risks

**The academy's dialogue duplicates lore that lives in the codex.** If the rank ladder changes, two places say it. Accepted for now: the dialogue table is authored prose like every other host's, and wiring dialogue to read the lore registries is a larger change than this one. Noted so that a future lore edit knows to check here.

**Three exteriors now carry multiple doors each.** 市場街 carries the general store, the jeweller and the stalls; 東市 carries the alchemist and the merchant hall. The doorway-collision check added by the replan is what keeps these honest, and this change is its heaviest user.
