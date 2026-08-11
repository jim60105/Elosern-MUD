## 1. Completion gate

- [ ] 1.1 Add a completion gate (co-location + `interaction_reason(npc, "talk") is None`) evaluated at the top of `world/rules/npc_intents.py::apply_npc_intent`, returning a stable stale-completion result that skips the intent
- [ ] 1.2 Keep the existing pre-call checks as a fast path

## 2. Stale-completion surfacing

- [ ] 2.1 In `typeclasses/npcs.py::at_talked_to`, render the speech and append the stale-context note when the gate fails
- [ ] 2.2 In the Web freeform adapter (`exploration_actions.py`), surface the same outcome

## 3. Tests and verification

- [ ] 3.1 Tests: give/take/relation/lore intents dropped after separation or busy-state transition; applied when co-located
- [ ] 3.2 Test: party-invite rechecks remain in force (no double gate)
- [ ] 3.3 Run npc-dialogue, npc_intents, exploration-actions, and affinity tests
