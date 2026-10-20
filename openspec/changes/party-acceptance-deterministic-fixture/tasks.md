# Tasks

## 1. Authorized dedicated initialization

- [x] 1.1 Coordinate with the original acceptance apply owner to amend only its design setup policy to the dedicated pre-session seed plus protected GM-only runtime interventions; update the existing fixture guide with launch flags and incompatible combinations, and verify the named journey/unchecked evidence criteria remain intact on that owner's current feature branch.
- [x] 1.2 Add the opt-in isolated synthetic fixture mode through existing deterministic construction/grant/inventory/map seams; test exact tagged 艾拉/卡恩 identities, membership/capacity/co-location, owned heal/opener and prerequisites, bags/equipment, wounded targets, merchant headroom/purse, finishable monster and connected exit; document the starting-state table and verify no duplicated seed identities and no change to existing modes without the new option.
- [x] 1.3 Add consumer regressions for member-owned item/heal/hostile-opening previews, readable member lineage and real exit navigation; verify incompatible new-mode composition rejects before mutation, required actor/target/resource facts survive publication, and register every new module/method in its exact Evennia/browser manifest with requirement annotations.

## 2. Integration handoff

- [x] 2.1 Boot the dedicated mode after save/lineage fixes land and run its exact managed panel/text smoke with no shell/raw patches or external services; run focused fixture tests, exact ownership/frozen contracts and `openspec validate party-acceptance-deterministic-fixture --strict`, then record runnable launch instructions and actual consumer state without checking original UI acceptance steps complete.

## Workflow follow-up

- Land all six batch fixes before resuming `party-management-acceptance` on its existing branch/worktree.
- Its owner exercises the exact journey, including successful consumable use, transfer to 卡恩, UI re-equipment, 艾拉's field heal, cancelled then confirmed hostile opening and finished fight, possession/exit/followers and possessed surfaces, plus combat equipment with transfer refusal. Record real UI and text evidence separately; unexecuted steps stay evidence gaps.
- Ordinary contract/traceability checks become authoritative after synchronization; archive original acceptance only when its genuine blockers and all unchecked tasks are resolved.

## Verification record

- Task 1.1: `os-apply-party-management` committed `2ba526ee` on `feat/party-management-acceptance`; its diff changes only the Journey setup clause (one insertion/one deletion), and its tasks/specs are untouched (only task 1.1 checked). Launch flags, incompatibilities, the starting-state table and the pre-login fixture / post-login protected-GM policy are documented in `docs/development/evennia-testing-guide.md`.
- Task 1.2: `web/tests/browser/seed/party_management_acceptance_fixture.py` composes the tagged pair, lineage grants, bags/equipment, wounds, merchant stock/purse, a never-fleeing finishable monster and connected exits through the existing seams; the fixture is inert without the flag and rejects a non-fresh runtime before mutation.
- Task 1.3: `web/webclient/actions/tests/test_party_management_acceptance_fixture.py` exercises item/heal/opening previews, both lineages, purchase/transfer/equipment/sale, the combined heal-then-open-then-finish sequence with the remaining resources, possessed exit traversal with followers; composition rejection and the flagless no-op are covered; the browser smoke is registered in `.github/browser-shards.json`; the Evennia module is owned by the existing `web.webclient.actions` shard label (an explicit module label overlaps, as the ownership contract reported). Publication evidence across the seed → server boundary covers party member identity, merchant identity/open state/stock and readable lineage text; actor-owned skills, legal targets, MP and bags/equipment are asserted in-process rather than claimed as published.
- Task 2.1: `uv run --locked evennia test --settings test_settings.py --noinput --keepdb web.webclient.actions.tests.test_party_management_acceptance_fixture` -> 14 tests OK. `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_party_acceptance.PartyManagementFixtureSmokeBrowserTest.test_dedicated_fixture_publishes_members_merchant_and_lineage` -> 1 test OK (managed panel + text smoke, no external service). `world.tests.test_synthetic_data` -> 25 tests OK. `tests.test_evennia_test_optimization_contract`, `tests.test_webclient_frozen_contract`, `tests.test_browser_verification_contract`, `tests.test_data_independence_webclient_actions`, `tests.test_test_data_lint` -> 71 tests OK. `openspec validate party-acceptance-deterministic-fixture --strict` passed.

## Review record

- Plan critique (blocking) folded into this change: wounded 艾拉 for a legal self-potion, Evennia consumer tests relocated under `web/webclient/actions/tests`, explicit commander threading in previews, real purchase/transfer/equipment/sale, possessed traversal with followers, a real finished encounter, an early fresh-runtime guard, and a separate smoke class.
- Post-implementation critique (tip `4b5d8f6b`) found **no blocking issues**. Non-blocking 1 (combined heal-then-opening path unexercised) was fixed by committing 艾拉's field heal and then opening/finishing the encounter in one fixture state. Non-blocking 2 (publication evidence narrower than the task wording) was dispositioned by strengthening the consumer coverage and accurately bounding the cross-process publication claim above; the smoke remains panel/text only and never substitutes for the original UI acceptance journey.
