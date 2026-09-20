## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §6.1 and
§6.3.

This change is content. Every mechanism it uses exists: place rows
(`settlement-place-registry`), assortments
(`commerce-assortment-registry`), and optionally scales and overrides
(`place-price-scaling`). The only judgement calls are which goods go where,
who keeps the shops, and where they stand.

## Goals / Non-Goals

**Goals:**

- Give the capital's specialist trades a location, a craftsman and a shelf.
- Leave the capital's purchasable set exactly as wide as it is today.

**Non-Goals:**

- Redesigning the capital map. The lore document calls for one
  (`docs/lore/settlement-locations.md:500`) and this is not it. Every
  exterior used here already exists.
- The remaining place types. 首飾店, 鍊金坊, 旅店, 公共浴場, 訓練場, 商會,
  魔法學院, 貴族區 and 市場街 stay unbuilt; their goods remain on the
  general store's shelf rather than being removed from the world.
- Price variation. The capital's three new shops sit at par with no
  overrides. The mechanism exists; this content does not need it.

## Decisions

**Narrow the general store rather than duplicate its goods.** The
alternative was to let the specialists and the general store both stock
weapons and armour, on the reasoning that a real general store carries a bit
of everything. Rejected for a concrete reason: the resolver rejects an item
offered by two of one place's assortments, and allowing the same key at two
*places* with different prices is the job of `place-price-scaling`'s
overrides, not of accidental overlap. Disjoint shelves also make the
regression precise — the union across all capital places must equal the
pre-split offered set — which is the one property that matters to a player.

**Three exteriors chosen from what exists.** 鐵匠鋪外 (0,2) is named for a
forge and its description already mentions the anvil, so the forge belongs
there. 南大道 (2,1) is described as lined with shops and stalls, which fits
an eatery on a main street. 北大道 (2,3) is described as broad and stately,
which fits a tailor who also takes noble commissions — the lore document's
裁縫坊 runs both an ordinary armour line and a formal-wear line
(`docs/lore/settlement-locations.md:188`). Nothing here required inventing a
node.

**Named hosts rather than the lore document's placeholders.** The document
offers 霍布·熔爐 and 柯爾特·暖爐 as illustrations. They are replaced by names
rolled from the project's corpus and selected on etymology, and the document
is corrected to match. The alternative — keep the document's names — was
rejected because they were written as examples of a naming convention, not
as authored registry content, and the convention is better demonstrated by
names whose meaning actually fits the trade. The correction is part of this
change so the two never disagree.

**Sex is authored on all three.** Two of the three rolled hosts are male;
the tailor is female, which is also why she was chosen from her shortlist —
the capital's existing two hosts plus two new male hosts would have made
every named shopkeeper in the game male by default rather than by decision.

## Risks / Trade-offs

- **The general store's shelf shrinks visibly.** A player who knew where to
  buy a sword now finds it elsewhere. → Intended, and the point of the
  change; the sword is still in the same city, two rooms away.
- **Correcting the lore document's two names touches a file this change
  otherwise has no business in.** → Leaving them would ship a document that
  contradicts the registry on a checkable fact. The edit is two lines.
- **Conflicts with `ciaran-village-commerce` on `commerce.yaml`.** → Both
  append shop rows; the sections are disjoint and the resolution is
  mechanical. Places do not collide at all, since each settlement has its
  own module.
