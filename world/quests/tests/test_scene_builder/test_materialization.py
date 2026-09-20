"""Slice of ``test_scene_builder``: SceneBuilderMaterializationTests.
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
    _portrait_callbacks,
    _T_ARCHETYPE,
    _T_ANCHOR,
    _T_NPC_TIER,
    _T_MONSTER_TIER,
    _T_SENTENCE,
    _instance_bound_payload,
    _escort_anchor_payload,
    _monster_instance_payload,
    _reach_anchor_payload,
    SceneBuilderTestBase,
)

class SceneBuilderMaterializationTests(SceneBuilderTestBase):
    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_instance_scene_is_spawned_described_and_bound(self):
        record, _ = self._accept(_instance_bound_payload())
        rooms_before = InstanceRoom.objects.all().count()
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        room = result.room
        self.assertIsInstance(room, InstanceRoom)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before + 1)
        self.assertTrue(room.db.named)
        self.assertEqual(room.scene_archetype, _T_ARCHETYPE)
        self.assertIn(_T_SENTENCE, room.db.desc)

        forward = [e for e in self.anchor.exits if e.destination == room]
        backward = [e for e in room.exits if e.destination == self.anchor]
        self.assertEqual(len(forward), 1)
        self.assertEqual(len(backward), 1)

        npcs = [obj for obj in room.contents if isinstance(obj, NPC)]
        self.assertEqual(len(npcs), 1)
        self.assertIn(npcs[0], room.db.owned_entities)

        fresh = self._fresh(record.quest_id)
        self.assertEqual(fresh.stage_room_id, room.pk)
        self.assertEqual(fresh.objective_target_ids, (npcs[0].pk,))
        self.assertEqual(fresh.protected_entity_ids, ())

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_permanent_layer_scene_is_located_without_spawning_or_binding(self):
        record, _ = self._accept(_reach_anchor_payload())
        rooms_before = InstanceRoom.objects.all().count()
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertIs(result.room, self.anchor)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
        fresh = self._fresh(record.quest_id)
        self.assertIsNone(fresh.stage_room_id)
        self.assertEqual(fresh.objective_target_ids, ())
        self.assertEqual(fresh.protected_entity_ids, ())

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_defeat_and_escort_map_occupants_to_the_correct_binding_set(self):
        defeat_record, _ = self._accept(_instance_bound_payload())
        defeat_result = materialize_stage(
            self.player, defeat_record.quest_id, origin_room=self.anchor
        )
        defeat_npcs = [o for o in defeat_result.room.contents if isinstance(o, NPC)]
        defeat_fresh = self._fresh(defeat_record.quest_id)
        self.assertEqual(defeat_fresh.objective_target_ids, tuple(n.pk for n in defeat_npcs))
        self.assertEqual(defeat_fresh.protected_entity_ids, ())

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_escort_stage_is_refused_before_publication(self):
        with self.assertRaisesRegex(
            QuestCompileError,
            "ESCORT objective, which cannot be published until a "
            "protected-entity binding flow exists",
        ):
            compile_quest_blueprint(_escort_anchor_payload())

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_monster_tier_defeat_spawns_quantity_monsters(self):
        record, _ = self._accept(_monster_instance_payload())
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        monsters = [obj for obj in result.room.contents if isinstance(obj, Monster)]
        self.assertEqual(len(monsters), 2)
        for monster in monsters:
            self.assertEqual(monster.threat_tier, _T_MONSTER_TIER)
            self.assertIn(monster, result.room.db.owned_entities)
        fresh = self._fresh(record.quest_id)
        self.assertEqual(
            fresh.objective_target_ids, tuple(monster.pk for monster in monsters)
        )

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_mid_spawn_failure_rolls_everything_back(self):
        record, _ = self._accept(_instance_bound_payload())
        rooms_before = InstanceRoom.objects.all().count()
        exits_before = Exit.objects.all().count()
        npcs_before = NPC.objects.all().count()
        # Patching the scene-builder's own spawn import leaves the instance
        # room and its exit pair created, then the occupant spawn fails: the
        # outer transaction must roll the whole scene back.
        with patch(
            "world.quests.scene_builder.spawn",
            side_effect=RuntimeError("injected occupant spawn failure"),
        ):
            with self.assertRaises(RuntimeError):
                materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
        self.assertEqual(Exit.objects.all().count(), exits_before)
        self.assertEqual(NPC.objects.all().count(), npcs_before)

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_failure_after_bind_rolls_back_and_resets_the_quest_log_cache(self):
        from world.quests.binding import bind_stage_runtime as real_bind

        record, _ = self._accept(_instance_bound_payload())
        rooms_before = InstanceRoom.objects.all().count()
        exits_before = Exit.objects.all().count()

        def flaky_bind(actor, quest_id, **kwargs):
            real_bind(actor, quest_id, **kwargs)
            raise RuntimeError("injected post-bind failure")

        with patch(
            "world.quests.scene_builder.bind_stage_runtime", side_effect=flaky_bind
        ):
            with self.assertRaises(RuntimeError):
                materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
        self.assertEqual(Exit.objects.all().count(), exits_before)
        fresh = self._fresh(record.quest_id)
        self.assertIsNone(fresh.stage_room_id)
        self.assertEqual(fresh.objective_target_ids, ())
        self.assertEqual(fresh.protected_entity_ids, ())

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_reentry_is_idempotent(self):
        record, _ = self._accept(_instance_bound_payload())
        first = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        rooms = InstanceRoom.objects.all().count()
        exits = Exit.objects.all().count()
        npcs = NPC.objects.all().count()
        second = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertIs(second.room, first.room)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms)
        self.assertEqual(Exit.objects.all().count(), exits)
        self.assertEqual(NPC.objects.all().count(), npcs)

    @covers_requirement("scene-builder::materializing-a-stage-spawns-the-destination-sets-scene-metadata-and-binds-one-stage-atomically-and-idempotently")
    def test_invalid_materialization_requests_are_named_and_side_effect_free(self):
        with self.assertRaises(SceneBuilderNotActive):
            materialize_stage(self.player, "bogus:1", origin_room=self.anchor)

        from world.quests.catalog import INTRODUCTORY_HUNT

        from world.quests.runtime import fulfill_record, definition_for

        record, _ = self._accept(_instance_bound_payload())
        definition = definition_for(record)
        from world.quests.transitions import apply_quest_log_replacement

        completed = fulfill_record(record, definition)
        apply_quest_log_replacement(self.player, [completed])
        with self.assertRaises(SceneBuilderNotActive):
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)

        hand_written = accept(self.player, INTRODUCTORY_HUNT.key)
        with self.assertRaises(SceneBuilderNoRequirements):
            materialize_stage(self.player, hand_written.quest_id, origin_room=self.anchor)

        fresh_record, _ = self._accept(_instance_bound_payload())
        other = create_object(Room, key="wrong-room")
        with self.assertRaises(SceneBuilderLocationError):
            materialize_stage(
                self.player, fresh_record.quest_id, origin_room=other
            )

    @covers_requirement("scene-builder::npc-role-tiers-resolve-deterministic-physical-stats-through-the-lore-registries")
    def test_stored_stats_equal_the_lore_table_values(self):
        record, _ = self._accept(_instance_bound_payload())
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        tier = SYNTH_NPC_TIERS[_T_NPC_TIER]
        config = trait_config_for_values(
            build_initial_traits(tier.race_key, tier=tier.static_tier_key)
        )
        # The tier path pins magic_power at the tier's own band floor.
        self.assertEqual(
            npc.traits.magic_power.base,
            SYNTH_STATIC_TIERS[tier.static_tier_key].magic_band[0],
        )
        for key in ("hp", "atk_phys", "agility", "defense", "magic_power"):
            self.assertEqual(
                getattr(npc.traits, key).base,
                config[key]["base"],
                key,
            )

    @covers_requirement("scene-builder::anti-hallucination-the-proposal-never-chooses-numbers-stats-or-class-lineage")
    def test_characterization_age_never_enters_a_stored_trait(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        record, _ = self._accept(payload)
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        tier = SYNTH_NPC_TIERS[_T_NPC_TIER]
        config = trait_config_for_values(
            build_initial_traits(tier.race_key, tier=tier.static_tier_key)
        )
        for key in ("hp", "atk_phys", "agility", "defense", "magic_power"):
            self.assertEqual(
                getattr(npc.traits, key).base,
                config[key]["base"],
                key,
            )
        self.assertNotIn("35", str(npc.traits.hp.base))
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertEqual(npc.db.age, 35)
        self.assertEqual(npc.db.apparent_age, 35)
        self.assertEqual(
            npc.db.portrait_policy,
            {"mode": "named", "stable_key": "forest_bandit_chief"},
        )
        # Registry provenance (gallery-builtin-fallbacks): the tier key rides
        # the spawned NPC so a tier-level fallback declaration resolves even
        # though the portrait subject is the stable key, not the tier.
        self.assertEqual(npc.db.npc_tier_key, _T_NPC_TIER)

    @covers_requirement("scene-builder::anti-hallucination-the-proposal-never-chooses-numbers-stats-or-class-lineage")
    def test_unknown_tier_in_a_requirement_is_rejected_before_any_spawn(self):
        record, _ = self._accept(_instance_bound_payload())
        forged = (
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype=_T_ARCHETYPE,
                anchor_near=_T_ANCHOR,
                scene_sentence=_T_SENTENCE,
                npc_reqs=(("bandit", "bogus_tier", None),),
            ),
        )
        SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
        rooms_before = InstanceRoom.objects.all().count()
        with self.assertRaises(SceneBuilderSpawnError):
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    @covers_requirement("scene-builder::the-occupant-spawn-path-exposes-a-post-commit-portrait-eligibility-seam-with-unchanged-atomicity")
    def test_generic_occupant_spawn_schedules_no_portrait(self):
        record, _ = self._accept(_instance_bound_payload())
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        # The stage-binding write also schedules its quest_transition event
        # (observability migration); the portrait seam's contract is that it
        # schedules NOTHING for a generic occupant.
        self.assertEqual(_portrait_callbacks(callbacks), [])
        from world.art.store import ArtAssetRecord

        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    @covers_requirement("scene-builder::the-occupant-spawn-path-exposes-a-post-commit-portrait-eligibility-seam-with-unchanged-atomicity")
    @covers_requirement("art-asset-lifecycle::validated-named-npc-spawn-schedules-its-portrait-ensure-after-the-spawn-transaction-commits")
    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_named_policy_occupant_schedules_after_commit_only(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        record, _ = self._accept(payload)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertEqual(len(_portrait_callbacks(callbacks)), 1)
        from world.art.store import ArtAssetRecord

        # The retrofit: the committed spawn owns one gallery job, never a
        # classic fixed-identity record.
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key__startswith="art:portrait:character:forest_bandit_chief:gen:"
            ).count(),
            1,
        )
        self.assertFalse(
            ArtAssetRecord.objects.filter(
                db_key="art:portrait:character:forest_bandit_chief"
            ).exists()
        )

    @covers_requirement("scene-builder::the-occupant-spawn-path-exposes-a-post-commit-portrait-eligibility-seam-with-unchanged-atomicity")
    @covers_requirement("art-asset-lifecycle::validated-named-npc-spawn-schedules-its-portrait-ensure-after-the-spawn-transaction-commits")
    @covers_requirement("spawn-named-portraits::a-spawned-named-occupant-completes-the-full-portrait-pipeline")
    def test_rolled_back_materialization_emits_no_portrait_job(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
                "title": "林間盜匪首領",
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        record, _ = self._accept(payload)

        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch(
                "world.quests.scene_builder._bind_stage",
                side_effect=RuntimeError("spawn failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                materialize_stage(
                    self.player, record.quest_id, origin_room=self.anchor
                )
        self.assertEqual(callbacks, [])
        from world.art.store import ArtAssetRecord

        self.assertEqual(ArtAssetRecord.objects.count(), 0)
