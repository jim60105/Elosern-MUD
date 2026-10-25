# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Identity inventory and companion readers

Implement Shared contract v2 once for both sources. Include package_role companion references using authorized package role_id/current binding, safe labels and foreign/cancelled/detached/remote rejection in focused tests.

- [x] 1.1 Implement RaceIs, SocialIdentityIs, Carries and CompanionPresent against explicit sources; add world/rules/tests/test_dialogue_physical_conditions.py with owner/actor asymmetry, no consumption and stale/co-location controls. Document each source and fail-closed behavior.

## 2. Clock skills and exposure boundaries

- [x] 2.1 Implement cyclic daypart intervals, SkillHandler ownership plus canonical proficiency reader, effective_exposure inclusive bounds. Tests cover exact daypart edges/wrap, missing clock, ownership versus conferral, threshold edges and worn bias without handler writes.

## 3. Hints and scene selection integration

- [x] 3.1 Implement All/Any bounded recursion, canonical labels and deterministic scene variant selection; wire select_authored_topic eligibility to fail closed with no protected body. Add tied-priority/unknown-label rejection tests and preserve fixed delivered variant on refresh.

## 4. Independent offline and browser acceptance

- [ ] 4.1 Extend race-qualified possession and equipment variant fixture/method in test_browser_exploration_dialogue.py; update Python/browser ownership and dialogue author docs, run focused condition tests/browser method and contract_gate. No new effect/reward subsystem.

