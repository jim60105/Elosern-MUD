## Context

See `proposal.md` — Why, and
`docs/superpowers/specs/2026-09-20-settlement-shops-design.md` §6.2.

The machinery for a second settlement already exists and is already
registry-driven. `sync_grid()` loops `CITY_GATE_REGISTRY` and prunes any exit
back into 虛境 on every run; `sync_wilderness()` provisions one grid-side
gate per registered gate; `WILDERNESS_ENTRY_REGISTRY`'s validator already
checks global gate uniqueness and footprint containment. Every one of those
loops has only ever run over one row.

`world/lore/races.py:216` ships the `ciaran` subrace with
`native_anchor="village_ciaran"`, and `ANCHOR_REGISTRY` carries
`village_ciaran` with a population of 100. The lore for this settlement is
written; the geography is not.

## Goals / Non-Goals

**Goals:**

- A second settlement that is walkable, reachable and distinctly not a town.
- Give the existing multi-entry invariants a second entry to check.

**Non-Goals:**

- Commerce, hosts, interiors, items. The village ships empty;
  `ciaran-village-commerce` furnishes it.
- Restricting the entrance by race. Out of scope by the same reasoning
  `world/maps/city_gates.py:10` already records, and explicitly left open.
- The other two elven villages. `docs/lore/settlement-locations.md:490` is
  emphatic that the three branches should not share a template, so 翠綠森林村
  and 幽月谷村 are not derived from this one.

## Decisions

**A shared map assembly, because `XYMAP_DATA_LIST` has two independent
readers.** The name is defined in `world/maps/altoria_capital.py` and
imported separately by `world/maps/bootstrap.py:19` and by
`world/lore/wilderness_entry.py:180`'s `_iter_map_extents()`. The second one
is easy to miss and is the dangerous one: `validate_wilderness_entries()`
runs from `sync_all()` at every startup and rejects a gate whose `z_map_key`
names no map it can see, so a village gate added while that import still
points at the capital alone fails the whole lore load, not just the village.
Both readers move to one assembly. The lore side keeps its import deferred
inside the function — lore must not import `world.maps` at module scope.

**Six nodes in a tree, not a grid.** The capital is a thirteen-node cross; a
village of a hundred people copying that shape would read as a small town.
Six nodes give one entrance, one gathering place, and four dwelling
approaches — enough for the four homes `ciaran-village-commerce` attaches,
with nothing left over. The tree topology also means no ambiguous shortest
paths, matching the capital's existing property.

**The entrance takes a `CITY_GATE_REGISTRY` row despite not being a gate.**
The alternative was a separate registry for non-walled arrivals. Rejected as
duplication: the row's job is "the authored way in from 虛境", and nothing
about it presumes masonry. What the registry cannot express is the
*presentation*, so the fix is naming and description — 隱密小徑 — plus a
sentence in the requirement saying a row may describe a concealed path. This
keeps one loop in `sync_grid()` instead of two.

**The village is reachable from 虛境, accepting that every race sees it.**
This is the one decision with a real cost.
`world/maps/city_gates.py:10` records that race-based gate selection is out
of scope, so adding a row means a human character can walk into a settlement
the lore says is hidden from other races
(`docs/lore/settlement-locations.md:33`). Three options were weighed:
gate the row by race (out of scope, and would be the first race-conditional
in `sync_grid`); omit the row and reach the village only across the
wilderness (coherent with the lore, but leaves the shipped elf preset
starting in a human capital); or accept the leak. The third was chosen
because an unreachable elven start is a worse defect than a lore
inconsistency, and because the inconsistency is recorded rather than hidden.
Gating remains open.

**The wilderness footprint is placed far from the capital's.** The capital
occupies `(58,98)`–`(62,102)`. The village's mask is placed well away from
it rather than adjacent, so the footprint-overlap and approach-cell
uniqueness rules are satisfied by construction rather than by a near miss
that a later capital expansion could break.

**No `practice` or training-ground mechanism.** 練刀場 is an exterior node
with a description. The branch's swordsmanship culture
(`docs/lore/settlement-locations.md:441`) is worth a room, but `practice` is
already room-independent, so giving the node a mechanism would invent one
where the system deliberately has none.

## Risks / Trade-offs

- **Every new character now sees two exits from 虛境**, one of which leads to
  a hidden village. → Accepted above; recorded as open rather than silently
  shipped.
- **Conflicts with `settlement-place-registry` on
  `world/maps/bootstrap.py`.** → Land this first. Here the edit is the map
  assembly at the top of the file; there it is a rewrite of
  `sync_service_interiors`. In that order the two touch different regions.
- **Two modified scenarios keep a title that now contradicts their body.**
  `anchor-placement` and `wilderness-gateway` each carry a scenario named
  "The registry has exactly one entry after this change", and a MODIFIED
  block may not drop or rename an existing scenario. → The bodies are
  rewritten to state the two-entry reality and each carries a comment saying
  the title is a retained historical artifact. A test author must read the
  body, not the title.
- **Three existing requirements assert a single-entry registry and become
  two-entry.** → Those assertions were written as "this change populates one
  entry", i.e. statements about their own scope, not invariants. Rewriting
  them to describe the registry's growth rule is the correction the second
  entry forces, and the disjointness rules they already carry become
  meaningful for the first time.
- **The village ships walkable and empty** between this change and
  `ciaran-village-commerce`. → A player can reach it and find nobody. Short
  window, and the alternative is a single change twice the size.
