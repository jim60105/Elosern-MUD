# Tasks

Total estimate: **5 hours**, including implementation, focused verification, documentation and integration. Prerequisites and conflicts are in proposal.md.

## 1. Commander and member resolution (2h)

- [ ] 1.1 Add `world/rules/party_scope.py` with `PartyScopeError`, the three codes, `PARTY_SCOPE_MESSAGES`, `resolve_commander`, and `authorize_member(commander, member_id, purpose, anchor)`; verify with `world/rules/tests/test_party_scope.py` cases for player commander, possessed commander, non-player non-possessed rejection, non-member NPC, deleted dbid, boolean/str ids, absent member, knocked-out `act` rejection and `organize` admission, and an unchanged attribute snapshot after every rejection.

## 2. Scope, text token and guards (2h)

- [ ] 2.1 Add `present_party_scope(acting)` and `resolve_member_token(acting, token)`; verify ordering (commander, roster order), exclusion of a member left elsewhere by a failed follow, identical scope with and without possession, de-duplication, exact-name match, ambiguous and unknown tokens rejected without caller fallback.
- [ ] 2.2 Add `party_in_combat(acting, *members)` and the live-puppet requirement in `resolve_commander`; verify a possessed figure in a session bars the request while the commander body is out of combat, and a flagged but unpuppeted NPC is rejected.

## 3. Integration (1h)

- [ ] 3.1 Register the new test module in exactly one shard of `.github/evennia-shards.json` and verify `tests.test_evennia_test_optimization_contract` passes with `--env-file=<file containing MUD_TEST_SETTINGS=1>`.
- [ ] 3.2 Annotate the tests with `covers_requirement` IDs for every `party-member-authority` requirement (IDs from `uv run --locked python -m tools.spec_traceability list` once synced; record the intended IDs in the test docstrings until then), run `uv run --locked python -m tools.contract_gate` and `openspec validate party-member-authority --strict`.
