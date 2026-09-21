## Context

One YAML file carries every assortment's offer rules and every shop's hours. It is about to grow by half again, and three content changes each need to append a section to it.

## Goals / Non-Goals

**Goals.** One file per settlement. A deterministic merge. A duplicate across files that fails loudly.

**Non-Goals.** No content change, no re-pricing, no schema change. The sections keep their shape; only which file holds them moves.

## Decisions

### Per settlement, plus one for what is not per-settlement

`price_scales` is keyed by settlement but is a single cross-cutting table, and putting each settlement's scale in its own file would mean a settlement file that declares both its own scale and its own shops — fine until a shop in one settlement needs a scale defined in another. It goes in its own `scales.yaml`.

Assortments are not strictly per-settlement either — an assortment is a reusable bundle and nothing stops two settlements referencing one. Today none do, and the bundles are named for their settlements. They go with their settlement, and if a genuinely shared bundle appears it gets a `shared.yaml`.

### Duplicates fail, they do not merge

The natural implementation merges dicts and lets the last file win. That is the wrong default here: the reason to split is that each file owns its section, and a silent override means two files can disagree about a price with no signal.

So the merge counts keys and raises naming both files. This is the same fail-closed posture the rest of the catalog loader already takes.

### Sorted order, stated as deliberate

`PLACE_REGISTRY`'s slice order carries a comment explaining that it is load-bearing. The commerce directory's order matters less — the merge is by key, not positional — but "the loader iterates a directory" invites a non-deterministic listing, so the sort is explicit and the requirement says so.

## Risks

**A file that fails to parse is now one of several.** The error must name which file, not just "commerce rulebook". Cheap to get right and easy to forget.

**Moving ~470 lines of YAML by hand can drop a row.** The before-and-after comparison of the whole resolved catalog is the guard, and it is the first thing to write.
