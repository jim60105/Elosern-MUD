## Context

The village ships four dwellings covering weapons, attire, food and sundries. The matrix marks two more 「變」 — adornments and remedies — and the document describes both villagers by name of interest: one who loves making ornaments, one who studies herbs and blending.

The map cannot hold them. Six nodes: an entrance, a plaza, and four dwelling approaches, all occupied.

## The map, and why it grows this way

```
+ 0 1 2 3

3   #-#          (1,3) 長老古樹下   (2,3) 銀葉坡
    |
2   #-#          (1,2) 村北古樹下   (2,2) 織房坡
    |
1 #-#-#-#        (0,1) 隱密小徑 (1,1) 村中廣場 (2,1) 練刀場 (3,1) 藥草園
    |
0   #-#          (1,0) 溪畔小徑   (2,0) 溪畔下游

+ 0 1 2 3
```

Ten nodes, nine links, still a tree. Verified against `XYMap.parse()`. The six original coordinates are untouched, so none of the four landed homes moves.

Each addition extends something already there rather than opening new ground: 銀葉坡 is further up the weaving slope, 藥草園 is past the training ground where cleared sun reaches, 長老古樹下 is deeper into the north grove, 溪畔下游 is further along the stream. That is how a village of a hundred people grows — along its existing paths.

## Goals / Non-Goals

**Goals.** Four nodes. Two trading homes. An explicit statement of the two-price rule the village embodies.

**Non-Goals.** No new mechanism. No shops — these are homes. No inn: the matrix marks 旅店 「變」 for elven villages but the document's own section says outsiders almost never stay and that when they do it is 「重大劇情事件而非常態設施」, so a lodging place would contradict the text that the matrix cell points at.

## Decisions

### The tree rule is promoted from a comment to a requirement

`village_ciaran.py`'s docstring explains that the village is a tree on purpose: 「一個一百人的村落複製那種形狀會讀起來像小鎮」. That reasoning was a module comment, which is exactly the kind of thing the next person to add a node does not read.

Growing the map is the moment to move it into the spec, with a scenario that counts links against nodes. The rule is cheap to satisfy and easy to violate by accident — one convenience path between two dwellings and the village silently becomes a street grid.

### `crescent_earring` changes hands inside the village

月牙耳環 sits in 瓦爾溫's sundries today because the collector was the only villager trading. The document names it, with 三稜晶符, as the adornment-maker's work. So it moves — within one settlement, verbatim price, no behaviour change — and the sundries keep what a collector would actually have.

This is a move between two bundles of the same settlement, which is the case the per-shop overlap rule cares about: after the move exactly one village shop offers the key, and that must stay true.

### The two-price rule gets stated properly

The village already sells 精靈蛛絲 at 60 copper while the capital sells the same key at 60,000. That works, and it works through two assortments rather than any override — but nothing in the specs says it is *intended*. It reads as two independent prices that happen to differ.

The adornment-maker makes it a pattern rather than a coincidence, so this change writes the intent down: an elven-made good is everyday at home whatever it is worth abroad, the same key may carry two prices, and the two are the same item. The last clause is the one worth pinning — the player must not end up with a different object depending on where they shopped.

Rarity is called out as read-nowhere because 三稜晶符 and the other elven goods were deliberately given high rarity, and rarity is presentation-only. A price that tracked rarity would break the whole premise.

### No inn, and the matrix cell is not ignored

「旅店」 is 「變」 for elven villages, and this change declines to build one. That is a reading of the document, not an oversight: the 旅店 section says elven villages have no commercialised lodging and that an outsider staying over is a major story event. The design records the decision so the next person comparing the matrix to the implementation finds an answer rather than a gap.

## Risks

**Two new nodes land empty.** 長老古樹下 and 溪畔下游 are built here and filled by the commons change. If that change slips, the village has a dead-end path to an elder's tree with no elder. Acceptable — 溪畔下游 is scenery permanently, and a grove with a great tree is a reasonable place to walk to.

**Both new bundles touch `assortments.py` alongside the capital's shop changes.** `assortments.py` is edited by this change and by the capital's adornments and sanctum changes; the sections are disjoint but the file is not, so these must not be worked in parallel on that file. The commerce-balance collision this paragraph used to name is retired: `commerce-rulebook-slices` split the monolith into `rulebook/commerce/`, so this change edits the village slice (`ciaran.yaml`) and the capital changes edit theirs (`altoria.yaml`) — disjoint files, loadable and owned independently.
