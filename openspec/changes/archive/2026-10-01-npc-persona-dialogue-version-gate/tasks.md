Apply on branch `feat/npc-persona-dialogue-version-gate` in worktree `.worktrees/npc-persona-dialogue-version-gate`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. Tests use synthetic cards written through the persona service and `FakeLLMClient`; no live model.

## 1. Gate

- [x] 1.1 Add `current_persona_version` to `world/rules/npc_persona.py` (design D1) with tests that malformed metadata yields `None` and nothing is written.
- [x] 1.2 Implement design D2 in `typeclasses/npcs.py` and `world/rules/player_messages.py`; verify with `twisted.internet.task.Clock`-driven tests in `typeclasses/tests/`: one-leaf edit mid-flight, change-and-revert mid-flight, no-op save mid-flight (still presents and applies), degraded-then-stale, thinking timer cancelled, no second client call, player line kept and no NPC line appended.
- [x] 1.3 Map the stale outcome in `_talk_freeform_adapter`, `_party_invite_adapter`/`_render_invite_outcome`, and `commands/invite.py`; verify in `web/webclient/actions/tests/` and `commands/tests/`: rejected `stale_persona` result with no session refresh, invite with no join/refusal/threshold, text `invite` prints the explanation, and the existing separated-context tests stay green.

## 2. Gates

- [x] 2.1 Add the event to the observability catalog and run `uv run --locked python -m tools.observability_lint check` in the same batch as the focused labels; `tools/observability_freeze.json` unchanged.
- [x] 2.2 Confirm shard ownership with `tests.test_evennia_test_optimization_contract`; sync the ADDED `npc-dialogue` requirement into `openspec/specs/`, annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-dialogue-version-gate --strict`.
