Apply on branch `feat/npc-persona-dialogue-consumption` in worktree `.worktrees/npc-persona-dialogue-consumption`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. Every test uses synthetic profiles and `FakeLLMClient`; no live model.

## 1. Prompt consumption

- [ ] 1.1 Switch `NPC_PERSONA_FIELDS` to the card render order, add `npc_dialogue.persona_frame` to `prompts/npc_dialogue.yaml` and `world/prompts/registry.py` (allowlist `block`), and render it per design D1; verify in `world/ai/tests/` and `world/prompts/tests/`: speech style follows personality, hidden identity present, no truncation for a boundary card, frame present only with a card, byte-identical system message without persona, and the player block unchanged (public-only).

## 2. Voice routing

- [ ] 2.1 Add `current_persona_version` and `provenance_profile_key` read-only helpers to `world/rules/npc_persona.py` (design D2) with tests that malformed metadata yields `None` and nothing is written.
- [ ] 2.2 Implement `misunderstood_line_for` / `offline_greeting_for` and route unknown keywords and the degraded branch per design D4; verify in `world/rules/tests/test_dialogue.py` and `typeclasses/tests/`: profiled host's own misunderstanding line, unprofiled host's shared line, dangling key emits `npc_voice_profile_missing` and returns the shared line, offline companion greeting from profile, silence without either, and card edits not changing any scripted line; `explore.talk_open` tests unchanged and green.

## 3. Persona-version completion gate

- [ ] 3.1 Implement design D3 in `typeclasses/npcs.py` (`stale_persona` result, no NPC memory append, sentinel) and `world/rules/player_messages.py` (explanation); verify with `twisted.internet.task.Clock`-driven tests: one-leaf edit mid-flight, change-and-revert mid-flight, no-op save mid-flight (still applies), degraded-then-stale, thinking timer cancelled, no second client call.
- [ ] 3.2 Map the stale outcome in `_talk_freeform_adapter`, `_party_invite_adapter`/`_render_invite_outcome`, and `commands/invite.py`; verify in `web/webclient/actions/tests/` and `commands/tests/`: rejected `stale_persona` result with no session refresh, invite with no join/refusal/threshold, text `invite` prints the explanation, and the existing separated-context tests stay green.

## 4. Gates

- [ ] 4.1 Add the two events to the observability catalog and run `uv run --locked python -m tools.observability_lint check` in the same batch as the focused labels; `tools/observability_freeze.json` unchanged.
- [ ] 4.2 Confirm shard ownership with `tests.test_evennia_test_optimization_contract` (register any new `world/rules/tests` module in exactly one rules shard; other touched packages are package-owned); sync the deltas (`persona-dialogue-injection`, `scripted-dialogue`, `npc-dialogue`, `prompt-library`) into `openspec/specs/`, annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.test_data_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-dialogue-consumption --strict`.
