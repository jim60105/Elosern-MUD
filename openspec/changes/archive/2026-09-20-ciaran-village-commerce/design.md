## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §6.2 and
§6.3.

This change writes data. Every mechanism it needs is delivered by its five
dependencies, and the value of the change is precisely that: if furnishing a
settlement whose culture rejects commerce requires any new mechanism, the
place abstraction is wrong and this change is where that shows.

## Goals / Non-Goals

**Goals:**

- Meet the lore document's playability floor for elven villages.
- Demonstrate that the de-commercialised narrative costs no code.
- Demonstrate one item at two prices across two settlements.

**Non-Goals:**

- The other two elven villages. `docs/lore/settlement-locations.md:490`
  warns against a shared 「精靈村」 template; 翠綠森林村 and 幽月谷村 get
  their own designs.
- A jeweller and a temple-equivalent. Four hosts cover the four assortments;
  a fifth for jewellery alone would be a home with one shelf, so the
  collector carries it.
- Race-gated access to the village. Inherited as an open question from
  `ciaran-village-map`.
- Any elven quest, dialogue or event content.

## Decisions

**Four hosts, mapping one-to-one onto four assortments.** The lore document
names the pattern — 「喜歡製武具的負責全村的武器需求，愛鑽研服飾的負責防具與傳統服飾，
蒐集癖負責雜貨，料理愛好者負責食物」 — and it happens to be exactly one
assortment each. Jewellery has no fourth enthusiast, so it goes to the
collector, whose stated trait is 「什麼都蒐集、什麼都多做一份」. Inventing a
fifth host for one category would contradict a settlement of a hundred
people.

**Room names use the given name alone.** 「維特希爾·威爾德布瑞亞爾的家」 is
sixteen characters before the possessive. Elven surnames in this project's
corpus are phonetic transliterations averaging five to eight characters, and
the corpus's own guidance warns about rendered length. A village also does
not refer to a neighbour's house by full name. The four given names were
checked for mutual distinctness at exactly this position — an earlier
shortlist paired 斯瑞內斯 with 拉瑞內斯, which would have produced two
near-identical room names.

**Names chosen on etymology, sexes authored female.** 斯塔爾法爾 (Starfall)
is meteoric iron, tying the smith to the branch's 暗影鋼; 妮特布倫
(Nightbloom) is the valley's darkness and its candied blossoms; 斯蒂爾瓦特爾
(Stillwater) is sediment — what flows in never flows out, which is the
collector's trait; 威爾德布瑞亞爾 (Wildbriar) twines like warp and weft, and
thorn and needle share a root. 海莉爾 means "healer's daughter" and has
nothing to do with smithing, which is deliberate: elves hold no fixed
trades, so a name that read as a job title would contradict the setting.

A roll produced 斯塔爾威維爾 (Starweaver), a sharper etymology for the
weaver, but it collided on the given name with the smith. The
星墜 → meteoric iron → 暗影鋼 link was judged the more valuable of the two.

**The capital imports one good, not an assortment — and it already does.**
`elven_spider_silk` is one of the 58 keys the general store offers today, at
60,000 copper (`guild_economy.yaml:261`), so
`commerce-assortment-registry` carries it into the capital's sundries
assortment unchanged. This change only adds it to the village collector's
assortment at an everyday price.

An earlier draft added it to the capital as a stocked addition with an
override, on the false assumption that the capital did not stock it. That
would have declared the same key through two routes on one shop — an
overlap the resolver is specified to reject — and would have needed an
exclusion to undo a shelf entry that should never have been removed. Two
shops, two assortments, one key is the correct shape and needs no new
mechanism at all, which is a stronger demonstration than the override
version would have been.

Referencing the village's assortment from the capital was never an option:
it would import the whole shelf, contradicting
`docs/lore/settlement-locations.md:178` — elven craft 「幾乎不會流入外界市場」.

**`elven_spider_silk` is the price-variation demonstration, not a blade.**
Its band is `material`, whose ceiling is open-ended, so a village price of a
few dozen copper and the capital's existing 60,000 are both legal — a ratio
of about a thousand. Blades sit in `masterwork_gear`, capped at 500,000, and
would demonstrate the same thing with less headroom. The silk also needs no
capital-side edit at all, so the whole demonstration is one line in one new
assortment.

**Elven blades are shelvable; the branch's named masterworks are not.**
`masterwork-gear-price-band` moves the elven craft rows out of `relic` so
they can be sold at an everyday village price. The nine genuine keepsakes
stay where they are, and the lore document's account of a masterwork
reaching the outside world 「只能寫成某位精靈罕見地割愛的一次性事件」 remains a
narrative event, not a shop transaction.

## Risks / Trade-offs

- **The "no special case" guarantee is asserted, not enforced by
  construction.** A later change could add an archetype branch to the trade
  path and nothing structural would stop it. → The scenario that inspects
  the trade path for an archetype branch is the guard; it is a behavioural
  assertion and it is the best available.
- **Conflicts with `altoria-trading-places`** on `commerce.yaml` only, as
  disjoint appended rows. → `places_altoria.py` is no longer touched by this
  change, so the two content changes no longer share a place module.
- **Four hosts in a hundred-person village is a high proportion.** → The
  lore's framing is that these are interests rather than occupations, so
  they are four villagers who happen to make things, not four tradespeople.
- **Neither the price scale nor the override mechanism is exercised by this
  content.** Both are specified and unit-tested by `place-price-scaling`
  against synthetic places; nothing here needs them. → Deliberate:
  elven goods are cheap at home because they are locally produced, which the
  assortment base already expresses; adding a scale on top would price the
  same fact twice.
