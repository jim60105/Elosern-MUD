## Context

The capital replan laid out a lower city around three locations that do not exist: 客棧巷 (an inn lane), 浴場前 (a bathhouse frontage) and the tavern that a river town's inn lane always has. The attendant blueprint made hosting them possible. This change fills them.

They are the first places in the settlement build that sell nothing, so they are also the first test of whether the place registry can carry a location whose whole purpose is that someone is standing there.

## Goals / Non-Goals

**Goals.** Three rooms, three hosts, three dialogue tables. Discoverability: a player who walks into the inn should learn what the inn is for by talking to the innkeeper.

**Non-Goals.** No lodging fee, no drink effects, no bathing effects. All three are marked 〔提案〕 in the source document, meaning they need their own design pass before any number is invented.

## Decisions

### The restraint is a requirement, not a note

"Do not add lodging fees" reads like a scope note and is written into the spec instead. The reason is that this is the exact point where scope creep is most tempting and least visible: an inn without a bill feels unfinished, and the fix is one attribute and one number. The document anticipates this and says 「這是刻意的設計簡化」 — deliberate simplification, not an oversight.

A requirement that the command set and persisted attribute set are unchanged before and after makes the temptation fail a test rather than pass a review.

### Dialogue carries the affordance

`rest`, `sleep`, `practice` and `invite` all work anywhere. That is correct — tying them to a building would be the mechanism this change refuses to add — but it leaves the inn with no way to signal what it is for.

The signal is the innkeeper. This is the same job the guild staff's dialogue already does: its greeting lists the guild commands, and that is how a new player learns them. The innkeeper listing `rest` and `practice` follows a pattern that is already load-bearing, and the spec pins it so the dialogue cannot later be rewritten into pure flavour.

### The bathhouse is a contrast scene, not a system

The document's interest in the bathhouse is the ethics gap it exposes — humans and beastfolk treat nudity as private, elves have no concept of shame — and it calls that contrast 「敘事鉤子」, a hook left for story. The location is authored to make the contrast visible in its description and its keeper's lines, and that is the whole of its content.

## Risks

**Three rooms with nothing to do in them read as filler.** Mitigated by what the document already assigns them: the tavern is where `invite` is meant to happen and where private commissions come from, so it is a real destination the moment recruitable NPCs exist. The inn and bathhouse are weaker and are honest about it.

**Two places share 客棧巷.** Their doorway names must differ or they collide into one exit. The capital replan adds the check that catches this; this change is its first real user.
