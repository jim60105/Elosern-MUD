# Tasks

Total estimate: **4.5 hours**, including implementation, focused verification, documentation and integration. Prerequisites and conflicts are in proposal.md.

## 1. Commander and member resolution (2h)

- [ ] 1.1 Add `world/rules/party_scope.py` with `PartyScopeError`, the three codes, `PARTY_SCOPE_MESSAGES`, `resolve_commander`, and `authorize_member(commander, member_id, purpose, anchor)`; verify with `world/rules/tests/test_party_scope.py` cases for player commander, possessed commander, non-player non-possessed rejection, non-member NPC, deleted dbid, boolean/str ids, absent member, knocked-out `act` rejection and `organize` admission, and an unchanged attribute snapshot after every rejection.

## 2. Scope and text token (1.5h)

- [ ] 2.1 Add `present_party_scope(acting)` and `resolve_member_token(acting, token)`; verify ordering (acting, commander, roster order), different-room exclusion, possession ordering, de-duplication, exact-name match, ambiguous and unknown tokens rejected without caller fallback.

## 3. Integration (1h)

- [ ] 3.1 Register the new test module in exactly one shard of `.github/evennia-shards.json` and verify `tests.test_evennia_test_optimization_contract` passes with `--env-file=<file containing MUD_TEST_SETTINGS=1>`.
- [ ] 3.2 Annotate the tests with `covers_requirement` IDs for every `party-member-authority` requirement (IDs from `uv run --locked python -m tools.spec_traceability list` once synced; record the intended IDs in the test docstrings until then), run `uv run --locked python -m tools.contract_gate` and `openspec validate party-member-authority --strict`.
