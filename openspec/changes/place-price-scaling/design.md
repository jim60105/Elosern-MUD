## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §4.

The binding constraint is that money in this project is exact integer
copper, end to end. `world/rules/guild_config.py::_require_int` rejects a
float outright, and `shop-economy` states the invariant. Any price
adjustment must therefore be integer arithmetic with a rounding rule chosen
once and written down, not a float multiply rounded at the edges.

The second constraint is `PRICE_TABLE`: a band is a property of the item,
global across every shop. Whatever adjustment happens must land back inside
that band.

## Goals / Non-Goals

**Goals:**

- Express both "everything here costs more" and "this one thing costs a
  fortune here" without cloning goods lists.
- Keep the resolved `ShopConfig` shape unchanged so nothing downstream
  learns about scaling.
- Catch every pricing mistake at startup.

**Non-Goals:**

- Location-scoped price bands. A band stays global; if a desired price will
  not fit, the band is widened in a change that owns the item, not bypassed
  here.
- Dynamic pricing — supply, demand, reputation, haggling. The resolved price
  is static per place.
- Content. No settlement's scale or override is authored here beyond what
  the tests need; the two content changes author their own.

## Decisions

**Two layers, not three.** A per-assortment scale ("elven goods cost 9× in
my shop") was considered and rejected. It reads well for one case and then
compounds: with a settlement scale, a place scale and an assortment scale,
the resolved price depends on the order the three multiplications and their
roundings are applied, and there is no order a reader would reliably guess.
Collapsing to one multiplication plus absolute overrides makes the resolved
value obvious from two numbers. The case it loses — a whole bundle marked up
at one shop — is expressible as several overrides, and the lore document's
own framing of scarce foreign goods is per-item anyway.

**Overrides are absolute, not multiplicative.** If an override were itself
scaled, every authored override would need the reader to compute the
settlement scale to know the shelf price. Absolute means the authored number
is the number.

**Overrides are complete or rejected.** A partial override merged with the
assortment base would be the only place in this loader where two sources
silently combine. The existing contract rejects a shop whose offers and item
list disagree by a single entry; accepting a half-specified rule here would
contradict that stance. It also gives additions a well-defined supply route:
an addition has no base, and a complete override is exactly what it needs,
so one mechanism covers both jobs.

**Half-up rounding, `(base * scale + 50) // 100`.** Banker's rounding and
truncation were the alternatives. Truncation biases every scaled price
downward, which is invisible at par and systematic at scale. Banker's
rounding is unsurprising to a statistician and surprising to everyone
reading a price list. Half-up is the rule a person doing this on paper would
use, and integer arithmetic keeps it exact.

**Validate after scaling, not before.** Checking the base and trusting the
multiply would let a legal base scale out of its band. The check therefore
moves to the resolved value. A consequence worth stating: a base that is
legal at par can become illegal at a scale, and the error names the resolved
value so the author sees what actually broke.

**Scale bounded to 1..1000.** Zero would make goods free and is almost
certainly a typo for 100; negative is meaningless; an unbounded upper end
lets one digit slip turn a band violation into an overflow-shaped confusion.
A 10× ceiling covers the scarcity cases the lore describes, and the band
check catches anything beyond.

## Risks / Trade-offs

- **A scale that is legal for most of an assortment can be illegal for one
  item near its band ceiling**, so raising a settlement's scale can fail
  load for a reason unrelated to the item being priced. → Intended: the
  error names the item and the resolved value, which is the information
  needed to either override that item or lower the scale.
- **Rounding can invert buy and sell at extreme scales** when the two base
  values are adjacent. → An explicit rejection rather than a clamp; clamping
  would silently alter an authored price.
- **`commerce.yaml` is edited by this change and by both content changes.**
  → Different sections (`price_scales:` here, `assortments:` and `shops:`
  rows there). Landing this first means the content changes author against
  the final schema instead of migrating to it.
