## 1. Shared observation boundary

- [ ] 1.1 Extract `after_successful_movement(player, room)` from the four success paths (grid `MovementCostMixin.at_post_traverse`, `WildernessGateExit.at_traverse`, `WildernessReturnExit.at_traverse`, wilderness step), preserving today's charge/arrival/follow ordering
- [ ] 1.2 Refactor the four paths to call the shared helper
- [ ] 1.3 Add the onboarding observation call inside the shared helper and remove the `GridRoom.at_object_receive` onboarding hook (`typeclasses/rooms.py`), keeping quest room observation intact

## 2. Idempotency safeguards

- [ ] 2.1 Confirm `observe_room_entry` is a no-op for onboarded players and repeated arrivals (one-transition rule); add a guard if missing

## 3. Tests and verification

- [ ] 3.1 Tests: guided player entering plain `Room`, `InstanceRoom`, and wilderness is marked skipped; corridor arrival and onboarded moves are no-ops
- [ ] 3.2 Run onboarding, rooms, exits, and wilderness movement tests
