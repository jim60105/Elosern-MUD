## 1. Objective data and validation

- [x] 1.1 Extend `world/quests/definitions.py`: `QuestObjective` gains `region_key`/`species_key`/`countable_variant_keys` (legal only together, mutually exclusive with the tier/bound selectors, at least one ordinary variant among countables), registration validates region/species/variant registry membership and ownership with `QuestDefinitionError`, and `QuestDefinition` gains bounded zh-TW `rating_rationale_zh` and `background_flavor_zh` fields — all synthetic-fixture tests: valid hunt registers immutably, foreign variant key rejected, two-selector reject, name-not-key reject, grade/rationale/flavor kept separate with danger grade never overriding rank and flavor never completing a quest

## 2. Planner matching

- [x] 2.1 Extend `world/quests/planner.py` `_matching_defeats` to evaluate the species-hunt selector from the defeat entry's species/variant keys plus the individual's location resolved to the declared region at defeat time, counting each persistent identity once (on top of the landed dedupe) and never matching tier-only or unlisted-variant kills, and verify with planner tests: stronger variant counts once, unlisted variant/outside-region/tier-only never count, ordinary-only completion suffices

## 3. Acceptance provisioning

- [x] 3.1 Implement the acceptance-time target guarantee: the deterministic acceptance path calls the ambient/site managers' ensure API with (region, species, ordinary-eligible variants, needed count); managers decide within capacity/ownership/site state, never rebuilding eligible individuals or early-recovering cleared sites; guarantee + provisioning + record (+ board-path affinity) commit in one `transaction.atomic()`, refusal is a named reason with zero partial state, and verify: guarantee-satisfied accept creates nothing, shortfall provisioning through the owner only, illegal hunt refused with database before/after equality (quest log, affinity, every manager-owned individual)
- [x] 3.2 Extend `world/quests/describe.py` and the board one-liner to render the hunt selector deterministically (region/species/count/countable variants, stable order), render grade/rationale/flavor as three sections in `guild show` with omission for absent fields, unknown kinds still raising, and verify the quest-detail and board tests plus a read-only-state assertion
- [x] 3.3 Update the compile/payload validators for the new stored objective and prose fields so a corrupt payload fails loudly, and verify round-trip restore equality plus rejection of malformed stored hunts

## 4. Player-visible surface and docs

- [x] 4.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the `guild show` / `guild list` output gains (new rendered sections and one-liner form; no new keys/aliases/syntax) and keep `tests/test_command_docs.py` green

## 5. Verification

- [x] 5.1 Register new test modules in exactly one shard of `.github/evennia-shards.json`; run focused quest tests (`definitions`, `acquire`/lifecycle, `planner`, `describe`, board), `tools.test_data_lint check` (synthetic species only, bestiary names absent from behavior tests), `uv run --locked python -m tools.contract_gate`, and the observability lint for changed modules
