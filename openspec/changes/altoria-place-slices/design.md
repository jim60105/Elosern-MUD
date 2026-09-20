## Context

The capital replan leaves `places_altoria.py` holding five re-pointed rows and about to receive fourteen more, and it normalises shared exteriors without adding a guard for the way they can go wrong.

Both are cleanup the replan could have carried and deliberately did not: that change is the map and the three registries that index into it, which cannot land separately from each other without a broken startup. This one is everything about the capital's places that is not the map.

## Goals / Non-Goals

**Goals.** Three terrace slices. A guard on doorway collisions. No content change at all.

**Non-Goals.** No new place, no changed row, no changed exterior. If this change's diff contains a description or a coordinate, it has gone wrong.

## Decisions

### Terraces, not an arbitrary three-way split

The city is described as three terraces and a place's terrace is the first thing that locates it, so the slices are named for them. The alternative groupings — by kind, by whether the place trades — would cut across the map and leave a reader guessing which file a location is in.

It also gives the four content changes that follow a natural, mostly-disjoint assignment: hospitality writes lower, the sanctum writes upper, adornments writes middle. Mostly, not entirely — crown-and-watch spans lower and upper, learning-and-exchange spans middle and upper — so this reduces the contention rather than removing it.

### The collision check, and why it is not in the replan

The replan is where the hazard appears: the forge and the tailor share 工匠巷 from that point on. It hand-checks the one case, and the guard arrives here.

That ordering leaves a window where a collision is possible and unguarded, which is acceptable because exactly one shared exterior exists in it and that change's tasks name the check explicitly. The alternative — folding the guard into the replan — makes a change that is already over a day longer for a rule that is not about maps.

### The split reorders the derived roster

`places.py` documents that slice order is load-bearing: the derived roster and the derived shop registry both iterate the assembled dict, and `sync_service_content` processes rows in that order. Distributing five rows across three terraces changes their order relative to each other.

Nothing should depend on it — sync is idempotent and keyed by `service_id` — but "should" is why the tasks say to look for an order assertion rather than assume there is none.

## Risks

**A row is dropped or duplicated during the split.** Moving rows between files by hand is where one goes missing. The guard is asserting the assembled registry's keys and contents are identical before and after, which is cheap and exact.

**Contention is reduced, not eliminated.** Two of the four content changes still span two slices each, and all four still share `world/lore/dialogue/altoria.py`. This change does not pretend to fix that; the batch plan states which pairs remain serial.
