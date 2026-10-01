Apply on branch `feat/npc-persona-content-altoria-upper` in worktree `.worktrees/npc-persona-content-altoria-upper`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Inventory and grounding

- [ ] 1.1 Confirm the `npc-persona-profile-registry` inventory rows owned by `altoria_upper` equal the sources listed in design.md, and record each host's grounding facts (place row, settlement-document passage, spec requirements, what each keyword currently teaches) as a short brief in this task's completion note; verify the brief covers every host and every keyword.
- [ ] 1.2 `rg` each current line's distinctive phrases across `world`, `web`, `commands`, and `tests` to list every test that pins the provisional prose; verify the list is recorded in this task's note.

## 2. Author cards and references

- [ ] 2.1 Author the 5 host profiles in `world/lore/npc_profiles/altoria_upper.py` per design D2 (complete card, `misunderstood` line, `greeting=None`); verify `uv run --locked python -c "import world.lore.npc_profiles"` succeeds (the registry validates every card at import).
- [ ] 2.2 Set `host_profile_key` on the 5 owned rows in `world/lore/settlements/places_altoria_upper.py`; verify `world.lore.tests.test_settlements` passes.

## 3. Rewrite dialogue and tests

- [ ] 3.1 Rewrite the greeting and all keyword responses of the 5 owned tables in `world/lore/dialogue/altoria_upper.py` per design D1/D3/D5 (in character, no command token; formal for the priestess, captain and dean, colloquial for the deacon and instructor); verify the labels `world.lore.tests.test_settlements`, `world.lore.tests.test_church`, `world.lore.tests.test_shops`, `world.rules.tests.test_dialogue`, `world.rules.tests.test_guild_economy_sync.test_church_hosts`, `world.rules.tests.test_guild_config.test_service_host_roster` each pass in its own command.
- [ ] 3.2 Remove every test assertion that pins NPC prose per design D4: delete `test_dialogue_assembly`'s pre-split content digests (keeping a prose-free four-answer shape check), and replace the exact-word pins in `test_altoria_crown_watch` (instructor), `test_altoria_learning_exchange` (dean) and `test_altoria_sanctum` (deacon must quote a trade command) with no-backticked-token assertions, keeping every registry-derived substance check; verify those labels plus `test_service_host_merchant_dialogue` pass and no test or browser test is left asserting a removed line (`rg` the old phrases again, expecting no hit).
- [ ] 3.3 Add no new test module (design D4). Set the owned pinned place tuples in `test_settlements` to their new `host_profile_key`, move the shipped-registry immutability check from `test_npc_profiles` into the `test_npc_profile_inventory` data contract, and resolve the guild-economy test support's service ids by place kind (identical hunks across the content slices); verify the labels pass and `uv run --locked python -m tools.test_data_lint check` is clean.

## 4. Editorial review

- [ ] 4.1 Review every card and line against the grounding briefs and the settlement facts, and review same-profession hosts side by side (greeting and one shared-topic response each); record findings and fixes in this task's completion note. If an approved dialogue model is configured, record one representative free-form prompt/reply per host built from the new card; otherwise state explicitly that no model-output review was performed.

## 5. Gates and handoff

- [ ] 5.1 Confirm no shard edit is needed (no test module is added); verify with `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- [ ] 5.2 If `npc-profile-registry` is already a main capability, sync this change's ADDED requirement into `openspec/specs/npc-profile-registry/spec.md` and annotate the covering place-registry validation test with the literal ID from `uv run --locked python -m tools.spec_traceability list`; otherwise leave it unannotated for the archive workflow. Verify `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.3 Run `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-content-altoria-upper --strict`; record the results.
