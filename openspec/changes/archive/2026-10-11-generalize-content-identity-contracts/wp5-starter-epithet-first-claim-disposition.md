# WP5 disposition: authored starter epithet and first-claim surfaces (tasks 5.1-5.4)

Baseline `master` = `9c3c14f7`; handover branch tip = `39c5a970`. This file
records what tasks 5.1-5.4 delivered, the one synthetic starter declaration and
every surface that consumes it, the assertion/metadata mapping, and the proof
that no behavior expectation pins the shipped starter spelling. It is evidence,
not a plan.

## 1. The declaration, the seam, and the one synthetic stand-in

The shipped `world/lore/titles.py::STARTER_EPITHET` (display `南門新客` plus its
authored origin basis) is **unchanged** and stays the sole display/origin
authority; the claim path banks whatever declaration sits on the
`world.lore.titles` seam at call time:

- `world/rules/titles/planner.py::grant_first_quest_epithet` does a
  function-local `from world.lore.titles import STARTER_EPITHET`, so
  `patch("world.lore.titles.STARTER_EPITHET", X)` is the actual seam. The name is
  also re-exported by `world/lore/__init__.py`, so a patched test must never
  import the constant through `world.lore` (that module-level binding would
  freeze the shipped object); every WP5 suite patches the `world.lore.titles`
  attribute.
- New shared synthetic declaration:
  `world/tests/synthetic_data/data_world.py::SYNTH_STARTER_EPITHET =
  StarterEpithet("苔徑新旅", "你在合成公會完成第一次任務回報。")`, exported
  through the kit package `__init__`. It is not a catalog mapping, so the kit's
  own `_catalog_maps()` self-test skips it; the kit's file-scan self-test
  (`world/tests/test_synthetic_data.py::test_kit_and_mirrors_are_gate_clean`,
  observed passing) is the collision backstop for its invented prose.

Consumers of that one declaration (all patch the same seam):

| Surface | File | Role |
| --- | --- | --- |
| Claim transaction | `world/rules/tests/test_guild_rewards.py` | synthetic-mechanism |
| CLI `guild turnin` | `commands/tests/test_guild_economy_commands.py` | representative-smoke |
| CLI `talk 回報` | `commands/tests/test_talk_turnin_commands.py` | representative-smoke |
| Webclient claim | `web/webclient/actions/tests/test_service_actions.py` | representative-smoke |
| 稱號 look line | `typeclasses/tests/test_appearance.py` | behavior consumer |
| NPC dialogue context | `typeclasses/tests/test_npc_dialogue.py` | behavior consumer |
| Nomination service | `server/conf/tests/test_title_nomination_service.py` | behavior consumer |

`world/rules/tests/test_titles/_support.py` and
`world/rules/tests/test_title_view.py` now alias `T_STARTER` to the same kit
declaration (previously their own identical literal), so every WP5 claim-surface
suite and both `T_STARTER` aliases share one synthetic starter value. Two
pre-existing local synthetic declarations are deliberately left as they are —
they already patched the same seam with invented prose and pin nothing shipped:
`web/webclient/presentation/tests/test_character_panel/_support.py`
(`StarterEpithet("苔徑新客", …)`, whose expectations derive from its own
constant) and the `_EPITHET` fixture entry in
`world/rules/tests/test_titles/_support.py`.

## 2. Task 5.1 — frozen declaration authority, banking, timing, dedupe, slots

`world/rules/tests/test_guild_rewards.py::RewardSettlementTests` patches the seam
in `setUp` and asserts the synthetic display/origin:

- `test_first_ever_claim_grants_the_starter_epithet` — notification
  `f"獲得異名：{SYNTH_STARTER_EPITHET.display}"`, composed full title, banked
  display **and** origin basis, auto-equipped epithet slot.
- `test_first_claim_banks_without_replacing_an_occupied_epithet_slot` (new) — a
  member who already adopted a nominated epithet before the first claim gets the
  starter banked while the occupied slot and composed title are unchanged
  (empty-slot-only auto-equip). Annotated
  `quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically`,
  the same id its four siblings carry.
- `test_later_claims_never_re_grant` — byte-identical `read_title_state` and an
  empty notification list.
- `test_rolled_back_first_claim_revokes_the_epithet` — injected affinity failure
  after the bank: raw `title_collection`/`title_equipped`, parsed state, composed
  title and empty claims list all equal their pre-turn-in values.
- `test_the_grant_is_definition_independent` — a non-`introductory_hunt` first
  claim grants the synthetic declaration identically.

`title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically`
keeps its grant-level epithet scenarios in
`world/rules/tests/test_titles/test_title_guild_pairing.py`, whose
`_starter()` already reads the patched seam; no annotation moved there.

## 3. Task 5.2 — the three claim surfaces

All three surfaces assert the committed first-claim state and the
prefix-plus-display notification built from the one synthetic declaration
(`f"獲得異名：{SYNTH_STARTER_EPITHET.display}"`); the prefix `獲得異名：` is the
code-side presentation grammar, the display after it is data:

| Surface | Assertion site | What is asserted |
| --- | --- | --- |
| CLI `guild turnin` | `test_guild_economy_commands.py::test_register_list_accept_turnin_flow` | claim output carries the prefix + synthetic display; the second claim stays title-silent |
| CLI `talk 回報` | `test_talk_turnin_commands.py::test_talk_turnin_with_quest_id_settles_once`, `::test_talk_turnin_later_claims_stay_title_silent` | same, on the dialogue keyword path |
| Webclient claim | `test_service_actions.py::test_turnin_echoes_the_first_claim_epithet_then_stays_silent` | last message is the prefix + synthetic display; a later claim emits no `獲得異名` |

The fixed guild title `F級冒險者` is untouched on every surface.

## 4. Task 5.3 — fixtures explicitly synthetic, source-data integrity, ledger roles

**(a) Source-data integrity without a literal.**
`world/lore/tests/test_titles_registry.py::test_starter_epithet_is_a_frozen_display_and_basis_pair`
now asserts the declaration is a frozen `StarterEpithet` whose display is
non-empty and within the enforced banking cap
(`world.rules.titles.MAX_EPITHET_DISPLAY_CODE_POINTS`) and whose origin basis is
non-empty and fits the codex basis window
(`world.rules.title_view.TITLE_MAX_BASIS_CHARS`), with the freeze still proven.
It is annotated `title-system::the-fixed-title-lore-registry-validates-and-syncs-idempotently`
(the requirement whose body names the constant). Its first docstring line, the
file's ledger `contract` reason and both ledgers are byte-unchanged.

**(b) Fixture text made explicitly synthetic.** The shipped display and its
paired fixture basis were replaced by `苔徑新客` / `初次走入苔徑。` in:

| File | Sites |
| --- | --- |
| `web/static/webclient/js/tests/protocol_title_codex.test.js` | epithet row, equipped slot, full title, normalized display, bad-key row |
| `web/static/webclient/js/tests/protocol_character.test.js` | optional full-title row |
| `web/static/webclient/js/tests/protocol_core.test.js` | status-panel full-title row |
| `web/webclient-app/stories/Overlays/TitleCodexPanel.stories.js` | epithet row, equipped slot, full title |
| `web/webclient-app/stories/fixtures/character_panels.js`, `status_panels.js` | titled samples |
| `web/webclient-app/tests/data/character_status_drawer.test.js` | two drawer expectations |
| `web/webclient-app/tests/overlays/title_codex_panel.test.js` | `T_EPITHET` + the equip payload |
| `web/webclient/presentation/tests/test_title_codex_panel.py` | `_T_EPITHET`/`_T_EPITHET_BASIS` fixtures + presenter expectations |
| `web/tests/browser/seed/titles_fixture.py`, `web/tests/browser/test_browser_title_codex.py` | the seeded epithet and its expectation |
| `world/ai/tests/test_npc_dialogue_prompts.py` | `_T_EPITHET`/`_T_FULL_TITLE` samples |
| `world/ai/tests/test_title_nomination.py` | `OWNED`, the context full title, collision/void samples |
| `world/rules/tests/test_titles/test_title_commit_rollback.py` | the paired basis string |

The browser seed fixture keeps its unregistered ledger state and now states in
its docstring that its epithets are explicitly synthetic fixture data, not the
shipped declaration.

**(c) Completion scan (the criterion is not enforced by any gate).** The lint
token universe does **not** contain `南門新客` (`STARTER_EPITHET` is a dataclass
instance, and `tools.test_data_lint.derive_universe` harvests catalog mapping
keys and display fields only — proven by the pre-existing unregistered seed
fixture carrying it at `violations=0`). The no-pinning criterion is therefore
enforced by this reproducible scan over the lint corpus roots
(`commands/ server/ typeclasses/ world/ web/ tests/ tools/tests/`), whose
observed result after WP5 is: `南門新客` occurs in exactly one file,
`world/lore/titles.py` (the declaration). No fixture basis residue
(`初入南門。`) remains either.

**(d) Ledger/seed metadata.** No WP5 file's classification or reason changes.
Every touched Python/JS test file already sits in `seedDebtPaths` (and
`world/ai/tests/test_npc_dialogue_prompts.py` stays `debt`, deliberately not
promoted to `contract`); `world/lore/tests/test_titles_registry.py` stays a
`contract` with its original reason; `web/tests/browser/seed/titles_fixture.py`
stays unregistered.
`tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` are
byte-identical to the handover tip.

## 5. Task 5.4 — documentation and mappings

- `docs/development/evennia-testing-guide.md` gains §稱號與啟始異名的資料擁有權
  inside the test-data-independence section: the declaration is the sole
  display/origin authority; the grant happens at the first guild reward claim
  (not registration) through the regular writer with dedupe, empty-slot-only
  auto-equip and transaction rollback; behavior tests patch the seam with
  `SYNTH_STARTER_EPITHET` and assert prefix + synthetic display; only data
  contract tests inspect the shipped declaration; no live banked epithet is
  renamed or re-granted.
- `docs/gm/quests.md` §設定公會任務板與報酬 states the first-ever reward claim's
  starter-epithet side effect with the same data ownership.
- This file is the assertion/metadata mapping: §1 names the declaration and its
  consumers, §2-§4 name each edited file, its role and its requirement ids.

## 6. Verification actually executed

| Command | Observed result |
| --- | --- |
| `uv run --locked python -m tools.test_data_lint check` | `scanned=1253 flagged=99 universe=1219+38 quantity-pins=10 violations=0` — byte-identical to the handover baseline |
| `uv run --locked python -m tools.spec_traceability check` | 2094 requirements, **8447** associations (handover: 8445), 2066 covered, 28 uncovered, **86** errors (handover: 86) — measured with a `git stash` probe of the clean tip; +2 associations from the two added annotations, no new error, and no WP5 file appears among the errors |
| `uv run --locked --env-file=<MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_rewards` | `Ran 35 tests ... OK` |
| same, `world.rules.tests.test_titles.test_title_guild_pairing test_title_state_collection test_title_state_surfaces` | `Ran 29 tests ... OK` |
| same, `world.rules.tests.test_title_view world.lore.tests.test_titles_registry` | `Ran 41 tests ... OK` |
| same, `world.tests.test_synthetic_data` | `Ran 25 tests ... OK` |
| same, `commands.tests.test_guild_economy_commands commands.tests.test_talk_turnin_commands` | `Ran 34 tests ... OK` |
| same, `web.webclient.actions.tests.test_service_actions` | `Ran 46 tests ... OK` |
| same, `typeclasses.tests.test_appearance` | `Ran 45 tests ... OK` |
| same, `typeclasses.tests.test_npc_dialogue` | `Ran 54 tests ... OK` |
| same, `server.conf.tests.test_title_nomination_service` | `Ran 18 tests ... OK` |
| same, `world.ai.tests.test_npc_dialogue_prompts world.ai.tests.test_title_nomination` | `Ran 53 tests ... OK` |
| same, `web.webclient.presentation.tests.test_title_codex_panel` | `Ran 18 tests ... OK` |
| same, `world.rules.tests.test_titles.test_title_commit_rollback test_title_planner test_title_predicates test_epithet_nomination_rules test_epithet_removal_rules` | `Ran 58 tests ... OK` |
| `node --test web/static/webclient/js/tests/protocol_title_codex.test.js protocol_character.test.js protocol_core.test.js` | `tests 36 / pass 36 / fail 0` |
| `npx --no-install vitest run web/webclient-app/tests/overlays/title_codex_panel.test.js web/webclient-app/tests/data/character_status_drawer.test.js` | `Test Files 2 passed (2)`, `Tests 41 passed (41)` |
| `uv run --locked --env-file=<MUD_TEST_SETTINGS=1> python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_title_codex` | `Ran 3 tests in 117.244s ... OK` — the one-class browser budget run. Prerequisite observed: the gitignored Vite bundle `web/static/webclient/app/dist/` must exist (`pnpm build`); the first attempt (without it) failed inside `wait_for_shell_active` with `connected: False` before any codex assertion, i.e. a checkout precondition, not a WP5 expectation |
| `uv run --locked python -m tools.contract_gate` | observability `violations=0`, test-data `violations=0`, manifests OK, contracts `Ran 18 tests ... OK`; the gate fails only on traceability with the unchanged 86 pre-sync errors (the change's own new ids plus the five WP3 bestiary `dynamic-requirement-id` sites WP7 owns); no WP5 file appears among them |
| `openspec validate generalize-content-identity-contracts --strict` | `Change 'generalize-content-identity-contracts' is valid` |
| `openspec validate --all --strict` / `--specs --strict` | `315 passed, 3 failed (318 items)` (the three unchanged deferred monster proposals) / `312 passed, 0 failed (312 items)`; WP5 edited no spec file, so neither total moved by this package |
| `git diff --check` | clean |

456 focused Python tests, 36 Node protocol tests, 41 Vitest tests and the
3-test browser journey were actually executed; the integrated Python/JS/browser
and metadata gates remain WP7's.

## 7. Retained contracts (untouched)

The clergy ladder (`c_believer`…`c_cardinal`) and its content test, the fixed
guild-rank title `F級冒險者` and the rank pairing, the six title category tabs
(`TITLE_CODEX_CATEGORIES` and the Python mirror) and `compose_title` /
`_assert_slot_invariant` / the panel validators keep their spec statements,
their ids and their assertions. WP5 edited no delta spec, no main spec, no
`openspec/specs/` file, no deferred proposal and no `exploration-*` change, and
no requirement statement.

## 8. Delta-spec deviations

None. No requirement was renamed, removed or reworded; every annotation WP5
added asserts a scenario its target requirement already states, and both target
ids already existed in the main specs, so `openspec validate` totals are
unaffected by this package.

## 9. Left to a later package

- **WP7**: run the integrated Python/JS/browser and metadata/test-data gates and
  produce the zero-stale-id conclusion; the pre-sync `unknown-requirement-id`
  errors of the change's own new ids resolve when the delta is applied/archived.
- **WP6**: untouched by this package (equipment/shop membership).
- The shipped `STARTER_EPITHET` display/origin spelling is deliberately **not**
  edited anywhere; a future authoring change to that value needs no test edit,
  which is the point of this cutover.

## 10. Independent review dispositions

**Plan-stage critique (blocking pass, verdict `adjust`) — all three blocking
findings adopted:**

1. *The lint gate does not contain `南門新客`, so the no-pinning criterion needs
   its own scan.* Adopted: the migration is anchored on the verified per-file
   corpus scan (§4c) rather than on the gate, and the completion scan is part of
   the record.
2. *The new occupied-slot test was mapped to the wrong requirement id.* Adopted:
   it carries
   `quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically`,
   not the title-system paired-titles id.
3. *`world/lore/__init__.py` re-exports `STARTER_EPITHET`, and the
   `test_service_actions.py` rename needed an explicit resolution.* Adopted: §1
   records that the seam is the `world.lore.titles` attribute, patched tests
   never import the constant through `world.lore`, and
   `test_service_actions.py` keeps `_T_STARTER_EPITHET = SYNTH_STARTER_EPITHET`
   so every downstream `._T_STARTER_EPITHET` reference resolves.

Non-blocking findings adopted: unify the two Python behavior-test spellings onto
the kit declaration (§1); phrase the registry bounds as the enforced banking cap
plus the codex window (§4a); replace the paired fixture basis, not only the
display (§4b); record the prefix-plus-display notification contract (§3); leave
the clergy/six-tab/dedupe tests untouched (§7); do not prune `seedDebtPaths`
(§4d). Rejected: none.

**Post-implementation critique (blocking pass, verdict `fix`, no blocking
findings) — both non-blocking findings dispositioned:**

1. *Overstated unification.* Adopted: §1 now scopes the whole-value unification
   to the WP5 claim-surface suites and the two `T_STARTER` aliases, and names the
   two pre-existing local synthetic declarations it does not move. Both files
   keep patching the correct `world.lore.titles` seam with invented prose, so no
   behavior expectation pins the shipped spelling and no future authoring edit
   of `STARTER_EPITHET` breaks them; no code change was needed.
2. *Alleged residual fixture basis at `test_title_commit_rollback.py:150`.*
   **Rejected with evidence, not because the fix was hard:** the tree at HEAD
   contains zero occurrences of the shipped-era basis. A scan of the seven lint
   corpus roots for `初入南門` returns no hits, and for `南門新客` returns only
   `world/lore/titles.py:129`; line 150 of that file reads
   `bank_epithet(self.actor, _starter().display, "初次走入苔徑。", 1)`. The
   finding described the pre-change revision.

The reviewer independently re-checked §4c's scan result, the lint-universe
explanation, the touched files' `seedDebtPaths` membership, the registry test's
constant pair and annotation, and the quest/testing-guide prose, and confirmed
every one of them, so the §6-recorded claims stand unchanged.
