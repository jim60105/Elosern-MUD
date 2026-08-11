## 1. Context declarations

- [ ] 1.1 Require an explicit `requires_event_context` (possibly empty `frozenset`) on every `register_effect_handler` call, for `set_disguise` and `confer_skill_partial` and all other handlers
- [ ] 1.2 Make `_require_context` read the declaration (single source of truth)
- [ ] 1.3 Add a registry-completeness test: every registered handler declares the field

## 2. Preflight and preview checks

- [ ] 2.1 Add the context check to `ActionResolver.preflight` (`world/rules/action.py`) with a stable rejection reason, before any round cost
- [ ] 2.2 Add the same check to `_skill_wide_failure` (`world/rules/action_preview.py`) and the combat-session revalidation path
- [ ] 2.3 Derive combat-menu availability from the same check (`world/rules/combat_view.py`)

## 3. Tests and verification

- [ ] 3.1 Tests: `status_disguise`/`dominion_art` in combat reject at preflight (no round, no enemy action) and appear disabled in the menu
- [ ] 3.2 Test: out-of-combat `status_disguise` with supplied context still resolves
- [ ] 3.3 Run action-pipeline, combat-view, combat-session, and webclient combat-menu tests
