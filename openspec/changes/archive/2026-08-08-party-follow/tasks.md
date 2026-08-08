# party-follow Tasks

## 1. Follow implementation

- [x] 1.1 Add a safe bound-companion resolver to `world/rules/party.py` (skips stale dbids,
      non-NPC entries, and backref mismatches) and `follow_companions(player, source_location, *,
      destination=None, wilderness_coordinates=None, wilderness_source_coordinates=None,
      wilderness_name=WILDERNESS_NAME)`: filters companions co-located in the source room (and,
      in wilderness mode, companions registered in the script's `itemcoordinates` at
      `wilderness_source_coordinates`, because the contrib recycles wilderness rooms out from
      under NPC contents), moves each via `move_to(destination, quiet=True)` in destination mode
      (deregistering a wilderness companion from `itemcoordinates` after a successful move) or
      `enter_wilderness(companion, coordinates=..., name=...)` in wilderness mode, collects
      failures per companion, and never raises.
- [x] 1.2 Hook `follow_companions(traversing_object, source_location, destination=traversing_object.location)` into
      `MovementCostMixin.at_post_traverse` in `typeclasses/exits.py` after charging/recording,
      no-op for non-PlayerCharacter traversers.
- [x] 1.3 Hook the wilderness success paths in `typeclasses/exits.py`:
      `WildernessGateExit.at_traverse` (wilderness_coordinates=entry.wilderness_xy) and both
      success branches of `WildernessReturnExit.at_traverse` (ordinary step:
      wilderness_coordinates=traversing_object.location.coordinates with
      wilderness_source_coordinates=current; return: destination=grid_room with
      wilderness_source_coordinates=current).
- [x] 1.4 Emit the fixed Traditional Chinese 跟丟了 notification naming every left-behind
      companion, exactly once per traversal.
- [x] 1.5 Add integration tests (`EvenniaTest`): grid traversal follows companions; wilderness gate
      entry, ordinary wilderness step, and wilderness return each follow through the provider API;
      clock advances by exactly the player's cost; no announce messages or player-gated observer
      side effects fire for companions; an unenterable destination leaves the companion behind with
      the named 跟丟了 notification while others follow; empty-party traversal has no side
      effects; a bound companion in another room is not pulled; teleport/spawn relocation does not
      pull companions; a stale party entry never raises and does not block other companions; a
      left-behind companion rejoins on the next traversal from its room.

## 2. Verification

- [x] 2.1 Run the touched test labels, including the existing seam modules:
      `world.rules` party/movement, `typeclasses` exits (incl. `test_exits.py` and
      `test_exit_movement_cost.py`), `world.maps` wilderness integration.
- [x] 2.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [x] 2.3 Annotate substantive new tests with `covers_requirement` canonical IDs; run
      `openspec validate party-follow --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
