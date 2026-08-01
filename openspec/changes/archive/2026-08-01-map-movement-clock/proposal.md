## Why

`rulebook/clock.yaml::command_defaults.move: 30` has been declared, inert data since change 11
(`world-clock`). Change 12 (`map-anchor-grid`) explicitly declined to wire it. Change 13
(`map-wilderness`) wired only its own new `wilderness_move: 9000` cost and explicitly recorded, in
its own design.md D-8, that "no roadmap item after this one is scoped to give it one" — `move: 30`
is a **permanent gap by omission**, not a transitional one: under the current roadmap, walking
between the sample city's thirteen rooms never costs game time, while walking through the
wilderness right next to it does. The project owner has asked for a small, inserted roadmap change
to close that gap and make the time model coherent.

Closing it correctly requires more than wiring one constant. Three unrelated exit lineages exist in
this project (the project's own `typeclasses/exits.py::Exit`, the `xyzgrid` contrib's `XYZExit` used
directly, and change 13's bespoke `WildernessGateExit`/`WildernessReturnExit`), and change 13 already
built its own, separate movement-clock mechanism for one of them. Wiring `move: 30` onto the other
two without touching change 13's mechanism would leave two independent "walking costs time"
implementations in the codebase, one of which (change 13's) is still unimplemented and therefore
free to fold into a shared one now, before it ever ships. This change unifies all three lineages onto
one rulebook-driven cost table and one shared charging function, and folds change 13's own
wilderness wiring into it rather than leaving it a permanent, parallel special case.

## What Changes

- Add `world/rules/movement.py::charge_movement(traversing_object, cost_key)` — the single function
  every exit lineage calls to advance `WorldClock` for one successful step. It resolves the cost from
  `CLOCK_YAML["command_defaults"][cost_key]`, always uses `AdvanceSource.COMMAND` (movement never
  settles through the combat source — verified: the already-implemented `flee` skill
  (`world/rules/disengage.py`) never moves an entity between rooms at all, so no exit traversal is
  ever combat-sourced), and only charges when `traversing_object` is a `PlayerCharacter` — matching
  design doc D4 ("the world advances only on player action") and change 14's own precedent of gating
  on `PlayerCharacter` specifically rather than any `LivingEntity`.
- Add `typeclasses/exits.py::MovementCostMixin`, hooking `at_post_traverse` — not `at_traverse`'s own
  return value, which is verified (by reading `evennia/objects/objects.py` directly, and confirmed by
  a live `EvenniaTest` probe) to be `None` in both the success and failure branch of the stock
  `DefaultExit.at_traverse`. `at_post_traverse` is the hook that implementation calls exclusively on a
  successful `move_to()`, so a mixin built on it needs no return-value inspection and cannot fire for
  a locked exit (never reaches `at_traverse` at all — checked by `ExitCommand.func` before calling it)
  or a vetoed `at_pre_move` (aborts `move_to()` before `at_post_traverse` runs).
- Retrofit `typeclasses/exits.py::Exit` onto `MovementCostMixin` with `movement_cost_key = "move"`.
  This is a **free** consequence for two of the three lineages that already use this class: change
  12's Limbo↔grid bridge exit, and change 14's `spawn_instance_room()` origin/return exit pair — both
  already use `typeclasses.exits.Exit`, so neither needs any code change to start being charged.
- Add `typeclasses/exits.py::CostedXYZExit(MovementCostMixin, XYZExit)`, `movement_cost_key = "move"`
  — verified directly against the real, installed `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit` (not
  a stand-in) that the mixin composes correctly via ordinary MRO and that `XYZExit`'s own coordinate
  behavior survives unchanged.
- Wire `CostedXYZExit` into 聖潔王都's twelve intra-city exits via a single `("*", "*", "*")` wildcard
  entry in the sample city's map-data `"prototypes"` dict — verified directly against the real
  `evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()` that this one entry overrides every link's
  typeclass on the map, with no per-coordinate bookkeeping. Change 12 (`map-anchor-grid`) is not yet
  implemented, so this lands as a `MODIFIED sample-city-altoria` delta spec here, resolved against
  real code at implementation time, exactly as change 13 already did for `GridRoom`'s base classes.
- Fold change 13's own `WildernessGateExit`/`WildernessReturnExit` clock wiring into
  `charge_movement(traversing_object, "wilderness_move")`, replacing their bespoke inline
  `get_world_clock().advance(...)` calls. Observable behavior is unchanged (same cost, same
  success-only condition, same `AdvanceSource.COMMAND`); the only change is that they now go through
  the shared function instead of duplicating it. Change 13 is committed but unimplemented, so this
  edits its own `design.md` (D-5, D-6, D-8, and the "No change to the grid layer's own
  movement-clock posture" Non-Goal) directly, and this change also files a `MODIFIED wilderness-gateway`
  delta spec updating the two clock-charging requirements to name the shared function, plus the
  "wilderness_move is a new, distinct clock cost" requirement's "Grid traversal is unaffected"
  scenario (see the "Grid traversal now charges" amendment below).
- File a `MODIFIED world-clock` delta spec against the archived `openspec/specs/world-clock/spec.md`,
  replacing "move and converse command-default time costs are declared as rulebook data only" with a
  requirement that `move` is now consumed by ordinary exit traversal (no bespoke `move` command is
  added — Evennia's own per-exit auto-generated traverse commands are what fire `at_traverse`).
  `converse: 60` remains untouched and out of scope, exactly as change 13 left it.
- Amend `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §11 with this change's roadmap
  row (see design.md for the exact position and dependency reasoning), and update change 13's
  design.md D-8 note so it no longer claims "no roadmap item ... is scoped to give it one."

## Capabilities

### New Capabilities
- `movement-cost-charging`: `world/rules/movement.py::charge_movement()`, `typeclasses/exits.py::
  MovementCostMixin`, `CostedXYZExit`, the `PlayerCharacter` gate, the `AdvanceSource.COMMAND` choice,
  and the structural (not heuristic) exclusion of failed traversals, locked exits, teleports, spawns,
  and change 14's `_relocate_to_default_home()` reclamation relocation.

### Modified Capabilities
- `world-clock` (change 11, archived): `command_defaults.move` is no longer purely inert rulebook
  data — it is consumed by every successful `typeclasses.exits.Exit`/`CostedXYZExit` traversal by a
  `PlayerCharacter`. `converse` is unaffected.
- `wilderness-gateway` (change 13, pending): the two clock-charging requirements
  ("A successful traversal advances the world clock..." and "Every successful WildernessReturnExit
  traversal advances the clock...") now name `world.rules.movement.charge_movement()` as the
  mechanism instead of an inline `get_world_clock().advance()` call. Observable behavior (cost,
  success-only condition, `AdvanceSource.COMMAND`) is unchanged. The "wilderness_move is a new,
  distinct clock cost" requirement's "Grid traversal is unaffected" scenario is amended: intra-city
  grid traversal now charges `move` via `CostedXYZExit` (this change's own wiring), so the old
  assertion that it "remains unwired to the clock" is retired, while the requirement's real subject —
  grid steps never read `wilderness_move`, wilderness steps never read `move` — is preserved.
- `sample-city-altoria` (change 12, pending): the sample city's twelve intra-city exits now spawn as
  `CostedXYZExit` instead of the bare contrib `XYZExit`, via one wildcard map-data prototype override.
  The room/exit topology, count, and connectivity this capability already specifies are unchanged.

## Impact

- New files: `world/rules/movement.py`, its test module.
- Edits to already-landed implementation files: `typeclasses/exits.py` (`MovementCostMixin`,
  `Exit` retrofit, `CostedXYZExit` added).
- Edits to other pending changes' own artifacts (not yet implemented, so no landed code changes):
  `openspec/changes/map-wilderness/design.md` (D-5, D-6, D-8, one Non-Goal).
- One amendment to `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §11 (new roadmap row).
- No database migration concerns (project is unreleased, zero users). `converse: 60` remains
  unwired, exactly as every prior change left it — out of this change's scope.
