"""Slice of ``test_scene_builder``: SceneOccupantPrototypeTests, SceneBuilderPortraitPipelineTests.
"""
from contextlib import ExitStack
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest
from django.test import override_settings
from evennia.prototypes import prototypes as prototypes_module
from evennia.prototypes import spawner as spawner_module
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room
from world.ai.profiles import default_profiles
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.subjects import ArtSubjectKind
from world.art.worker import drain_synchronous
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import read_records
from world.quests.scene_builder import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    _validate_occupant_parent,
    materialize_stage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation, accept
from world.skills.registry import SkillPrerequisite
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.traits import build_initial_traits, trait_config_for_values
from world.tests.synthetic_data import (
    SYNTH_ANCHORS,
    SYNTH_ARCHETYPES,
    SYNTH_GUILD_ISSUER_KEY,
    SYNTH_NPC_TIERS,
    SYNTH_STATIC_TIERS,
    make_skill,
    synthetic_registries,
)
from tools.spec_traceability import covers_requirement

from ._support import (
    _T_ISSUER,
    _T_ARCHETYPE,
    _T_ANCHOR,
    _T_NPC_TIER,
    SceneBuilderTestBase,
)

class SceneOccupantPrototypeTests(EvenniaTestCase):
    @covers_requirement("scene-builder::anti-hallucination-the-proposal-never-chooses-numbers-stats-or-class-lineage")
    @covers_requirement("npc-identity-titles::the-existing-scene-builder-and-generated-quest-contracts-are-unchanged-where-not-amended")
    def test_module_prototypes_resolve_with_whitelisted_keys_and_typeclasses(self):
        prototypes_module.load_module_prototypes("world.prototypes")
        npc_proto = spawner_module.search_prototype("scene_npc", require_single=True)[0]
        monster_proto = spawner_module.search_prototype(
            "scene_monster", require_single=True
        )[0]
        self.assertEqual(npc_proto["prototype_key"], "scene_npc")
        self.assertEqual(npc_proto["typeclass"], "typeclasses.npcs.NPC")
        self.assertEqual(monster_proto["prototype_key"], "scene_monster")
        self.assertEqual(monster_proto["typeclass"], "typeclasses.monsters.Monster")

    def test_whitelist_contains_exactly_the_two_scene_prototypes(self):
        self.assertEqual(
            SCENE_OCCUPANT_PROTOTYPE_WHITELIST, ("scene_npc", "scene_monster")
        )

    def test_validate_occupant_parent_rejects_non_whitelisted_parent_and_override(self):
        _validate_occupant_parent({"prototype_parent": "scene_npc"})
        with self.assertRaises(SceneBuilderSpawnError):
            _validate_occupant_parent({"prototype_parent": "instance_room"})
        with self.assertRaises(SceneBuilderSpawnError):
            _validate_occupant_parent(
                {
                    "prototype_parent": "scene_npc",
                    "typeclass": "typeclasses.rooms.Room",
                }
            )

class SceneBuilderPortraitPipelineTests(SceneBuilderTestBase):
    """End-to-end spawn -> on_commit -> gate -> fake worker coverage."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.tempdir.name)),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    def _characterized_payload(self, **overrides):
        from world.ai.director_templates import QUEST_TEMPLATE_POOL

        payload = QUEST_TEMPLATE_POOL[0].to_payload()
        # The hand-written pool names shipped catalog rows; the portrait
        # pipeline only needs a structurally valid blueprint, so the rows are
        # re-pointed at the kit before materialization.
        payload["issuer"] = _T_ISSUER
        for stage in payload["stages"]:
            stage["location_req"]["archetype"] = _T_ARCHETYPE
            stage["location_req"]["anchor_near"] = _T_ANCHOR
            stage["location_req"]["anchor_key"] = None
            for req in stage["npc_req"]:
                req["tier"] = _T_NPC_TIER
        entry = {
            "display_name": "黑鬍",
            "age": 35,
            "apparent_age": 35,
            "portrait": {"stable_key": "forest_bandit_chief"},
        }
        entry.update(overrides)
        payload["stages"][0]["npc_req"][0].update(entry)
        return payload

    def _materialize_and_drain(self, payload, client=None):
        record, _ = self._accept(payload)
        with self.captureOnCommitCallbacks(execute=True):
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        client = client or FakeSDWebUIClient()
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            dispatched = drain_synchronous(10)
        return record, client, dispatched

    @covers_requirement("spawn-named-portraits::a-spawned-named-occupant-completes-the-full-portrait-pipeline")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_fake_worker_receives_the_story_driven_description(self):
        record, client, dispatched = self._materialize_and_drain(
            self._characterized_payload()
        )
        self.assertEqual(dispatched, 1)
        self.assertEqual(len(client.calls), 1)
        subject, description = client.calls[0]
        self.assertEqual(subject.kind, ArtSubjectKind.CHARACTER)
        self.assertEqual(subject.key, "forest_bandit_chief")
        self.assertIn("黑鬍", description)
        self.assertIn("35", description)

        # The retrofit settles to a gallery card, not a classic record.
        from world.art import gallery as gallery_api
        from world.art.subjects import ArtSubject
        from world.art.store import ArtAssetRecord

        cards = gallery_api.cards_for(ArtSubject(ArtSubjectKind.CHARACTER, "forest_bandit_chief"))
        self.assertEqual(len(cards), 1)
        self.assertIsNone(cards[0]["binding"])
        self.assertTrue(
            (Path(self.tempdir.name) / cards[0]["stored_identity"]).is_file()
        )
        self.assertFalse(
            ArtAssetRecord.objects.filter(
                db_key="art:portrait:character:forest_bandit_chief"
            ).exists()
        )

    @covers_requirement("spawn-named-portraits::a-spawned-named-occupant-completes-the-full-portrait-pipeline")
    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_shared_stable_key_resolves_to_one_card_from_the_first_materialization(self):
        from world.art import gallery as gallery_api
        from world.art.subjects import ArtSubject

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "forest_bandit_chief")
        first_client = FakeSDWebUIClient()
        _, _, first_dispatched = self._materialize_and_drain(
            self._characterized_payload(),
            client=first_client,
        )
        self.assertEqual(first_dispatched, 1)
        # The first materialization's description is the one that generated
        # the card.
        self.assertIn("黑鬍", first_client.calls[0][1])
        self.assertNotIn("獨眼", first_client.calls[0][1])
        _, second_client, second_dispatched = self._materialize_and_drain(
            self._characterized_payload(
                display_name="獨眼",
                age=40,
                apparent_age=40,
            ),
            client=FakeSDWebUIClient(),
        )

        # The second materialization sees the occupied gallery and is
        # suppressed by the automatic-generation guard without requesting a
        # second generation: nothing dispatched, still exactly one card.
        self.assertEqual(second_dispatched, 0)
        self.assertEqual(second_client.calls, [])
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertTrue(
            (Path(self.tempdir.name) / cards[0]["stored_identity"]).is_file()
        )
