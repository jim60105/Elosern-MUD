"""Data-contract test: quest compile data-contract surface
Quest publication and registry tests (RegisterGeneratedQuestTests family).

Covers ``register_generated_quest`` all-or-nothing publication with preflight
and rollback, the scene-requirement registry entries, and the shared payload
contract with the ``scenario_director`` guardrail. Shared isolation and
payload helpers come from ``_compile_helpers``.
"""

from unittest.mock import patch
import unittest

from world.lore.monster_placement import MonsterSite
from world.quests.compile import (
    CompiledQuest,
    IssuanceDescriptor,
    QuestCompileError,
    SCENE_REQUIREMENT_REGISTRY,
    StageSpawnRequirement,
    compile_quest_blueprint,
    payload_to_registrations,
    register_generated_quest,
    register_restored_quest,
    scene_requirements_for,
)
from world.quests.compile.payload import _compiled_to_payload
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
    validate_definition,
)
from world.quests.tests._compile_helpers import (
    CompileRegistryIsolation,
    _defeat_payload,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
)
from world.rules.quest_issuance import (
    QUEST_ISSUANCE_REGISTRY,
    Settlement,
    npc_issuer_key,
)
from world.tests.synthetic_data import (
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    SYNTH_MONSTER_VARIANTS,
    SYNTH_REGIONS,
    synthetic_registries,
)

from tools.spec_traceability import covers_requirement
from world.quests.tests._card_fixtures import occupant_card_record

class RegisterGeneratedQuestTests(CompileRegistryIsolation, unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Pure-unit class: the durable store is a database Script, so the
        # store boundary is patched to keep every test here DB-free.
        patcher = patch(
            "world.quests.compile.registration.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _compiled(self):
        return compile_quest_blueprint(_defeat_payload())

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_double_registration_is_idempotent(self):
        compiled = self._compiled()
        register_generated_quest(compiled)
        register_generated_quest(compiled)
        self.assertEqual(
            len(QUEST_DEFINITION_REGISTRY),
            len(self._registry_items) + 1,
        )
        self.assertEqual(
            len(GUILD_OFFER_REGISTRY),
            len(self._offer_items) + 1,
        )

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_conflicting_offer_rolls_back_the_definition_write(self):
        first = compile_quest_blueprint(
            {
                **_defeat_payload(),
                "reward": {"copper": 50, "items": [], "merit": 25},
            }
        )
        register_generated_quest(first)
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)

        conflicting = compile_quest_blueprint(
            {
                **_defeat_payload(),
                "reward": {"copper": 60, "items": [], "merit": 25},
            }
        )
        with self.assertRaises(QuestCompileError):
            register_generated_quest(conflicting)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_definition_new_plus_offer_conflicting_leaves_both_registries_unchanged(self):
        # A conflicting offer already exists for the identity of a definition
        # that is not yet registered (possible through direct registry writes).
        # The preflight must reject before writing the definition, so neither
        # registry changes.
        compiled = self._compiled()
        existing_offer = GuildQuestOffer(
            definition_key=compiled.definition.key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(
                copper=60,
                items=(),
                merit=25,
            ),
        )
        GUILD_OFFER_REGISTRY[(compiled.definition.key, "guild_branch_altoria")] = (
            existing_offer
        )
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_generated_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    @covers_requirement("quest-blueprint::escort-quests-require-a-bound-protected-entity-path")
    def test_register_generated_quest_refuses_escort_stages(self):
        from ._fixtures import anchor_locator, escort, quest
        from world.quests.definitions import QuestType

        definition = quest(
            "escort_publication_guard",
            quest_type=QuestType.ESCORT,
            stages=(QuestStage(0, escort(anchor_locator())),),
        )
        compiled = CompiledQuest(
            definition=definition,
            reward=QuestReward(copper=50, items=(), merit=25),
            issuance=IssuanceDescriptor(
                issuer_key="guild:guild_branch_altoria",
                settlement=Settlement.COUNTER,
            ),
            stage_requirements=(),
        )
        with self.assertRaisesRegex(
            QuestCompileError,
            "ESCORT stages cannot be published until a protected-entity "
            "binding flow exists",
        ):
            register_generated_quest(compiled)
        self.assertNotIn(definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertNotIn(
            (definition.key, "guild_branch_altoria"), GUILD_OFFER_REGISTRY
        )

class SceneRequirementRegistryTests(CompileRegistryIsolation, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        # Pure-unit class: the durable store is a database Script, so the
        # store boundary is patched to keep every test here DB-free.
        patcher = patch(
            "world.quests.compile.registration.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        super().tearDown()

    def _bound_compiled(self):
        payload = _defeat_payload()
        payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
        }
        payload["stages"][0]["npc_req"] = [
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "persona": occupant_card_record(),
            }
        ]
        return compile_quest_blueprint(payload)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_scene_requirements_are_registered_with_the_publication(self):
        compiled = self._bound_compiled()
        register_generated_quest(compiled)
        requirements = scene_requirements_for(compiled.definition.key)
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].index, 0)
        self.assertEqual(requirements[0].npc_reqs, (("bandit", "bandit", None),))
        self.assertEqual(compiled.stage_requirements, requirements)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_double_registration_keeps_one_requirement_entry(self):
        compiled = self._bound_compiled()
        register_generated_quest(compiled)
        before = scene_requirements_for(compiled.definition.key)
        register_generated_quest(compiled)
        after = scene_requirements_for(compiled.definition.key)
        self.assertEqual(len(before), 1)
        self.assertEqual(after, before)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_two_blueprints_differing_only_in_scenes_compile_to_different_keys(self):
        first = self._bound_compiled()
        second_payload = _defeat_payload()
        second_payload["stages"][0]["objective"] = {
            "kind": "defeat",
            "quantity": 1,
            "monster_tier": None,
        }
        second_payload["stages"][0]["location_req"] = {
            "layer": "instance",
            "archetype": "forest_path",
            "anchor_key": None,
            "anchor_near": "capital_altoria",
            "xyz": None,
            "scene_sentence": "另一段不同的場景描述。",
        }
        second_payload["stages"][0]["npc_req"] = [
            {
                "role": "bandit",
                "tier": "bandit",
                "disposition": None,
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "persona": occupant_card_record(),
            }
        ]
        second = compile_quest_blueprint(second_payload)
        self.assertNotEqual(first.definition.key, second.definition.key)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_conflicting_offer_rollback_leaves_no_requirement_entry(self):
        compiled = self._bound_compiled()
        existing_offer = GuildQuestOffer(
            definition_key=compiled.definition.key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(copper=60, items=(), merit=25),
        )
        GUILD_OFFER_REGISTRY[(compiled.definition.key, "guild_branch_altoria")] = (
            existing_offer
        )
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_generated_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)
        self.assertNotIn(compiled.definition.key, SCENE_REQUIREMENT_REGISTRY)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_hand_written_definition_reads_back_empty_requirements(self):
        from world.quests.catalog import INTRODUCTORY_HUNT

        register_quest_definition(INTRODUCTORY_HUNT)
        self.assertEqual(scene_requirements_for(INTRODUCTORY_HUNT.key), ())
        self.assertNotIn(INTRODUCTORY_HUNT.key, SCENE_REQUIREMENT_REGISTRY)

class PrivateCommissionRegistrationTests(CompileRegistryIsolation, unittest.TestCase):
    """Character-namespaced issuances publish into the issuance registry only.

    Pure-unit like the guild-path classes: the durable store boundary is
    patched, and the carrier-authorization seam is patched to authorize the
    compiled key (the genuine scan runs in the Evennia-backed store tests).
    """

    def setUp(self):
        super().setUp()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        patcher = patch(
            "world.quests.compile.registration.append_generated_quest_payload", return_value=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        authorizer = patch(
            "world.quests.compile.compiler.issuer_is_authorized", return_value=True
        )
        authorizer.start()
        self.addCleanup(authorizer.stop)

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        super().tearDown()

    def _npc_compiled(self, issuer="npc:grey_granny", copper=50):
        return compile_quest_blueprint(
            {
                **_defeat_payload(),
                "issuer": issuer,
                "reward": {"copper": copper, "items": [], "merit": 0},
            }
        )

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_a_private_commission_registers_into_the_issuance_registry(self):
        compiled = self._npc_compiled()
        register_generated_quest(compiled)
        self.assertIn(compiled.definition.key, QUEST_DEFINITION_REGISTRY)
        self.assertIn(
            (compiled.definition.key, "npc:grey_granny"),
            QUEST_ISSUANCE_REGISTRY,
        )
        self.assertEqual(len(GUILD_OFFER_REGISTRY), len(self._offer_items))

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_two_commissioners_of_one_definition_register_two_issuances(self):
        first = self._npc_compiled(issuer="npc:grey_granny")
        second = self._npc_compiled(issuer="npc:old_martha")
        self.assertEqual(first.definition.key, second.definition.key)
        register_generated_quest(first)
        register_generated_quest(second)
        self.assertEqual(
            len(QUEST_DEFINITION_REGISTRY), len(self._registry_items) + 1
        )
        self.assertIn(
            (first.definition.key, "npc:grey_granny"), QUEST_ISSUANCE_REGISTRY
        )
        self.assertIn(
            (first.definition.key, "npc:old_martha"), QUEST_ISSUANCE_REGISTRY
        )

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_a_conflicting_private_issuance_rolls_back_the_definition(self):
        compiled = self._npc_compiled()
        register_generated_quest(compiled)
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_issuance = dict(QUEST_ISSUANCE_REGISTRY)
        before_requirements = dict(SCENE_REQUIREMENT_REGISTRY)

        conflicting = self._npc_compiled(copper=60)
        with self.assertRaises(QuestCompileError):
            register_generated_quest(conflicting)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, before_issuance)
        self.assertEqual(SCENE_REQUIREMENT_REGISTRY, before_requirements)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_a_restored_conflicting_requirement_registers_nothing(self):
        # The restore path must preflight before its first write: a
        # conflicting spawn-requirement entry leaves no definition and no
        # issuance registered (design D4).
        compiled = self._npc_compiled()
        SCENE_REQUIREMENT_REGISTRY[compiled.definition.key] = ()
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_issuance = dict(QUEST_ISSUANCE_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_restored_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(QUEST_ISSUANCE_REGISTRY, before_issuance)

    @covers_requirement("scenario-director::the-deterministic-compile-boundary-translates-validated-proposals-into-the-runtime-type")
    def test_a_restored_guild_conflicting_requirement_registers_nothing(self):
        compiled = compile_quest_blueprint(_defeat_payload())
        SCENE_REQUIREMENT_REGISTRY[compiled.definition.key] = ()
        before_definition = dict(QUEST_DEFINITION_REGISTRY)
        before_offer = dict(GUILD_OFFER_REGISTRY)
        with self.assertRaises(QuestCompileError):
            register_restored_quest(compiled)
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before_definition)
        self.assertEqual(GUILD_OFFER_REGISTRY, before_offer)


class SharedPayloadContractTests(CompileRegistryIsolation, unittest.TestCase):
    @covers_requirement("scenario-director::the-canonical-payload-contract-is-versioned-and-shared-by-both-boundaries")
    def test_guardrail_valid_payload_compiles_without_contract_rejection(self):
        from jsonschema import Draft7Validator

        from world.ai.director_templates import QUEST_TEMPLATE_POOL
        from world.ai.scenario_director import (
            SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
            _VALIDATORS,
        )

        for entry in QUEST_TEMPLATE_POOL:
            with self.subTest(entry=entry.name):
                payload = entry.to_payload()
                validator = Draft7Validator(SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
                self.assertEqual(
                    [error.message for error in validator.iter_errors(payload)], []
                )
                for validator_fn in _VALIDATORS.values():
                    self.assertEqual(validator_fn(payload), [])
                compiled = compile_quest_blueprint(payload)
                validate_definition(compiled.definition)


# ---------------------------------------------------------------------------
# The durable mirror of a species-hunt definition (task 3.3): the stored
# payload round-trips the new objective and prose fields, and a corrupt stored
# hunt fails loudly at the payload boundary. Every key below is a kit row or an
# invented one.
# ---------------------------------------------------------------------------
_HUNT_SPECIES = next(iter(SYNTH_MONSTER_SPECIES))
_HUNT_VARIANTS = tuple(
    key
    for key, row in SYNTH_MONSTER_VARIANTS.items()
    if row.species_key == _HUNT_SPECIES
)
_HUNT_ORDINARY = next(
    key for key in _HUNT_VARIANTS if SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_STRONGER = next(
    key for key in _HUNT_VARIANTS if not SYNTH_MONSTER_VARIANTS[key].ordinary_variant
)
_HUNT_REGION = next(iter(SYNTH_REGIONS))
_PAYLOAD_RATIONALE = "合成評價理由：合成隘口的合成強勢型成群巡守，落單者風險極高。"
_PAYLOAD_FLAVOR = "合成背景：合成議會懸賞合成鬃毛，合成獵場因而喧鬧。"


def _hunt_definition() -> QuestDefinition:
    return QuestDefinition(
        key="t_payload_hunt",
        display_name="合成討伐委託",
        quest_type=QuestType.DEFEAT,
        rank="F",
        stages=(
            QuestStage(
                0,
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=2,
                    region_key=_HUNT_REGION,
                    species_key=_HUNT_SPECIES,
                    countable_variant_keys=(_HUNT_ORDINARY, _HUNT_STRONGER),
                ),
            ),
        ),
        deadline_hours=48,
        rating_rationale_zh=_PAYLOAD_RATIONALE,
        background_flavor_zh=_PAYLOAD_FLAVOR,
    )


def _compiled_hunt() -> CompiledQuest:
    return CompiledQuest(
        definition=_hunt_definition(),
        reward=QuestReward(copper=25, items=(), merit=0),
        issuance=IssuanceDescriptor(
            issuer_key=npc_issuer_key("t_payload_commission"),
            settlement=Settlement.AUTO,
        ),
        stage_requirements=(
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=None,
                archetype=None,
                anchor_near=None,
                scene_sentence=None,
                npc_reqs=(),
            ),
        ),
    )


@synthetic_registries(
    "regions", "monster_species", "monster_variants", "monster_tiers"
)
class SpeciesHuntPayloadTests(CompileRegistryIsolation, unittest.TestCase):
    """The stored payload codec carries the hunt selector and the prose fields."""

    def test_a_stored_hunt_payload_round_trips_and_restores(self):
        compiled = _compiled_hunt()
        restored = payload_to_registrations(_compiled_to_payload(compiled))
        self.assertEqual(restored, compiled)
        objective = restored.definition.stages[0].objective
        self.assertEqual(objective.region_key, _HUNT_REGION)
        self.assertEqual(objective.species_key, _HUNT_SPECIES)
        self.assertEqual(
            objective.countable_variant_keys, (_HUNT_ORDINARY, _HUNT_STRONGER)
        )
        self.assertIsInstance(objective.countable_variant_keys, tuple)
        self.assertEqual(restored.definition.rating_rationale_zh, _PAYLOAD_RATIONALE)
        self.assertEqual(restored.definition.background_flavor_zh, _PAYLOAD_FLAVOR)
        # The restored aggregate publishes through the same writer a startup
        # restore uses, so a hunt survives a server restart.
        register_restored_quest(restored)
        self.assertIn(
            restored.definition.key, QUEST_DEFINITION_REGISTRY
        )

    def test_a_corrupt_stored_hunt_fails_loudly_at_the_payload_boundary(self):
        tier_key = next(iter(SYNTH_MONSTER_TIERS))
        cases = {
            "partial-selector": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].pop("species_key"),
            "unknown-region": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].update(region_key="t_absent_region"),
            "unknown-species": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].update(species_key="t_absent_species"),
            "unknown-variant": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].update(countable_variant_keys=["t_absent_variant"]),
            "string-variants": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].update(countable_variant_keys=_HUNT_ORDINARY),
            "no-ordinary-variant": lambda payload: payload["definition"]["stages"][
                0
            ]["objective"].update(countable_variant_keys=[_HUNT_STRONGER]),
            "tier-beside-hunt": lambda payload: payload["definition"]["stages"][0][
                "objective"
            ].update(monster_tier=tier_key),
            "prose-not-a-string": lambda payload: payload["definition"].update(
                rating_rationale_zh=5
            ),
            "prose-too-long": lambda payload: payload["definition"].update(
                background_flavor_zh="評" * 501
            ),
            "prose-ascii-only": lambda payload: payload["definition"].update(
                rating_rationale_zh="synthetic rationale"
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                payload = _compiled_to_payload(_compiled_hunt())
                mutate(payload)
                with self.assertRaises(QuestCompileError):
                    payload_to_registrations(payload)


# ---------------------------------------------------------------------------
# The durable mirror of a bound site clear-out (task 1.2): the stored payload
# carries the site key with an absent-key default, the generative compile
# boundary never authors one, and a corrupt stored clear-out fails loudly at
# the payload boundary. Every key below is a kit row or an invented one.
# ---------------------------------------------------------------------------
_CLEAR_OUT_SITE = "t_payload_site"
_CLEAR_OUT_SITES = {
    _CLEAR_OUT_SITE: MonsterSite(
        _CLEAR_OUT_SITE,
        "nest",
        _HUNT_REGION,
        (4, 4),
        (_HUNT_ORDINARY,),
        1,
        True,
    )
}
_CLEAR_OUT_EXTRA = {"monster_sites": _CLEAR_OUT_SITES}


def _clear_out_definition() -> QuestDefinition:
    return QuestDefinition(
        key="t_payload_clear_out",
        display_name="合成清剿委託",
        quest_type=QuestType.DEFEAT,
        rank="E",
        stages=(
            QuestStage(
                0,
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    requires_bound_targets=True,
                    site_key=_CLEAR_OUT_SITE,
                ),
            ),
        ),
        deadline_hours=None,
    )


def _compiled_clear_out() -> CompiledQuest:
    return CompiledQuest(
        definition=_clear_out_definition(),
        reward=QuestReward(copper=100, items=(), merit=0),
        issuance=IssuanceDescriptor(
            issuer_key=npc_issuer_key("t_payload_clear_out_commission"),
            settlement=Settlement.AUTO,
        ),
        stage_requirements=(
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=None,
                archetype=None,
                anchor_near=None,
                scene_sentence=None,
                npc_reqs=(),
            ),
        ),
    )


def _stored_clear_out_objective(payload: dict) -> dict:
    return payload["definition"]["stages"][0]["objective"]


@synthetic_registries(
    "regions",
    "monster_species",
    "monster_variants",
    "monster_tiers",
    "monster_sites",
    extra=_CLEAR_OUT_EXTRA,
)
class SiteClearOutPayloadTests(CompileRegistryIsolation, unittest.TestCase):
    """The stored payload codec carries the bound clear-out's site key."""

    def test_a_stored_clear_out_payload_round_trips_the_site_key(self):
        compiled = _compiled_clear_out()
        payload = _compiled_to_payload(compiled)
        self.assertEqual(
            _stored_clear_out_objective(payload)["site_key"], _CLEAR_OUT_SITE
        )
        restored = payload_to_registrations(payload)
        self.assertEqual(restored, compiled)
        objective = restored.definition.stages[0].objective
        self.assertEqual(objective.site_key, _CLEAR_OUT_SITE)
        self.assertTrue(objective.requires_bound_targets)
        # The restored aggregate publishes through the same writer a startup
        # restore uses, so a clear-out survives a server restart.
        register_restored_quest(restored)
        self.assertIn(restored.definition.key, QUEST_DEFINITION_REGISTRY)

    def test_an_absent_stored_site_key_decodes_to_the_bound_family(self):
        # A payload written before the selector existed decodes to exactly the
        # objective it recorded: an absent key is the *bound-with-no-site*
        # family, never an invented site.
        payload = _compiled_to_payload(_compiled_clear_out())
        _stored_clear_out_objective(payload).pop("site_key")
        restored = payload_to_registrations(payload)
        objective = restored.definition.stages[0].objective
        self.assertIsNone(objective.site_key)
        self.assertTrue(objective.requires_bound_targets)

    def test_a_corrupt_stored_clear_out_fails_loudly_at_the_payload_boundary(self):
        tier_key = next(iter(SYNTH_MONSTER_TIERS))
        cases = {
            "unknown-site": lambda payload: _stored_clear_out_objective(
                payload
            ).update(site_key="t_absent_site"),
            "non-string-site": lambda payload: _stored_clear_out_objective(
                payload
            ).update(site_key=5),
            "empty-site": lambda payload: _stored_clear_out_objective(payload).update(
                site_key=""
            ),
            "site-without-the-bound-flag": lambda payload: (
                _stored_clear_out_objective(payload).update(
                    requires_bound_targets=False
                )
            ),
            "site-beside-a-tier": lambda payload: _stored_clear_out_objective(
                payload
            ).update(monster_tier=tier_key),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                payload = _compiled_to_payload(_compiled_clear_out())
                mutate(payload)
                with self.assertRaises(QuestCompileError):
                    payload_to_registrations(payload)


class ClearOutCompileBoundaryTests(unittest.TestCase):
    """The generative boundary never authors a site key (design D-C1)."""

    def test_no_compiled_proposal_authors_a_site_key(self):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        stages = 0
        for entry in QUEST_TEMPLATE_POOL:
            with self.subTest(entry=entry.name):
                compiled = compile_quest_blueprint(entry.to_payload())
                for stage in compiled.definition.stages:
                    stages += 1
                    self.assertIsNone(stage.objective.site_key)
        self.assertGreater(stages, 0)

    def test_a_proposal_declaring_a_site_key_is_rejected(self):
        # Presence is rejected, not just a value: a proposal can never smuggle a
        # hand-written site key in and have it silently ignored.
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        rejected = 0
        for entry in QUEST_TEMPLATE_POOL:
            for payload_stage in entry.to_payload()["stages"]:
                if payload_stage["objective"]["kind"] != "defeat":
                    continue
                payload = entry.to_payload()
                payload["stages"][payload_stage["index"]]["objective"]["site_key"] = (
                    _CLEAR_OUT_SITE
                )
                with self.assertRaises(QuestCompileError) as caught:
                    compile_quest_blueprint(payload)
                self.assertIn("site_key", str(caught.exception))
                rejected += 1
        self.assertGreater(rejected, 0)


if __name__ == "__main__":
    unittest.main()
