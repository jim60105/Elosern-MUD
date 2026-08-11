## Context

`WildernessReturnExit.at_traverse` (`typeclasses/exits.py:149-193`) routes by coordinate math (and the registered south gateway), while the Evennia contrib builds the eight direction exits as self-loops (`destination=room`, `evennia/contrib/grid/wilderness/wilderness.py:386-405`). `_wilderness_layer` (`web/webclient/presentation/local_map.py:593-615`) emits `action=None` for every node, and `_move_rows` (`web/webclient/presentation/exploration.py:490-518`) reads `exit_obj.destination` and encodes the current room's coordinates (`exploration.py:463-467`).

## Goals / Non-Goals

**Goals:**
- UI destinations and actions agree with traversal for all wilderness exits.
- One resolver shared by both presenters (and usable by future surfaces).

**Non-Goals:**
- Changing traversal mechanics or the contrib's self-loop exits.
- Rewriting the grid/interior map layers.

## Decisions

**D1 — Pure function resolver.** `resolve_wilderness_destination(room, direction, gateway_rule)` mirrors `WildernessReturnExit`'s routing: coordinate step for ordinary directions, gateway override for the registered south exit; returns a node identity (`wild:` or `grid:`). The resolver is a pure read helper in `world/maps/` (no state writes), so presenters can call it freely.

**D2 — Presenters consume the resolver.** `_wilderness_layer` builds move descriptors for traversable adjacent nodes; `_move_rows` uses the resolver instead of `exit_obj.destination`.

**D3 — Traversal stays authoritative.** The move action still submits `exit_ref` + current node to `explore.move` (`exploration_actions.py:317-355`); the resolver only fixes presentation, so no relocation path changes. Nodes that are out of bounds, lack a gateway target, or otherwise cannot be traversed SHALL carry no move action (the presenter asks the resolver whether the edge is traversable, not merely whether a direction exists).

## Risks / Trade-offs

- **Resolver/traversal drift**: the resolver is extracted from the same routing code the exit uses; a comment and test pin them together.
- **Gateway rule lookup**: the resolver needs the gateway mapping; it reads the same registration the exit uses (single source).
