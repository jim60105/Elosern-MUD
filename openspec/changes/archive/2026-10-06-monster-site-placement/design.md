## Context

Design §5 splits placement into deterministic regional ambient rules and authored camps/nests/boss
sites. The repo already has the ambient half's discipline — `world/maps/wilderness_population.py`
reconciles one pure model per coordinate, guarded by the `db.population_key` ownership marker, with
foreign-monster immunity and active-session protection — but no site concept at all. The world clock
(`world/rules/clock.py` plus the clock-upkeep registration seam) is the only in-game time source, and
`monster-identity-construction` provides the one legal way to build a species-backed individual.

## Goals / Non-Goals

**Goals:** authored placement data in the lore idiom; site lifecycle with ownership; ambient/site
domains that cannot cross; recovery only on in-game conditions; capacity ceilings; deterministic ambient
selection. **Non-Goals:** no quest provisioning (the quest owner asks existing managers and is covered
by `monster-quest-objectives`), no replacement of the tier-example ambient branch, no spawn API in lore,
no combat or AI change, no story-flag machinery.

## Decisions

**D-P1 One placement module, two registries, both in lore.** Ambient rules and sites reference the same
variant keys and validate against the same species/variant/habitat data; one module keeps cross-checks
in one place (same shape as `monster-species-registry` D-S1). Execution stays out of lore entirely —
lore exposes no verb that could spawn.

**D-P2 Sites are a new `world/maps/monster_sites.py`, ambient stays in `wilderness_population.py`.**
The population module's contract (per-coordinate pure model, one marker) is extended additively for
species-bearing entries; the site lifecycle needs clock hooks, per-site state, and recovery semantics
that do not belong in a coordinate-reconciliation function. Both owners reuse the *same* marker
discipline — ownership markers are how the single-writer boundary distinguishes "mine" from "foreign",
and a third owner kind is a bug, not a feature.

**D-P3 Recovery conditions are a closed vocabulary, not expressions.** `recover_after_ticks: int` (in
game clock) is the only condition shipped; the registry vocabulary can admit a future approved
deterministic predicate by name, never free-form text or wall-clock time. One-shot sites carry no
condition and their cleared state is durable until an author-side change re-issues them — an explicit
non-goal to invent a reissue command nobody asked for.

**D-P4 Recovery creates fresh individuals, never resurrected ones.** Even for a recoverable site, the
old rows stay dead: identity continuity across a recovery would let old quest bindings count new
monsters (design §6's bound-clearing rule). Fresh rows plus a durable `cleared_at_tick` per site give
the quest layer a consistent "has the site recovered?" question to ask.

**D-P5 The tier-example branch stays.** Wholesale conversion of ambient cells to species identity is
content-blocked — the bestiary covers six species, the map needs more, and the introductory hunt plus
the pinned `(60, 103)` formula are contract-pinned. Keeping both branches honors the design's own
limitation table (tier examples were never species identity) instead of faking species coverage. The
proposal declares this boundary so it is not mistaken for a shim.

**D-P6 Recovery runs inside the existing clock-upkeep settlement** (the named `world/maps/` seam that
already settles due events in fixed order), so recovery ordering vs other due events is deterministic
and observable (`clock_advance` context), not a background timer.

## Risks / Trade-offs

- Two ambient branches (tier-example + species rules) coexist until species content widens; mitigated by
  one marker discipline and by tests asserting each branch's cells are disjoint from the other's.
- Sites add persistent per-site state to `world/maps/`; kept minimal (`state`, `cleared_at_tick`) so
  there is no shadow copy of individual data.

## Open Issues

None; species content beyond the approved six and any richer recovery predicates are future authored
content, gated by this registry's validation.
