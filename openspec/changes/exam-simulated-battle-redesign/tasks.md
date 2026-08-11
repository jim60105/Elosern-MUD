## 1. Simulated-battle semantics

- [ ] 1.1 Remove the session-wide `nonlethal` flag for `guild_exam` mode in `world/rules/combat_session.py::_context_for` (per-target `nonlethal_keys` unchanged)
- [ ] 1.2 Keep kill-reward suppression (no kill XP/loot, DEFEAT quest progress, or protected-entity failure) for exam rounds

## 2. Full restoration

- [ ] 2.1 In `world/rules/guild_exams.py::start_guild_exam`, restore candidate and opponent HP/MP/SP to full after spawn, inside the all-or-nothing start
- [ ] 2.2 In `settle_session`'s exam branch, restore both sides' HP/MP/SP to full after the outcome is recorded and before opponent deletion

## 3. Player-facing description

- [ ] 3.1 Update the pre-exam text (Telnet `guild exam` intro and Web exam intro) to state the simulated-battle rule and full-restoration guarantee

## 4. Tests and verification

- [ ] 4.1 Test: examiner HP reaches 0 → PASS; opponent deleted; both sides restored to full HP/MP/SP
- [ ] 4.2 Test: candidate HP reaches 0 → FAIL, no rank change; candidate restored to full HP/MP/SP
- [ ] 4.3 Test: wounded/spent candidate and examiner start the exam at full HP/MP/SP
- [ ] 4.4 Test: lethal exam defeat grants no kill XP/loot, DEFEAT progress, or protected-entity failure
- [ ] 4.5 Test: failed exam start restores nothing
- [ ] 4.6 Run guild-exam, combat-session, quest-planner, and protected-entity tests
