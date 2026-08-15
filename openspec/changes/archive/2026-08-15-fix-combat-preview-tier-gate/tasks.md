## 1. Preview gate wiring (depends on fix-npc-policy-cast-gate)

- [x] 1.1 Confirm `world.rules.progression.can_cast_skill(entity, skill) -> bool` exists (landed via `fix-npc-policy-cast-gate` task 1.1) before starting; do not implement or redefine it
- [x] 1.2 In `world/rules/action_preview.py::_skill_wide_failure`, import `can_cast_skill` from `world.rules.progression` and insert `if not can_cast_skill(actor, skill): return RejectReason.UNKNOWN_SKILL, skill_key` between the out-of-combat check and the divine-arts gate call, mirroring `_step1_ownership` ordering (`action.py:224-241`); update the function docstring and the module docstring to list elemental spell-tier eligibility among the mirrored checks

## 2. Preview parity tests

- [x] 2.1 Add an under-tier fixture helper in `world/rules/tests/test_action_preview.py` (e.g. `_under_tier_player()` with `traits.magic_level.base = 15`) alongside the existing `_player` helper, and a test proving an owned affordable `firestorm` with no affinities and no mastery is disabled with `RejectReason.UNKNOWN_SKILL` and the skill-key detail in `preview_skill`, in `revalidate_submission`, and in `ActionResolver.preflight` — all three agree
- [x] 2.2 Boundary parity test, both pass-side paths: (a) `db.affinity_elements = ["fire"]` at `magic_level == 15` (effective `floor(15 * 1.1) == 16`), and (b) no affinities at `magic_level == 16` (pure numeric `floor(16 * 1.0) == 16`) — in both cases `firestorm` is enabled in preview and revalidation, matching a successful preflight
- [x] 2.3 Mastery-override parity test: an actor owning `fire_mastery` in `db.skills["passive"]` gets `firestorm` enabled in preview regardless of magic level, matching preflight
- [x] 2.4 Direct-ownership-only test: an actor whose `db.skill_grants` holds `ConferredSkillGrant("source", "fire_mastery", 1.0)` but whose `owned_keys()` lacks `fire_mastery` (mirroring `test_progression.py::test_gate_mastery_override_is_direct_ownership_only`) still gets `firestorm` disabled with `UNKNOWN_SKILL`
- [x] 2.5 Malformed fail-closed test: patch `world.rules.progression.spell_tier_for` to raise `ValueError`, then assert `preview_skill` and `revalidate_submission` return disabled with `RejectReason.UNKNOWN_SKILL` and never raise
- [x] 2.6 Add a `world/rules/tests/test_combat_view.py` case: an actor in an engaged session with `traits.magic_level.base = 15`, `mp` at or above 30, and `db.skills = {"active": ["firestorm"], "passive": []}` gets a `SkillDescriptorView` with `enabled == False` and `reason_code == "unknown_skill"` (this drives both the Telnet `可用` line and the WebClient `enabled` field); confirm the same actor at `magic_level == 30` (baseline, gate-passing) keeps `enabled == True` so the view test is specifically about the tier gate
- [x] 2.7 Add `covers_requirement("action-resolution-pipeline::actionresolver-exposes-shared-side-effect-free-action-preview")` to the new parity tests where the assertions establish the extended requirement; run `uv run --locked python -m tools.spec_traceability check` to confirm the identifier resolves

## 3. Regression verification

- [x] 3.1 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_action_preview world.rules.tests.test_combat_view world.rules.tests.test_action_pipeline_rejections world.rules.tests.test_progression` and confirm every existing test stays green unchanged (especially `test_preview_has_no_side_effects` and the parity/ordering tests that use gate-passing skills)
- [x] 3.2 Run the full `world.rules` package suite, then `openspec validate --change fix-combat-preview-tier-gate --strict` and `git diff --check`; confirm no file outside `world/rules/action_preview.py` and the touched test files was modified
