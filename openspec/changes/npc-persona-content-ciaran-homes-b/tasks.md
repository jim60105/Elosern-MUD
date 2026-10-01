Apply on branch `feat/npc-persona-content-ciaran-homes-b` in worktree `.worktrees/npc-persona-content-ciaran-homes-b`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Inventory and grounding

- [ ] 1.1 Confirm the foundation inventory rows owned by `ciaran_homes_b` equal the sources listed in design.md, and record each host's grounding facts (place row, settlement-document passage, spec requirements, what each keyword currently teaches) as a short brief in this task's completion note; verify the brief covers every host and every keyword.
- [ ] 1.2 Capture SHA-256 digests of every current greeting and response of the owned tables (from the pre-change file) for the D4 test, and `rg` each line's distinctive phrases across `world`, `web`, `commands`, and `tests` to list every test that pins the provisional prose; verify the list is recorded in this task's note.

## 2. Author cards and references

- [ ] 2.1 Author the 4 host profiles in `world/lore/npc_profiles/ciaran_homes_b.py` per design D2 (complete card, `misunderstood` line, `greeting=None`); verify `uv run --locked python -c "import world.lore.npc_profiles"` succeeds (the registry validates every card at import).
- [ ] 2.2 Set `host_profile_key` on the 4 owned rows in `world/lore/settlements/places_ciaran.py`; verify `world.lore.tests.test_settlements` passes.

## 3. Rewrite dialogue and tests

- [ ] 3.1 Rewrite the greeting and all keyword responses of the 4 owned tables in `world/lore/dialogue/ciaran.py` per design D1/D3; verify the labels `world.lore.tests.test_settlements`, `world.lore.tests.test_shops`, `world.rules.tests.test_dialogue`, `world.rules.tests.test_guild_config.test_service_host_roster`, `world.rules.tests.test_guild_config.test_item_offer_definitions` each pass in its own command.
- [ ] 3.2 Convert every incidental exact-wording assertion found in task 1.2 into a behavior assertion (topic present, command named, no state change) or delete it when it only echoed prose; keep contract-pinned substrings; verify the affected labels pass and no browser test file is left asserting a removed line (`rg` the old phrases again, expecting no hit outside the digest test).
- [ ] 3.3 Add `world/lore/tests/test_npc_profiles_ciaran_homes_b.py` implementing design D4 as a data-contract test, register it in `tools/test_data_freeze.json`; verify the label passes and `uv run --locked python -m tools.test_data_lint check` is clean.

## 4. Editorial review

- [ ] 4.1 Review every card and line against the grounding briefs and the settlement facts, and review same-profession hosts side by side (greeting and one shared-topic response each); record findings and fixes in this task's completion note. If an approved dialogue model is configured, record one representative free-form prompt/reply per host built from the new card; otherwise state explicitly that no model-output review was performed.

## 5. Gates and handoff

- [ ] 5.1 Confirm no shard edit is needed (the new module is owned by the `world.lore` package label; listing it would double-own it); verify with `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.2 If `npc-profile-registry` is already a main capability, sync this change's ADDED requirement into `openspec/specs/npc-profile-registry/spec.md` and annotate the D4 test with the literal ID from `uv run --locked python -m tools.spec_traceability list`; otherwise leave it unannotated for the archive workflow. Verify `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.3 Run `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-content-ciaran-homes-b --strict`; record the results.
