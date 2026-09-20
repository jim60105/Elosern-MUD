## Context

The replan put a palace forecourt at the top of the pilgrim road, above the cathedral, as a deliberate political statement. Nothing is behind the door yet. Three other 治理與防衛 locations are likewise mapped and empty.

This change is where the settlement build first has to decide what to do about locations whose content is a story nobody has written.

## Goals / Non-Goals

**Goals.** Four rooms. The palace as the first host-less place. Explicit refusals of the two features these rooms invite.

**Non-Goals.** No access control, no bounty board, no throne-room event, no NPC royalty. 薇歐蕾特·阿爾托利亞 is a character-card figure with her own arc; placing a permanent copy of her in a throne room would pre-empt whatever story eventually uses her.

## Decisions

### The palace is host-less, and that is the content

A palace with a caretaker standing in it is worse than an empty one. The document says a noble district's value is 「劇情門檻」 — it is a stage. An attendant whose dialogue amounts to "the King is not seeing anyone" is filler that a later questline would have to write around.

Empty also makes the room honest about its state. A player who walks into a bare throne approach understands they have reached the edge of what is built; a player who talks to a guard with nothing to say thinks the content is there and they are missing it.

This is the first real use of `hostless-places`, and the reason that capability was worth its own change.

### No lock, deliberately

A gate is the obvious thing to build here and it is wrong at this stage. A lock on an empty room is not a mystery; it is a wall. Nothing is behind it, so nothing is being protected, and the only effect is to remove a room a player could otherwise explore.

The requirement is written as a prohibition with an instruction attached — when a story lands, it brings the gate *and* what is behind it in the same change. That keeps the door open for the feature while preventing the half of it that has no value.

### No bounty board, quoted rather than reasoned

The document rules this out at line 410 in as many words: 「不宜另開一套平行的懸賞系統」. The guardhouse is exactly where someone would add one, because a city watch posting bounties is a genre staple. The spec pins the refusal and points at the two existing routes — the guild board and `npc:` private commissions — so the answer to "the watch should offer work" is a commission, not a system.

The testable half is that the guardhouse host carries no quest-issuer component. It could not anyway — `quest_issuer` is person-bound and cannot anchor a place row — but asserting it documents the intent rather than relying on a constraint that exists for an unrelated reason.

### The drill yard hosts what already works

`practice` and `guild exam` work wherever the player is. The instructor's value is the same as the innkeeper's: his dialogue is where a player learns that `rest` plus `practice` is how proficiency is trained. No mechanism is added.

## Risks

**Four rooms with no content is a lot of empty capital.** Accepted and partly the point — the replan's premise is that a city needs places that are not shops. The drill yard and the two watch posts have dialogue that teaches real commands; the palace deliberately has nothing, and one such room is a feature while five would be a problem.

**The host-less palace exercises a capability nothing else uses yet.** If `hostless-places` has a defect, this is where it surfaces. The tasks assert the twice-run case explicitly, because "creates no NPC" and "creates no NPC on the second run either" are different bugs.
