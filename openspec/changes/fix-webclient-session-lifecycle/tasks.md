## 1. Puppet lifecycle sequence

- [ ] 1.1 On OOC: deliver a client transition (full unavailable snapshot or lifecycle envelope) that clears character panels and locks mutations, sent before retiring
- [ ] 1.2 Add `reset_client_sequence(session)` (coordinator epoch bump + clear `elosern_actor_id`) and call `retire_sequence` + it from `CmdOOC.func`
- [ ] 1.3 Ensure `CmdIC.func`/repuppet of the same character produces a fresh epoch (assert no reuse of the old cache/marker)
- [ ] 1.4 Keep the actor-id-diff reset as a fallback for other puppet changes
- [ ] 1.5 Add a browser test: OOC clears the UI without requiring a stale action click first

## 2. No-puppet action rejection

- [ ] 2.1 In `server/conf/inputfuncs.py::ui_action`, return a bounded rejection envelope (`no_puppet`, no character data) when `session.puppet` is None
- [ ] 2.2 Client: handle `no_puppet` as a rejection that releases the in-flight mutation lock without touching panels

## 3. Terminal combat full refresh

- [ ] 3.1 In `world/rules/combat_result.py::settle_to_oob_result`, return empty affected panels for terminal outcomes (keep the triple for non-terminal rounds)
- [ ] 3.2 Verify the dispatcher publishes a full snapshot on empty affected panels with a fresh revision
- [ ] 3.3 Client: confirm full snapshot replaces all panels and the exploration dock mounts from fresh state

## 4. Tests and verification

- [ ] 4.1 Browser/unit tests: `ooc` clears panels and blocks mutations; stale click after OOC releases the lock; repuppet of same character shows fresh state
- [ ] 4.2 Tests: terminal combat outcome leaves no stale exploration/character/services/local_map payload
- [ ] 4.3 Run `web/webclient/actions/tests`, presentation tests, and the combat browser tests (`test_browser_combat.py`, `test_browser_combat_rejection.py`)
- [ ] 4.4 Update `docs/game/commands.md`/`command-reference.md` only if OOC/IC player-visible behavior changes (expected: no)
