# Tasks

Read `design.md` first. Every code block named below is in it.

Rules that hold for every task:

- Edit test files only. Touch no runtime code, lore data, rulebook or file under `openspec/specs/`.
- Add no test. Append no key, name or number to any assertion.
- Keep every `@covers_requirement` decorator on the method it decorates, including on renamed methods.
- Run every Evennia test command alone, exactly as written, with nothing before or after it. If the test guard refuses a command for discovering more than 100 tests, run its labels as separate commands.

## 1. Baseline

- [x] 1.1 Run `git status`. Then run the four commands of group 4 once before editing anything. Verify each ends with `OK`; record any failure in the working notes as a pre-existing failure and do not fix it here.

## 2. Confirm the replacements equal the literals today

- [x] 2.1 Run `uv run --locked python -c "from world.lore.dialogue import DIALOGUE_SNAPSHOT as D; from world.lore.settlements.places import PLACE_REGISTRY as P, place_dialogue_keys as k, place_shop_identity as s; print(len(D), len({x for p in P.values() for x in k(p)}), len([1 for p in P.values() if s(p)]))"`. Verify by recording the three numbers in the working notes; the first two must be equal. These are the values the literals 25, 25 and 13 stand for today.

## 3. Rewrites

- [x] 3.1 Apply design Decision 1 to `world/lore/tests/test_dialogue_assembly.py`.
- [x] 3.2 Apply design Decision 2 to `world/rules/tests/test_dialogue_sources.py`.
- [x] 3.3 Apply design Decision 3 to `world/rules/tests/test_guild_economy_sync/test_service_host_identity.py`.
- [x] 3.4 Apply design Decision 4 to `world/rules/tests/test_guild_economy_sync/test_service_host_merchant_dialogue.py`.
- [x] 3.5 Apply design Decision 5 to `world/rules/tests/test_guild_economy_sync/_support.py` and `test_ciaran_village_commerce.py`. Verify with `grep -rn "_village_subrace_key\b" world` printing nothing.
- [x] 3.6 Apply design Decisions 6 and 7 to `world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py`.
- [x] 3.7 Apply design Decision 8 to `world/lore/tests/test_shops.py`.
- [x] 3.8 Apply design Decision 9. Verify the grep it names prints no line outside `openspec/changes/`.
- [x] 3.9 Verify the pins are gone: `grep -n "assertEqual(len(DIALOGUE_SNAPSHOT), 25)\|assertEqual(len(bindings), 25)\|assertEqual(len(events), 25)\|assertEqual(len(late), 25)\|assertEqual(len(places), 13\|assertEqual(len(attendants), 2)" world/lore/tests/test_dialogue_assembly.py world/rules/tests/test_dialogue_sources.py world/rules/tests/test_guild_economy_sync/*.py` prints nothing. Verify with `git diff --stat` that only test files changed.

## 4. Tests

- [x] 4.1 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_dialogue_assembly world.lore.tests.test_shops world.rules.tests.test_dialogue_sources`. Verify it ends with `OK`.
- [x] 4.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync.test_service_host_identity`. Verify it ends with `OK`.
- [x] 4.3 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync.test_service_host_merchant_dialogue`. Verify it ends with `OK`.
- [x] 4.4 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync.test_ciaran_village_commerce`. Verify it ends with `OK`.
- [x] 4.5 If a test fails after the edits and passed in 1.1, the rewrite is wrong: compare it with the design block and fix the rewrite. Do not restore a literal.

## 5. Integration

- [x] 5.1 Run `uv run --locked python -m tools.contract_gate`. Verify it ends with `contract gate passed`.
- [x] 5.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.spec_traceability check`. Verify both exit 0. If either names a renamed method, update the entry it reads to the new name and rerun.
- [x] 5.3 Run `openspec validate unpin-village-test-data --strict`. Verify it reports the change valid.
