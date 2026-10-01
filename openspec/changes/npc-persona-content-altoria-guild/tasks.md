Apply on branch `feat/npc-persona-content-altoria-guild` in worktree `.worktrees/npc-persona-content-altoria-guild`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Inventory and grounding

- [ ] 1.1 Confirm the foundation inventory rows owned by `altoria_guild` equal the sources listed in design.md, and record each host's grounding facts (place row, settlement-document passage, spec requirements, what each keyword currently teaches) as a short brief in this task's completion note; verify the brief covers every host and examiner and every keyword.
- [ ] 1.2 Capture SHA-256 digests of every current greeting and response of the owned tables (from the pre-change file) for the D4 test, and `rg` each line's distinctive phrases across `world`, `web`, `commands`, and `tests` to list every test that pins the provisional prose; verify the list is recorded in this task's note.

## 2. Author cards and references

- [ ] 2.1 Author the host profile in `world/lore/npc_profiles/altoria_guild.py` per design D2 (complete card, `misunderstood` line, `greeting=None`); verify `uv run --locked python -c "import world.lore.npc_profiles"` succeeds (the registry validates every card at import).
- [ ] 2.2 Set `host_profile_key` on the owned guild-hall row in `world/lore/settlements/places_altoria_middle.py`; verify `world.lore.tests.test_settlements` passes.
- [ ] 2.3 Author the seven examiner profiles in the same slice module, add the required `examiner_profile_key` to every `GuildRank` row in `world/lore/guild.py`, and extend `validate_guild_npc_identities` to reject an unresolved key naming the rank; verify with a synthetic-rank rejection test in `world/lore/tests/test_guild.py` and `world.lore.tests.test_guild` green.

## 3. Rewrite dialogue and tests

- [ ] 3.1 Rewrite the greeting and all keyword responses of the owned `guild_staff` table in `world/lore/dialogue/guild.py` per design D1/D3; verify the labels `world.rules.tests.test_dialogue`, `world.rules.tests.test_guild_dialogue_turnin`, `world.lore.tests.test_guild`, `world.lore.tests.test_settlements`, `commands.tests.test_talk_turnin_commands`, `commands.tests.test_talk_turnin_branch`, `web.webclient.presentation.tests.test_dialogue_panel` each pass in its own command.
- [ ] 3.2 Convert every incidental exact-wording assertion found in task 1.2 into a behavior assertion (topic present, command named, no state change) or delete it when it only echoed prose; keep contract-pinned substrings; verify the affected labels pass and no browser test file is left asserting a removed line (`rg` the old phrases again, expecting no hit outside the digest test).
- [ ] 3.3 Add `world/lore/tests/test_npc_profiles_altoria_guild.py` implementing design D4 as a data-contract test, register it in `tools/test_data_freeze.json`; verify the label passes and `uv run --locked python -m tools.test_data_lint check` is clean.

## 4. Editorial review

- [ ] 4.1 Review every card and line against the grounding briefs and the settlement facts, and review the seven examiners side by side against each other and against the branch master; record findings and fixes in this task's completion note. If an approved dialogue model is configured, record one representative free-form prompt/reply per host built from the new card; otherwise state explicitly that no model-output review was performed.

## 5. Gates and handoff

- [ ] 5.1 Confirm no shard edit is needed (the new module is owned by the `world.lore` package label; listing it would double-own it); verify with `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.2 If `npc-profile-registry` is already a main capability, sync this change's ADDED requirement into `openspec/specs/npc-profile-registry/spec.md` and annotate the D4 test with the literal ID from `uv run --locked python -m tools.spec_traceability list`; otherwise leave it unannotated for the archive workflow. Verify `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.3 Run `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-content-altoria-guild --strict`; record the results.
