## Why

The wilderness Web navigation surfaces disagree with actual traversal (audit finding F24): the minimap emits `action=None` on every wilderness node (no move possible), and the exploration move rows derive destinations from the Evennia pooled self-loop Exit (`destination` is the current room), so every direction advertises the current node — and the gateway south exit actually returns to the grid while the UI says otherwise.

## What Changes

- A single canonical exit-destination resolver computes the real arrival node from the current coordinates, direction, and gateway rules — the same logic `WildernessReturnExit.at_traverse` uses.
- The wilderness minimap layer attaches `explore.move` actions for every traversable adjacent node.
- The exploration move rows use the canonical resolver instead of `exit_obj.destination`.

## Capabilities

### New Capabilities

- `canonical-wilderness-destination`: shared destination resolution for wilderness exits.

### Modified Capabilities

- `webclient-local-map`: wilderness nodes are actionable with correct destinations.
- `webclient-exploration-menu`: move-row destinations match actual arrival nodes.

## Impact

- `web/webclient/presentation/local_map.py`, `web/webclient/presentation/exploration.py`, new shared resolver (near `typeclasses/exits.py` or `world/maps/`), tests.
