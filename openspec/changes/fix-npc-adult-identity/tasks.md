## 1. Shared adult-identity helper

- [ ] 1.1 Add `ensure_npc_adult_identity(npc)` to `typeclasses/npcs.py` (set-if-absent, adult baseline 18/18)

## 2. Wire into spawn paths

- [ ] 2.1 Call the helper in `world/rules/guild_economy.py::_sync_service_host` after `apply_race_baseline`
- [ ] 2.2 Call the helper in `world/rules/guild_exams.py::_spawn_opponent` after trait/skill setup

## 3. Tests and verification

- [ ] 3.1 Test: service hosts carry 18/18 after sync
- [ ] 3.2 Test: exam opponents carry 18/18 after spawn
- [ ] 3.3 Test: helper preserves existing adult ages and fills only a missing field when identity is partial
- [ ] 3.4 Run `world/rules` guild/economy tests and the art adult-gate tests
