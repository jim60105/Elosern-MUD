# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Write points

- [x] 1.1 Add the look hook (design 1) and the talk calls (design 2). Verify by 2.1.
- [x] 1.2 Add the service calls (design 3) and the invite calls (design 4). Verify by 2.1.

## 2. Tests

- [x] 2.1 Add integration tests, one per ADDED scenario, in `world/rules/tests/test_met_people.py` (using the real adapters and the real commands with `EvenniaCommandTest` where the scenario names the text path), covering both transports for look and talk; the invite test uses the offline/degraded dialogue client already used by the invite adapter tests. The ADDED requirement has no canonical ID before archive sync, so the tests stay unannotated until then (`docs/development/spec-test-traceability.md`), and the change report carries the test → requirement/scenario hand-off. Verify `<prefix> world.rules.tests.test_met_people` and the existing talk/look/invite/service adapter test modules (`rg -ln "explore.talk_open|explore.party_invite|shop.buy" web/webclient/actions/tests`) pass.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change met-person-write-points`; all pass.
- [x] 3.2 Run `openspec validate met-person-write-points --strict`; it passes.
