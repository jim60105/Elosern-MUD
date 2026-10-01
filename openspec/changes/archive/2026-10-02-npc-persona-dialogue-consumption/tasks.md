Apply on branch `feat/npc-persona-dialogue-consumption` in worktree `.worktrees/npc-persona-dialogue-consumption`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file. Every test uses synthetic profiles and `FakeLLMClient`; no live model.

## 1. Prompt consumption

- [x] 1.1 Switch `NPC_PERSONA_FIELDS` to the card render order, add `npc_dialogue.persona_frame` to `prompts/npc_dialogue.yaml` and `world/prompts/registry.py` (allowlist `block`), and render it per design D1; verify in `world/ai/tests/` and `world/prompts/tests/`: speech style follows personality, hidden identity present, no truncation for a boundary card, frame present only with a card, byte-identical system message without persona, and the player block unchanged (public-only).

## 2. Voice routing

- [x] 2.1 Add the `provenance_profile_key` read-only helper to `world/rules/npc_persona.py` (design D2) with tests that malformed metadata yields `None` and nothing is written.
- [x] 2.2 Implement `misunderstood_line_for` / `offline_greeting_for` and route unknown keywords, the degraded branch, the `commands/talk.py` no-keyword branch, and the `_talk_open_adapter` session line per design D3, including the `db.npc_offline_greeting` field ahead of the table and profile lookups; verify in `world/rules/tests/test_dialogue.py`, `typeclasses/tests/` and `webclient/actions/tests/` (the field written directly on the test NPC, no dependency on the companion builder): profiled host's own misunderstanding line, unprofiled host's shared line, dangling key emits `npc_voice_profile_missing` and returns the shared line, field greeting wins over a synthetic profile greeting and speaks without profile resolution, offline greeting from the profile when the field is empty, silence without any of the three, card edits not changing any scripted line, a `talk <NPC>` with no keyword and an `explore.talk_open` both opening with the field text over a table greeting, and `explore.talk_open` still falling to the fixed fallback line when nothing resolves.

## 3. Gates

- [x] 3.1 Add the event to the observability catalog and run `uv run --locked python -m tools.observability_lint check` in the same batch as the focused labels; `tools/observability_freeze.json` unchanged.
- [x] 3.2 Confirm shard ownership with `tests.test_evennia_test_optimization_contract` (register any new `world/rules/tests` module in exactly one rules shard; other touched packages are package-owned); sync the deltas (`persona-dialogue-injection`, `scripted-dialogue`, `npc-dialogue`, `webclient-exploration-menu`, `prompt-library`) into `openspec/specs/`, annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.test_data_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-dialogue-consumption --strict`.
