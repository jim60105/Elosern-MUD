## 1. Skill constraints

- [x] 1.1 Set `faction_constraint=FactionConstraint.ANY` on every shipped attack and recovery skill in `world/skills/registry.py` (`basic_attack`, `fire_ball`, `wind_blade`, `light_sword_style`, `shadow_slash`; no recovery skill is currently shipped)
- [x] 1.2 Confirm no skill declares `ENEMY`/`ALLY`; keep `SELF_ONLY` available for self-only effects (shipped `flee` only)
- [x] 1.3 Update the player-facing attack-skill descriptions from enemy-only wording to free-targeting wording (`敵人` → `目標`)

## 2. Targeting validation

- [x] 2.1 In `world/rules/targeting.py`, reduce the faction check to the self-only rule: `ANY` passes every relation; `SELF_ONLY` passes only `Relation.SELF`; legacy `ALLY`/`ENEMY` values restrict nothing
- [x] 2.2 Remove ally-dropping from AREA filtering (presence/alive/range semantics unchanged)
- [x] 2.3 Keep shorthand expansion semantics; verify `all-enemies`/`all-allies`/`all` validate like explicit lists

## 3. Friendly-fire integration

- [x] 3.1 (Depends on the combat-settlement change's outer round transaction) Move `_scan_friendly_fire` invocation inside the round transaction in `submit_player_action` (landed with `fix-combat-settlement-recovery`; verified in place)
- [x] 3.2 Confirm per-round membership snapshot and auto-leave notification-after-commit semantics are preserved

## 4. Delta spec coherence (apply.md step 1)

- [x] 4.1 Add `party-system` delta: companions are selectable by freely-targetable skills (friendly-fire penalty applies instead of faction rejection)
- [x] 4.2 Add `action-resolution-pipeline` delta: the different-context faction scenario uses `SELF_ONLY` instead of `ENEMY`
- [x] 4.3 Amend `targeting-validation` delta: rename the shortcuts requirement, amend the out-of-combat ENEMY scenario to the legacy-restricts-nothing rule
- [x] 4.4 Amend `skill-registry` delta: rename the SkillDef-faction requirement to the scope contract
- [x] 4.5 Fold the scan-transaction delta into the existing atomicity requirement (no duplicate requirement)

## 5. Tests and verification

- [x] 5.1 Update existing tests that assert the old enemy-only contract (`test_combat_party.py::test_enemy_targeting_skill_never_selects_companion`, `test_combat_session.py::test_wrong_faction_target_rejects`, `test_action_preview.py::test_revalidate_rejects_stale_or_wrong_shape`, `test_targeting.py` truth table and context-polymorphism tests)
- [x] 5.2 Tests: every attack skill can hit a companion (penalty per hit, auto-leave below 70); recovery skills resolve on allies and foes without penalty
- [x] 5.3 Test: `SELF_ONLY` still rejects non-actor targets
- [x] 5.4 Test: AREA expansion with `all` includes allies and applies penalties per companion hit
- [x] 5.5 Test: penalty-failure rolls back the round's damage with the round transaction (extend the existing rollback test with HP assertions)
- [x] 5.6 Sync the amended delta specs into `openspec/specs/` and update traceability annotations for renamed requirements
- [x] 5.7 Run skill-registry, targeting, combat-session, affinity, and friendly-fire tests
- [x] 5.8 Update `docs/game/commands.md` (no wording changes needed)/`command-reference.md` if combat-menu wording changes
