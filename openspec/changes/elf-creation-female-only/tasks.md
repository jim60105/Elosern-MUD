# Tasks

Create the Evennia test env file once before the focused runs:
`printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-test-env`. Every `evennia test` step below uses that
single-token `--env-file=/tmp/mud-test-env` spelling (AGENTS.md rejects both the inline prefix and
the two-token form). Run only the focused labels named per task.

## 1. Registry: the race's permitted-sex declaration

- [x] 1.1 In `world/lore/races.py`, import `SEX_VALUES` from `world.lore.sex` and add
      `allowed_sexes: tuple[str, ...] = SEX_VALUES` as the last field of the frozen `RaceProfile`
      (after `display_name_zh`), with a comment naming it the permitted-sex set. Give
      `RACE_REGISTRY["elf"]` `allowed_sexes=("female",)`; leave `human` and `beastfolk` on the
      default. Do not touch `world/lore/sex.py`. Verify:
      `uv run --locked python -c "from world.lore.sex import SEX_VALUES; from world.lore.races import RACE_REGISTRY as R; print(R['elf'].allowed_sexes, R['human'].allowed_sexes == SEX_VALUES)"`
      prints `('female',) True`.
- [x] 1.2 In `world/lore/tests/test_races.py` add
      `test_every_race_declares_a_non_empty_sex_subset_and_the_elf_declares_only_female`, decorated
      with `@covers_requirement("lore-registries::raceprofile-encodes-the-three-race-power-gap")`,
      asserting every `allowed_sexes` is a non-empty tuple drawn from the live `SEX_VALUES`, that
      `SEX_VALUES` is still exactly `("female", "male", "other")`, that
      `RACE_REGISTRY["elf"].allowed_sexes` is exactly `("female",)`, and that `human`/`beastfolk`
      permit all three. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.lore.tests.test_races`.

## 2. The single rule seam

- [x] 2.1 Create `world/rules/identity.py` exactly as in design.md §Contracts (`IdentityError`,
      `permitted_sexes`, `resolve_sex`, `ensure_entity_sex`) with a module docstring stating it is
      the single implementation of the race-bounded sex rule and naming its callers. It imports only
      `world.lore.races` and `world.lore.sex`. Verify:
      `uv run --locked python -c "from world.rules.identity import resolve_sex as r; print(r('elf', None), r('human', None), r('human', 'male'))"`
      prints `female other male`, and
      `uv run --locked python -c "from world.rules.identity import resolve_sex as r; r('elf', 'male')"`
      exits non-zero with `sex 'male' is not available for race 'elf'`.
- [x] 2.2 Create `world/rules/tests/test_identity.py` (`unittest.TestCase` for the pure functions,
      `EvenniaTestCase` for the entity write) with these methods, all decorated
      `@covers_requirement("living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other")`:
      `test_an_omitted_sex_resolves_to_the_race_permitted_default` (`elf` → the sole member, a
      full-vocabulary race → `DEFAULT_SEX`, an unresolvable race key → `DEFAULT_SEX`),
      `test_a_forbidden_member_is_refused_and_a_permitted_one_is_kept`,
      `test_a_non_member_keeps_the_vocabulary_message`, and
      `test_ensure_entity_sex_writes_the_resolved_value` (an entity whose `.race` is the elf stand-in
      ends on its permitted member; a human entity with `sex="male"` keeps `"male"`). Build the elf
      case with `replace(SYNTH_RACES["t_duskmari"], key="elf", allowed_sexes=("female",))` inside
      `synthetic_registries("races", extra={"races": {"elf": elf}})` — never `make_race("elf", …)`,
      which rejects a non-`t_` key. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_identity`.
- [x] 2.3 Register the new module in exactly one shard of `.github/evennia-shards.json`
      (`"world.rules.tests.test_identity"`), keeping every existing label untouched; this is the
      only manifest edit this change makes. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
      passes.

## 3. Player creation: race-aware validation, its code, and its tests

- [x] 3.1 In `world/rules/character_creation.py` replace `_validate_sex` (`:285-302`) with the
      delegating form from design.md §Contracts (import `IdentityError`, `resolve_sex` from
      `world.rules.identity`; re-raise as `CharacterCreationError(str(error))`). Change the single
      call site in `preflight_character_creation` (`:480`) to
      `checked_sex = _validate_sex(sex, race)`, keeping it after the race resolution. Do not rename
      the function or change its other callers (there are none). Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation.test_persona_and_sex_activation world.rules.tests.test_creation_messages`
      stays green.
- [x] 3.2 In `world/rules/creation_messages.py` add the code
      `"sex_not_allowed_for_race": "所選種族不允許這個性別。"` to `CREATION_REASON_MESSAGES` and the
      fragment pair `("is not available for race", "sex_not_allowed_for_race")` to
      `_MESSAGE_CODE_MATCHES`, immediately before the `("sex must be one of", "unknown_sex")` entry.
      In `world/rules/tests/test_creation_messages.py` add the case
      `"sex 'male' is not available for race 'elf'": "sex_not_allowed_for_race"` to the `cases`
      table of `test_every_mapped_message_fragment_yields_a_stable_code`. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_messages`.
- [x] 3.3 In `world/rules/tests/test_character_creation/test_persona_and_sex_activation.py` add a
      class `RaceBoundedSexTests(EvenniaTest)` whose `setUp` opens
      `open_synthetic_scope(self, "races", "static_tiers", "subraces", "starting_kits", "presets", "skills", "items", "prices", "elements", extra=…)`
      with the borrowed elf row (`replace(SYNTH_RACES["t_duskmari"], key="elf", allowed_sexes=("female",))`),
      its synthetic subrace, and a `SubraceStartingKit` for that subrace — the
      `test_affinity_creation.py:70-126` idiom verbatim. Add, each decorated
      `@covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")`:
      `test_elf_custom_rejects_a_non_female_sex_before_persistence` (the race's forbidden members,
      derived from `elf.allowed_sexes`, raise with `assertRaisesRegex(CharacterCreationError, "is not available for race")`;
      the shell stays `creation_pending`, `traits.all()` is empty, `attributes.get("sex")` is
      unchanged), `test_elf_custom_accepts_female_and_persists_it` (`entity.sex == "female"`), and
      `test_race_permitting_the_sex_still_accepts_male` (the kit race with `sex="male"` activates and
      stores `"male"`; omitted sex there still normalizes to `DEFAULT_SEX`).
      Also add `test_elf_omitted_sex_normalizes_to_female` decorated with both
      `@covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")`
      and the identity requirement ID, asserting the preflight resolves `"female"` and activation
      stores it. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation.test_persona_and_sex_activation`.
- [x] 3.4 In the same module add
      `test_elf_preset_declaring_a_forbidden_sex_is_rejected_before_activation`
      (`@covers_requirement` on both the identity and the preset-sex requirement IDs): insert a card
      built with `replace(<an in-scope card>, key="t_elf_card", race="elf", subrace=<elf subrace>,
      sex=<a member the elf row forbids>)` through `patch.dict(_live_presets(), {...})`, then assert
      `preflight_character_creation` raises `CharacterCreationError`, that
      `creation_reason(exc) == ("sex_not_allowed_for_race", CREATION_REASON_MESSAGES["sex_not_allowed_for_race"])`,
      and that the character stays pending. Verify: the same focused module command.
- [x] 3.5 In `world/rules/tests/test_creation_wizard.py`, extend the module-level `_SCOPE`'s `extra`
      with the same borrowed elf row, its subrace and its starting kit, then add two methods to the
      class that owns the draft requirement, each decorated
      `@covers_requirement("webclient-character-creation-ui::the-server-owns-the-persisted-creation-wizard-draft")`:
      `test_elf_draft_without_sex_stores_the_race_permitted_default`
      (`save_custom_draft` with the elf race/subrace/allocations, then
      `read_draft(...)["sex"] == elf.allowed_sexes[0]`) and
      `test_elf_draft_with_a_forbidden_sex_is_rejected_leaving_prior_draft` (prior draft unchanged,
      `rejection_code(exc) == "sex_not_allowed_for_race"`). Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_wizard`.
- [x] 3.6 In `web/webclient/actions/tests/test_creation_actions/_support.py` give `_T_ELF`
      `allowed_sexes=("female",)`; in `test_affinity_and_dispatch.py` add
      `test_elf_male_custom_save_rejects_with_the_shared_code_and_message`
      (`@covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")`):
      dispatch `creation.custom` with the elf race/subrace/allocations, empty affinity and
      `sex="male"`; assert `outcome == "rejected"`, `code == "sex_not_allowed_for_race"`, the message
      equals `CREATION_REASON_MESSAGES["sex_not_allowed_for_race"]`, `read_draft(...) is None`, and
      the character is still pending. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_creation_actions.test_affinity_and_dispatch`.

## 4. Preset registry: reject a card its race forbids

- [x] 4.1 Extend `world/lore/player_presets/validation.py::_validate_preset_sex` (`:249-261`) with
      the race check from design.md §Contracts (`RACE_REGISTRY.get` + `allowed_sexes`, `ValueError`
      naming the card, race and sex). Keep the vocabulary check first and the validator order in
      `world/lore/player_presets/__init__.py` unchanged.
- [x] 4.2 In `world/lore/tests/test_player_presets.py` add
      `test_an_elf_preset_declaring_a_forbidden_sex_is_rejected_at_load` (decorated
      `@covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")`),
      building a one-card registry from a synthetic card whose race is an elf row declaring a single
      permitted sex and whose sex is a forbidden member derived from that row, then asserting
      `_validate_preset_sex` raises naming the key and the race. Also extend
      `test_every_shipped_preset_declares_a_concrete_sex` to assert every shipped card's `sex` is in
      its own race's `allowed_sexes`. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets`.

## 5. Import: the semantic race/sex check and the loader write

- [x] 5.1 In `world/imports/validate.py` add `_check_sex_for_race(record)` exactly as in design.md
      §Contracts and register it in `validate_character` immediately after `_check_race_subrace`.
      Add no JSON-Schema `if/then` block to `world/imports/schema.py`. In
      `world/imports/loader.py::_instantiate_validated_character` replace
      `entity.sex = record["sex"]` (`:236`) with `ensure_entity_sex(entity, record["sex"])`.
      Verify the untouched controls stay legal:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.imports.tests.test_schema world.imports.tests.test_loader_trait_values`
      (the male `human_plains` record must keep loading).
- [x] 5.2 In `world/imports/tests/test_validation_semantics.py` add, **without any
      `covers_requirement` decorator** (the requirement is ADDED; see design.md §D12), and without
      naming shipped catalog symbols or unexempted tokens:
      `test_a_non_female_elf_record_is_rejected` and `test_a_permitted_sex_produces_no_sex_issue`
      (synthetic race row declaring one permitted sex via `synthetic_registries(..., extra=…)`;
      assert one `Issue` with `field == "sex"` and `[]` respectively),
      `test_races_that_permit_the_value_produce_no_sex_issue` (a full-vocabulary synthetic race with
      all three members), `test_an_unresolvable_race_leaves_the_sex_judgement_to_the_race_check`,
      and `test_the_sex_check_applies_to_npc_targets_too` (`validate_character(record, NPC)` still
      rejects on `sex`). Import `_check_sex_for_race` alongside the other `_check_*` imports.
      Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.imports.tests.test_validation_semantics`.
- [x] 5.3 In `world/imports/tests/test_batch_all_or_nothing.py` add, **unannotated**,
      `test_a_non_female_elf_record_persists_nothing_from_the_batch` inside `BatchTests`, using the
      `example_record()` + synthetic elf subrace stand-in idiom from design.md §Contracts: first
      assert `validate_batch` reports the `sex` issue for the bad record, then wrap `load_batch` in
      `patch("world.imports.loader._instantiate_validated_character")` and assert `ImportRejected`
      plus `instantiate.assert_not_called()` with a valid sibling in the same batch. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.imports.tests.test_batch_all_or_nothing`.

## 6. The other NPC creation paths

- [x] 6.1 In `world/rules/guild_economy.py::sync_service_content` replace `host.sex = place.host_sex`
      (`:202`) with `ensure_entity_sex(host, place.host_sex)`.
- [x] 6.2 In `world/quests/materializer.py::spawn_role_actor` add `ensure_entity_sex(npc)`
      immediately after `npc.race = tier.race_key` (`:272`); this covers both the stage scene builder
      and the published-encounter activation, which share the function. Add no `sex` field to the
      blueprint or the scene package.
- [x] 6.3 In `world/rules/starting_companions.py::build_starting_companion` replace
      `npc.sex = preset.sex` (`:167`) with `ensure_entity_sex(npc, preset.sex)`.
- [x] 6.4 Confirm by grep that no production module outside `world/rules/identity.py` assigns an
      entity's `sex` attribute (`grep -rn "\.sex = " world typeclasses --include=*.py` must show only
      the seam, docstrings, and test-package hits), so no creation path can bypass the rule.
- [x] 6.5 Tests, all in existing modules and each decorated
      `@covers_requirement("living-entity-hierarchy::livingentity-carries-sex-as-a-bounded-vocabulary-attribute-defaulting-to-other")`:
      in `world/quests/tests/test_scene_builder/test_materialization.py` (or the module that already
      spawns through `spawn_role_actor`) `test_an_elf_scene_npc_lands_on_the_permitted_sex` (a
      synthetic tier whose race declares one permitted sex ends on it) and
      `test_a_human_scene_npc_keeps_its_default_sex` (a full-vocabulary race keeps `DEFAULT_SEX` —
      the control); in `world/rules/tests/test_starting_companions.py`
      `test_an_elf_companion_card_lands_on_the_permitted_sex`; in
      `world/rules/tests/test_guild_economy_sync/test_service_host_identity.py`
      `test_an_elf_host_sync_writes_the_permitted_sex` (patch the place registry with a synthetic
      elf-hosted place and run `sync_service_content`). Verify each module with its own focused
      run, e.g.
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.quests.tests.test_scene_builder.test_materialization`
      and the same shape for
      `world.rules.tests.test_starting_companions` and
      `world.rules.tests.test_guild_economy_sync.test_service_host_identity`.

## 7. Place-registry host validator

- [x] 7.1 In `world/lore/settlements/places.py::validate_place_registry` add the host-race check
      from design.md §Contracts next to the existing `host_sex` membership check (`:325-328`), with
      a message naming the place, the race and the sex.
- [x] 7.2 In `world/lore/tests/test_settlements.py` add, **unannotated** (the requirement is ADDED),
      `test_an_elf_host_with_a_forbidden_sex_fails_load` (plant a complete host with the elf race and
      a forbidden member derived from the live registry through the file's runtime-assembly idiom,
      assert `ValueError` naming the place and the sex), `test_a_permitted_host_sex_still_loads`
      (the elf race with its permitted member validates), and
      `test_a_hostless_place_is_untouched_by_the_sex_check`, beside the existing
      `test_unknown_host_sex_is_rejected`. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.lore.tests.test_settlements`.

## 8. Name roll: a single-sex race pins the pool

- [x] 8.1 In `world/rules/namegen.py` import `RACE_REGISTRY` from `world.lore.races`, add
      `_resolve_race_bounded_sex(race_key, sex)` per design.md §Contracts, and pass its result into
      `_roll_from_pack` from `roll_name_for_race` only. Leave `roll_name`, `_roll_from_pack`,
      `_SEX_POOL` and `_BOUND_PACK_KEYS` untouched. Verify:
      `uv run --locked --env-file=/tmp/mud-test-env evennia test --settings test_settings.py --keepdb world.rules.tests.test_namegen`
      passes with the existing cases unchanged.
- [x] 8.2 In `world/rules/tests/test_namegen.py` extend `RollNameForRaceTest` with
      `test_a_single_declared_sex_pins_the_pool_for_every_forbidden_member` and
      `test_a_multi_sex_race_keeps_the_random_pool`, both decorated
      `@covers_requirement("npc-name-generation::roll-name-for-race-resolves-via-name-pack-by-race-with-a-bounded-fallback")`
      — use the exact ID from
      `uv run --locked python -m tools.spec_traceability list`, never a hand-typed name. Enter
      `synthetic_registries("races", extra={"races": …})` with a synthetic race bound to the
      file-local pack and declaring one permitted sex; assert every given component comes from that
      pool for `None`, `""`, `"unspecified"`, and the forbidden `SEX_VALUES` members across several
      seeds, and that no `("m", "f", "u")` choice is offered. The second test asserts a
      multi-sex race and `race_key=None` keep the single random choice and that an explicit
      permitted member still selects its own pool. Verify: the same focused module command.

## 9. Developer guides

- [x] 9.1 Update `docs/development/adding-npcs.md`: the §1 five-path table and the mechanism
      paragraph must state that every path resolves the sex through `world/rules/identity.py`
      (`ensure_entity_sex`); §2 question 1 (host identity) must state the host race/sex coupling and
      the load-time rejection; Step 1's NPC-specific card rules gain a bullet for `sex` (an elf card
      must declare the permitted member; a non-female elf sex is refused at validation/load with the
      named reason; the dream/scenario-director path declares no sex and the instantiator supplies
      it); the Step 2 CLI note names the `sex` rejection. Describe only shipped mechanisms. Verify
      by reading the diff against design.md §D9 and the delta scenarios — no statement may name a
      validator or field that does not exist after tasks 1–8.
- [x] 9.2 Update `docs/development/adding-player-presets.md`: §2 question 1 gains the race/sex
      coupling; §4's `_validate_preset_sex` row states both checks (vocabulary membership and
      race-permitted) and keeps the section's trigger-point/validator counts truthful; §5's
      common-mistakes table gains the elf-non-female entry with its load-time consequence, distinct
      from the existing "omitting `sex` raises `TypeError`" row.
- [x] 9.3 Extend `tests/test_preset_authoring_docs_contract.py` with, **unannotated** (the
      requirement is ADDED), `test_the_validator_table_documents_the_race_bounded_sex_rule` and
      `test_the_mistake_table_carries_the_elf_sex_case` (structural assertions over the guide text:
      the validator row names the race bound, the mistake table carries the elf case). Verify:
      `uv run --locked python -m unittest tests.test_preset_authoring_docs_contract`.

## 10. Integration gates

- [x] 10.1 Run `uv run --locked python -m tools.spec_traceability check --change elf-creation-female-only`:
      it exits 0, every MODIFIED requirement's annotated test exists, and no annotation error is
      reported. The three ADDED requirements are not indexed before the archive sync, so this run
      says nothing about them — expected, not a waiver.
- [x] 10.2 Run `uv run --locked python -m tools.contract_gate --change elf-creation-female-only`:
      traceability, both lints (including `tools.test_data_lint`), shard manifests and the
      frozen-audit contracts pass. The only manifest edit is the one shard entry from task 2.3.
- [x] 10.3 Run `openspec validate elf-creation-female-only --strict`: the change is valid.
- [x] 10.4 Confirm no observability change: `git diff --stat` touches no `world/observability/` path,
      no `log_*` call is added or moved, and `tools/observability_freeze.json` is unchanged.

## Workflow follow-up

- Hand `review.md` to the reviewer named for this change and record the disposition before archive;
  it covers the one new player-facing string and the two guide prose updates.
- At the archive sync, obtain the canonical IDs for the ADDED requirements (`import-validation`,
  `settlement-place-registry`, `preset-authoring-docs`) with
  `uv run --locked python -m tools.spec_traceability list` and annotate the ten behavior tests listed
  in design.md §D12 with those literal IDs; add any missing behavior test the mapping reveals.
- Archive only after `openspec validate --all --strict` and the post-sync traceability check pass.
