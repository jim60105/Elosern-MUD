Apply on branch `feat/npc-persona-editor-browser-edges` in worktree `.worktrees/npc-persona-editor-browser-edges`. Run ONE browser test method per command with `uv run --locked python -m web.tests.browser.unittest_driver <module>.<Class>.<test>`, output captured to a scratch file; never chain whole files.

## 1. Fixtures

- [x] 1.1 Extend the editor seed fixture with a second NPC carrying an initialized card, a deterministic way to move the bound NPC out of and back into the actor's room, and a second activated character on the same account; verify the seed runs through the existing seed runner.

## 2. Edge journeys

- [x] 2.1 Write the four methods listed in proposal.md with bounded deterministic waits; run each method once locally in its own command; annotate each with the matching `webclient-npc-persona-editor` requirement ID from `uv run --locked python -m tools.spec_traceability list`.
- [x] 2.2 Register every new method in `.github/browser-shards.json`; verify `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` (with `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input) and `tests.test_webclient_frozen_contract`.

## 3. Gates

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-editor-browser-edges --strict`; record results.
