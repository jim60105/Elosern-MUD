# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`.

## 1. Write points

- [ ] 1.1 Add the look hook (design 1) and the talk calls (design 2). Verify by 2.1.
- [ ] 1.2 Add the service calls (design 3) and the invite calls (design 4). Verify by 2.1.

## 2. Tests

- [ ] 2.1 Add integration tests, one per ADDED scenario, in `world/rules/tests/test_met_people.py` (using the real adapters through the action dispatcher test helpers and the real commands with `EvenniaCommandTest` where the scenario names the text path), decorated with the requirement ID; the invite test uses the offline/degraded dialogue client already used by the invite adapter tests. Verify `<prefix> world.rules.tests.test_met_people` and the existing talk/look/invite/service adapter test modules (`rg -ln "explore.talk_open|explore.party_invite|shop.buy" web/webclient/actions/tests`) pass.

## 3. Gates

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate --change met-person-write-points`; all pass.
- [ ] 3.2 Run `openspec validate met-person-write-points --strict`; it passes.
