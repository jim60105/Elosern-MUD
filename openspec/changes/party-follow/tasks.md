# party-follow Tasks

## 1. Follow implementation

- [ ] 1.1 Add a safe bound-companion resolver to `world/rules/party.py` (skips stale dbids,
      non-NPC entries, and backref mismatches) and `follow_companions(player, source_location, *,
      destination=None, wilderness_coordinates=None, wilderness_name=WILDERNESS_NAME)`: filters
      companions co-located in the source room, moves each via `move_to(destination, quiet=True)`
      in destination mode or `enter_wilderness(companion, coordinates=..., name=...)` in
      wilderness mode, collects failures per companion, and never raises.
- [ ] 1.2 Hook `follow_companions(traversing_object, source_location, destination=...)` into
      `MovementCostMixin.at_post_traverse` in `typeclasses/exits.py` after charging/recording,
      no-op for non-PlayerCharacter traversers.
- [ ] 1.3 Hook the wilderness success paths in `typeclasses/exits.py`:
      `WildernessGateExit.at_traverse` (wilderness_coordinates=entry.wilderness_xy) and both
      success branches of `WildernessReturnExit.at_traverse` (ordinary step:
      wilderness_coordinates=target_location.coordinates; return: destination=grid_room).
- [ ] 1.4 Emit the fixed Traditional Chinese 跟丟了 notification naming every left-behind
      companion, exactly once per traversal.
- [ ] 1.5 Add integration tests (`EvenniaTest`): grid traversal follows companions; wilderness gate
      entry, ordinary wilderness step, and wilderness return each follow through the provider API;
      clock advances by exactly the player's cost; no announce messages or player-gated observer
      side effects fire for companions; an unenterable destination leaves the companion behind with
      the named 跟丟了 notification while others follow; empty-party traversal has no side
      effects; a bound companion in another room is not pulled; teleport/spawn relocation does not
      pull companions; a stale party entry never raises and does not block other companions; a
      left-behind companion rejoins on the next traversal from its room.

## 2. Verification

- [ ] 2.1 Run the touched test labels, including the existing seam modules:
      `world.rules` party/movement, `typeclasses` exits (incl. `test_exits.py` and
      `test_exit_movement_cost.py`), `world.maps` wilderness integration.
- [ ] 2.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [ ] 2.3 Annotate substantive new tests with `covers_requirement` canonical IDs; run
      `openspec validate party-follow --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
