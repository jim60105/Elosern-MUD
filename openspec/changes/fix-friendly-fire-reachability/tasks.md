## 1. Skill constraints

- [ ] 1.1 Set `faction_constraint=FactionConstraint.ANY` on every shipped attack and recovery skill in `world/skills/registry.py` (`basic_attack`, `fire_ball`, `wind_blade`, `shadow_slash`, and any recovery skill)
- [ ] 1.2 Confirm no skill declares `ENEMY`/`ALLY`; keep `SELF_ONLY` available for self-only effects (none currently shipped)

## 2. Targeting validation

- [ ] 2.1 In `world/rules/targeting.py`, reduce the faction check to the self-only rule: `ANY` passes every relation; `SELF_ONLY` passes only `Relation.SELF`
- [ ] 2.2 Remove ally-dropping from AREA filtering (presence/alive/range semantics unchanged)
- [ ] 2.3 Keep shorthand expansion semantics; verify `all-enemies`/`all-allies`/`all` validate like explicit lists

## 3. Friendly-fire integration

- [ ] 3.1 (Depends on the combat-settlement change's outer round transaction) Move `_scan_friendly_fire` invocation inside the round transaction in `submit_player_action`
- [ ] 3.2 Confirm per-round membership snapshot and auto-leave notification-after-commit semantics are preserved

## 4. Tests and verification

- [ ] 4.1 Tests: every attack skill can hit a companion (penalty per hit, auto-leave below 70); recovery skills resolve on allies and foes without penalty
- [ ] 4.2 Test: `SELF_ONLY` still rejects non-actor targets
- [ ] 4.3 Test: AREA expansion with `all` includes allies and applies penalties per companion hit
- [ ] 4.4 Test: penalty-failure rolls back the round's damage with the round transaction
- [ ] 4.5 Run skill-registry, targeting, combat-session, affinity, and friendly-fire tests
- [ ] 4.6 Update `docs/game/commands.md`/`command-reference.md` if combat-menu wording changes
