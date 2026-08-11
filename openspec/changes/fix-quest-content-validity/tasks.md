## 1. Quantity cap

- [ ] 1.1 Add per-kind quantity validation in `world/quests/definitions.py::_validate_objective` (REACH/ESCORT require exactly 1)
- [ ] 1.2 Mirror the cap in `world/ai/scenario_director.py` proposal validation and `world/quests/compile.py`

## 2. ESCORT publish refusal

- [ ] 2.1 Reject ESCORT stages at proposal/compile time with a clear error until a protected-entity binding flow exists
- [ ] 2.2 Refuse `guild request` escort/護衛 requests with a clear player-facing message (director offline-template and live paths)

## 3. Defensive arrival increment

- [ ] 3.1 In `world/quests/room_observation.py::observe_room_entry`, increment progress by one (capped at quantity) instead of unconditional `fulfill_record`; keep the one-transition and post-follow idempotency rules

## 4. Tests and verification

- [ ] 4.1 Test: quantity-2 REACH proposal is rejected; quantity-1 accepted
- [ ] 4.2 Test: escort request is refused with a clear message and nothing is registered
- [ ] 4.3 Test: arrival increments at most one per event and never over-fills
- [ ] 4.4 Run quest definitions, room-observation, compile, and scenario-director tests
