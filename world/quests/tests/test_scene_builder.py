"""Tests for the deterministic SceneBuilder materialization layer (scene-builder).

Covers the occupant prototype whitelist, the requirements->prototype->spawn
rules (anti-hallucination by construction), atomic and idempotent instance
materialization, permanent-layer located-only behavior, DEFEAT/ESCORT binding
sets, rollback and re-entry, and the lore-backed stat derivation. The shared
base and mixin (``SceneBuilderTestBase``, ``SceneBuilderIsolation``) and the
module-level payload helpers live here; the offline loop, flavor, and
boundary classes moved to sibling modules that import them from this file.
"""

from pathlib import Path
import tempfile
import zlib
from random import Random
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
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import STATIC_TIER_REGISTRY
from world.maps.bootstrap import sync_grid
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import accept_quest, read_records
from world.quests.scene_builder import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    _validate_occupant_parent,
    materialize_stage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.namegen import roll_name_for_race
from world.rules.traits import build_initial_traits, trait_config_for_values

from tools.spec_traceability import covers_requirement


def _portrait_callbacks(callbacks):
    """The captured on-commit callbacks excluding quest-transition events and
    the namegen backfill trace.

    The observability migration schedules one ``quest_transition`` event per
    changed quest through ``transaction.on_commit``, and the backfill seam
    schedules one ``npc_name_fallback`` event per rolled name (namegen-npc-flow
    D4); the portrait-seam contracts below count only the callbacks the seam
    itself owns.
    """
    from world.quests import scene_builder

    return [
        callback
        for callback in callbacks
        if not getattr(getattr(callback, "__code__", None), "co_filename", "").endswith(
            "world/quests/transitions.py"
        )
        and getattr(callback, "func", None) is not scene_builder._log_name_fallback
    ]

def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _install_scenario_director():
    """Install the director layer idempotently after any module reload.

    ``world.ai.tests.test_scenario_director`` re-imports the module from
    ``sys.modules`` (cold-start test), which invalidates function identity for
    references captured earlier in the same process. Clearing the guardrail
    entries and re-registering through the live module keeps every later
    consumer deterministic regardless of test order.
    """
    from world.ai import guardrail, scenario_director
    from world.ai.schemas.registry import _OUTPUT_SCHEMAS

    guardrail._semantic_validators.pop("scenario_director", None)
    guardrail._degrade_fallbacks.pop("scenario_director", None)
    _OUTPUT_SCHEMAS.pop("scenario_director", None)
    scenario_director.register_scenario_director()


def _instance_bound_payload(**overrides):
    payload = {
        "name": "討伐林間盜匪",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": None},
                "location_req": {
                    "layer": "instance",
                    "archetype": "forest_path",
                    "anchor_key": None,
                    "anchor_near": "capital_altoria",
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [{"role": "bandit", "tier": "bandit", "disposition": None}],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _escort_anchor_payload(**overrides):
    payload = {
        "name": "護送商人至王都",
        "quest_type": "護衛",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "escort", "quantity": 1},
                "location_req": {
                    "layer": "anchor",
                    "archetype": "city_street",
                    "anchor_key": "capital_altoria",
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "聖潔王都的中央廣場，人聲鼎沸。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _monster_instance_payload(**overrides):
    payload = {
        "name": "討伐洞穴魔物",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 2, "monster_tier": "low"},
                "location_req": {
                    "layer": "instance",
                    "archetype": "cave_interior",
                    "anchor_key": None,
                    "anchor_near": "capital_altoria",
                    "xyz": None,
                    "scene_sentence": "深邃的洞穴內滴水聲迴盪。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _reach_anchor_payload(**overrides):
    payload = {
        "name": "探查王都廣場",
        "quest_type": "探索",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "reach_location", "quantity": 1},
                "location_req": {
                    "layer": "anchor",
                    "archetype": "city_street",
                    "anchor_key": "capital_altoria",
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "聖潔王都的中央廣場，人聲鼎沸。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": 72, "conditions": []},
    }
    payload.update(overrides)
    return payload


class SceneBuilderIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        self._requirements_items = list(SCENE_REQUIREMENT_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        SCENE_REQUIREMENT_REGISTRY.clear()
        SCENE_REQUIREMENT_REGISTRY.update(self._requirements_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()


class SceneBuilderTestBase(SceneBuilderIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        self.anchor = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.assertIsNotNone(self.anchor)
        self.player = create_object(PlayerCharacter, key="scene-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.anchor

    def _accept(self, payload):
        compiled = compile_quest_blueprint(payload)
        register_generated_quest(compiled)
        return accept_quest(self.player, compiled.definition.key), compiled

    def _fresh(self, quest_id):
        return next(r for r in read_records(self.player) if r.quest_id == quest_id)

class SceneOccupantPrototypeTests(EvenniaTestCase):
    @covers_requirement("scene-builder::anti-hallucination-the-proposal-never-chooses-numbers-stats-or-class-lineage")
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
        self.assertEqual(room.scene_archetype, "forest_path")
        self.assertIn("林間小徑", room.db.desc)

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
            self.assertEqual(monster.threat_tier, "low")
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

        from world.quests.catalog import INTRODUCTORY_HUNT, register_catalog

        register_catalog()
        from world.quests.runtime import fulfill_record, definition_for

        record, _ = self._accept(_instance_bound_payload())
        definition = definition_for(record)
        from world.quests.transitions import apply_quest_log_replacement

        completed = fulfill_record(record, definition)
        apply_quest_log_replacement(self.player, [completed])
        with self.assertRaises(SceneBuilderNotActive):
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)

        hand_written = accept_quest(self.player, INTRODUCTORY_HUNT.key)
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
        tier = NPC_TIER_REGISTRY["bandit"]
        config = trait_config_for_values(
            build_initial_traits(tier.race_key, tier=tier.static_tier_key)
        )
        # The tier path pins magic_power at the tier's own band floor.
        self.assertEqual(
            npc.traits.magic_power.base,
            STATIC_TIER_REGISTRY[tier.static_tier_key].magic_band[0],
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
                "age": 35,
                "apparent_age": 35,
                "portrait": {"stable_key": "forest_bandit_chief"},
            }
        )
        record, _ = self._accept(payload)
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        tier = NPC_TIER_REGISTRY["bandit"]
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

    @covers_requirement("scene-builder::anti-hallucination-the-proposal-never-chooses-numbers-stats-or-class-lineage")
    def test_unknown_tier_in_a_requirement_is_rejected_before_any_spawn(self):
        record, _ = self._accept(_instance_bound_payload())
        forged = (
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype="forest_path",
                anchor_near="capital_altoria",
                scene_sentence="王都近郊的林間小徑，樹影搖曳。",
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

        records = ArtAssetRecord.objects.filter(
            db_key="art:portrait:character:forest_bandit_chief"
        )
        self.assertEqual(records.count(), 1)

    @covers_requirement("scene-builder::the-occupant-spawn-path-exposes-a-post-commit-portrait-eligibility-seam-with-unchanged-atomicity")
    @covers_requirement("art-asset-lifecycle::validated-named-npc-spawn-schedules-its-portrait-ensure-after-the-spawn-transaction-commits")
    @covers_requirement("spawn-named-portraits::a-spawned-named-occupant-completes-the-full-portrait-pipeline")
    def test_rolled_back_materialization_emits_no_portrait_job(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(
            {
                "display_name": "黑鬍",
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

class SceneBuilderCharacterizationTests(SceneBuilderTestBase):
    def _characterized(self, **overrides):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0].update(overrides)
        return payload

    def _spawned_npc(self, payload):
        record, _ = self._accept(payload)
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        return next(obj for obj in result.room.contents if isinstance(obj, NPC))

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_full_characterization_is_materialized_fully(self):
        npc = self._spawned_npc(
            self._characterized(
                display_name="黑鬍",
                age=68,
                apparent_age=68,
                portrait={"stable_key": "forest_bandit_chief"},
            )
        )
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertEqual(npc.db.age, 68)
        self.assertEqual(npc.db.apparent_age, 68)
        self.assertEqual(
            npc.db.portrait_policy,
            {"mode": "named", "stable_key": "forest_bandit_chief"},
        )

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_authored_persona_and_background_land_on_the_spawned_npc(self):
        npc = self._spawned_npc(
            self._characterized(
                persona={
                    "personality": "沉穩",
                    "life_story": "守護森林多年的老獵人",
                    "habit": "黃昏時擦拭獵弓",
                },
                background="來自邊境村莊的資深嚮導",
            )
        )
        self.assertEqual(
            npc.db.persona,
            {
                "identity": {},
                "personality": "沉穩",
                "life_story": "守護森林多年的老獵人",
                "habit": "黃昏時擦拭獵弓",
                "appearance": {},
                "social_connection": {},
                "background": "來自邊境村莊的資深嚮導",
            },
        )
        # The flavor never feeds a stored stat.
        self.assertIsNotNone(npc.traits.atk_phys)

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_an_npc_without_a_persona_block_carries_none(self):
        npc = self._spawned_npc(self._characterized())
        self.assertIsNone(npc.db.persona)

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_over_bound_or_non_text_persona_fields_are_rejected_at_compile(self):
        from world.quests.compile import compile_quest_blueprint

        for overrides in (
            {"persona": {"personality": "x" * 601}},
            {"background": "x" * 601},
            {"persona": {"personality": 42}},
        ):
            with self.subTest(overrides=overrides):
                payload = self._characterized(**overrides)
                with self.assertRaises(ValueError):
                    compile_quest_blueprint(payload)

    @covers_requirement("scene-builder::npc-characterization-carries-an-optional-authored-persona-block-for-look-flavor")
    def test_forged_over_bound_persona_is_rejected_before_any_spawn(self):
        from world.quests.scene_builder import SceneBuilderSpawnError

        record, _ = self._accept(self._characterized())
        forged = (
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype="forest_path",
                anchor_near="capital_altoria",
                scene_sentence="王都近郊的林間小徑，樹影搖曳。",
                npc_reqs=(("bandit", "bandit", None),),
                characterizations=(
                    StageNpcCharacterization(
                        background="x" * 601,
                    ),
                ),
            ),
        )
        SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
        rooms_before = InstanceRoom.objects.all().count()
        with self.assertRaises(SceneBuilderSpawnError):
            materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertEqual(
            InstanceRoom.objects.all().count(), rooms_before,
            "a rejected persona must not spawn a room",
        )

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_portrait_only_occupant_receives_the_adult_baseline(self):
        npc = self._spawned_npc(
            self._characterized(portrait={"stable_key": "forest_bandit_chief"})
        )
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        self.assertEqual(
            npc.db.portrait_policy,
            {"mode": "named", "stable_key": "forest_bandit_chief"},
        )

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_baseline_is_valid_for_elven_occupants(self):
        npc = self._spawned_npc(
            self._characterized(
                tier="elven_civilian",
                portrait={"stable_key": "forest_elf_scout"},
            )
        )
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        from world.art.adult import portrait_eligibility

        self.assertEqual(portrait_eligibility(npc), (25, 25))

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_name_only_occupant_is_named_but_portrait_less(self):
        npc = self._spawned_npc(self._characterized(display_name="黑鬍"))
        self.assertEqual(npc.db.display_name, "黑鬍")
        self.assertIsNone(npc.db.age)
        self.assertIsNone(npc.db.apparent_age)
        self.assertIsNone(npc.db.portrait_policy)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_ages_only_occupant_sets_ages_but_no_policy(self):
        npc = self._spawned_npc(self._characterized(age=40, apparent_age=40))
        self.assertEqual(npc.db.age, 40)
        self.assertEqual(npc.db.apparent_age, 40)
        self.assertIsNone(npc.db.portrait_policy)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    @covers_requirement("scene-builder::the-occupant-spawn-path-backfills-a-missing-display-name-deterministically-through-the-namegen-rule-layer")
    def test_role_based_occupant_without_characterization_only_gets_a_name(self):
        # namegen-npc-flow: the backfill reaches this occupant (no authored
        # name); every other characterization field stays untouched.
        npc = self._spawned_npc(self._characterized())
        self.assertIsNotNone(npc.db.display_name)
        self.assertIn("・", npc.db.display_name)
        self.assertIsNone(npc.db.age)
        self.assertIsNone(npc.db.apparent_age)
        self.assertIsNone(npc.db.portrait_policy)

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_a_portrait_bearing_occupant_always_carries_canonical_ages_before_policy(self):
        """Repository guard: the policy is only materialized after the ages.

        A forged requirement carrying a portrait but no ages still lands on the
        deterministic baseline, so the art adult gate's canonical inputs are
        guaranteed present on every spawn path that sets a policy.
        """
        record, _ = self._accept(_instance_bound_payload())
        forged = (
            StageSpawnRequirement(
                index=0,
                objective_kind=ObjectiveKind.DEFEAT,
                location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                archetype="forest_path",
                anchor_near="capital_altoria",
                scene_sentence="王都近郊的林間小徑，樹影搖曳。",
                npc_reqs=(("bandit", "bandit", None),),
                characterizations=(
                    StageNpcCharacterization(portrait_stable_key="forged_key"),
                ),
            ),
        )
        SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
        result = materialize_stage(
            self.player, record.quest_id, origin_room=self.anchor
        )
        npc = next(obj for obj in result.room.contents if isinstance(obj, NPC))
        self.assertEqual(npc.db.age, 25)
        self.assertEqual(npc.db.apparent_age, 25)
        self.assertEqual(
            npc.db.portrait_policy, {"mode": "named", "stable_key": "forged_key"}
        )

    @covers_requirement("spawn-named-portraits::the-scenebuilder-applies-blueprint-characterization-to-named-occupants")
    def test_forged_invalid_characterization_is_rejected_before_any_spawn(self):
        """Defense in depth: forged requirements cannot bypass the adult floor.

        The compile boundary validated the accepted blueprint, but a forged
        ``StageSpawnRequirement`` must still be re-checked: underage, non-int,
        and unpaired ages would otherwise be written to a spawned NPC (a
        permanently adult-gated occupant). Each forged shape raises before any
        room or occupant is created.
        """
        forged_shapes = (
            StageNpcCharacterization(age=17, apparent_age=17),
            StageNpcCharacterization(age="30", apparent_age="30"),
            StageNpcCharacterization(age=30, apparent_age=None),
            StageNpcCharacterization(age=True, apparent_age=30),
        )
        record, _ = self._accept(_instance_bound_payload())
        for shape in forged_shapes:
            with self.subTest(shape=shape):
                forged = (
                    StageSpawnRequirement(
                        index=0,
                        objective_kind=ObjectiveKind.DEFEAT,
                        location=RoomLocator(DestinationKind.BOUND_INSTANCE),
                        archetype="forest_path",
                        anchor_near="capital_altoria",
                        scene_sentence="王都近郊的林間小徑，樹影搖曳。",
                        npc_reqs=(("bandit", "bandit", None),),
                        characterizations=(shape,),
                    ),
                )
                SCENE_REQUIREMENT_REGISTRY[record.definition_key] = forged
                rooms_before = InstanceRoom.objects.all().count()
                with self.assertRaises(SceneBuilderSpawnError):
                    materialize_stage(
                        self.player, record.quest_id, origin_room=self.anchor
                    )
                self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)


def _expected_backfill_name(
    definition_key: str, stage_index: int, role: str, race: str | None, sex: str | None
) -> str:
    """Independently recompute the design-D3 seed for backfill equality."""
    return roll_name_for_race(
        race or None,
        sex or None,
        Random(zlib.crc32(f"{definition_key}:{stage_index}:{role}".encode("utf-8"))),
    )


class SceneBuilderNamegenBackfillTests(SceneBuilderTestBase):
    """namegen-npc-flow: deterministic display-name backfill at the spawn seam."""

    def _room_npc(self, result):
        return next(obj for obj in result.room.contents if isinstance(obj, NPC))

    @covers_requirement("scene-builder::the-occupant-spawn-path-backfills-a-missing-display-name-deterministically-through-the-namegen-rule-layer")
    def test_backfill_matches_the_seed_and_replays_for_the_same_slot(self):
        record, compiled = self._accept(_instance_bound_payload())
        with self.captureOnCommitCallbacks(execute=True):
            first = materialize_stage(
                self.player, record.quest_id, origin_room=self.anchor
            )
        npc_one = self._room_npc(first)
        # Precondition (design D3): the prototype lands nameless; only the
        # backfill seam can give it a name here.
        self.assertEqual(
            npc_one.db.display_name,
            _expected_backfill_name(compiled.definition.key, 0, "bandit", npc_one.race, npc_one.sex),
        )
        # Rebuild the same definition's same stage/role for another actor: the
        # seed is slot-anchored, not instance-anchored, so the name replays.
        other = create_object(PlayerCharacter, key="scene-player-2")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.anchor
        second_record = accept_quest(other, compiled.definition.key)
        with self.captureOnCommitCallbacks(execute=True):
            second = materialize_stage(
                other, second_record.quest_id, origin_room=self.anchor
            )
        npc_two = self._room_npc(second)
        self.assertEqual(npc_two.db.display_name, npc_one.db.display_name)

    @covers_requirement("scene-builder::the-occupant-spawn-path-backfills-a-missing-display-name-deterministically-through-the-namegen-rule-layer")
    @covers_requirement("scene-builder::every-display-name-backfill-emits-an-observability-info-event")
    def test_authored_display_name_never_rolls_never_logs(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["npc_req"][0]["display_name"] = "黑鬍"
        record, _ = self._accept(payload)
        with (
            patch("world.quests.scene_builder.roll_name_for_race") as roll,
            patch("world.quests.scene_builder.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = materialize_stage(
                self.player, record.quest_id, origin_room=self.anchor
            )
        npc = self._room_npc(result)
        self.assertEqual(npc.db.display_name, "黑鬍")
        roll.assert_not_called()
        info.assert_not_called()

    @covers_requirement("scene-builder::the-occupant-spawn-path-backfills-a-missing-display-name-deterministically-through-the-namegen-rule-layer")
    def test_missing_race_reaches_the_rule_layer_as_none(self):
        # Force the "prototype race absent" branch: a wrapper characterization
        # seam clears npc.race after the tier assignment, and a recording roll
        # captures exactly what the backfill seam passes to the rule layer.
        from world.quests import scene_builder

        calls: list[tuple] = []
        original_apply = scene_builder._apply_characterization
        original_roll = scene_builder.roll_name_for_race

        def clearing_apply(npc, requirement, position):
            original_apply(npc, requirement, position)
            npc.race = None

        def recording_roll(race, sex, rng):
            calls.append((race, sex))
            return original_roll(race, sex, rng)

        record, compiled = self._accept(_instance_bound_payload())
        with (
            self.captureOnCommitCallbacks(execute=True),
            patch.object(scene_builder, "_apply_characterization", clearing_apply),
            patch.object(scene_builder, "roll_name_for_race", recording_roll),
        ):
            result = materialize_stage(
                self.player, record.quest_id, origin_room=self.anchor
            )
        npc = self._room_npc(result)
        self.assertEqual(calls, [(None, "other")])
        self.assertEqual(
            npc.db.display_name,
            _expected_backfill_name(compiled.definition.key, 0, "bandit", None, "other"),
        )

    @covers_requirement("scene-builder::every-display-name-backfill-emits-an-observability-info-event")
    def test_committed_backfill_logs_exactly_one_five_key_event(self):
        record, compiled = self._accept(_instance_bound_payload())
        with (
            patch("world.quests.scene_builder.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = materialize_stage(
                self.player, record.quest_id, origin_room=self.anchor
            )
        # The patch must be entered BEFORE the capture block so the capture's
        # __exit__ runs the scheduled callbacks while log_info is still the
        # mock (with-exit order is reverse of entry).
        npc = self._room_npc(result)
        events = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "npc_name_fallback"
        ]
        self.assertEqual(len(events), 1)
        context = events[0].kwargs["context"]
        self.assertEqual(
            set(context), {"quest", "definition_key", "stage", "role", "name"}
        )
        self.assertEqual(context["quest"], record.quest_id)
        self.assertEqual(context["definition_key"], compiled.definition.key)
        self.assertEqual(context["stage"], 0)
        self.assertEqual(context["role"], "bandit")
        self.assertEqual(context["name"], npc.db.display_name)

    @covers_requirement("scene-builder::the-occupant-spawn-path-backfills-a-missing-display-name-deterministically-through-the-namegen-rule-layer")
    @covers_requirement("scene-builder::every-display-name-backfill-emits-an-observability-info-event")
    def test_rolled_back_materialization_keeps_no_name_and_no_event(self):
        record, _ = self._accept(_instance_bound_payload())
        npcs_before = NPC.objects.count()
        with (
            patch("world.quests.scene_builder.log_info") as info,
            patch(
                "world.quests.scene_builder._bind_stage",
                side_effect=RuntimeError("spawn failed"),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(RuntimeError):
                materialize_stage(
                    self.player, record.quest_id, origin_room=self.anchor
                )
        events = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "npc_name_fallback"
        ]
        self.assertEqual(events, [])
        self.assertEqual(NPC.objects.count(), npcs_before)


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
    def test_fake_worker_receives_the_story_driven_adult_description(self):
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

        from world.art.store import ArtAssetRecord, ArtAssetStatus

        record = ArtAssetRecord.objects.filter(
            db_key="art:portrait:character:forest_bandit_chief"
        ).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertTrue(
            (Path(self.tempdir.name) / "portrait" / "character" / "forest_bandit_chief.png").is_file()
        )

    @covers_requirement("spawn-named-portraits::a-spawned-named-occupant-completes-the-full-portrait-pipeline")
    def test_shared_stable_key_resolves_to_one_asset_with_first_writer_wins(self):
        self._materialize_and_drain(
            self._characterized_payload(),
            client=FakeSDWebUIClient(),
        )
        self._materialize_and_drain(
            self._characterized_payload(
                display_name="獨眼",
                age=40,
                apparent_age=40,
            ),
            client=FakeSDWebUIClient(),
        )

        from world.art.store import ArtAssetRecord, ArtAssetStatus

        records = ArtAssetRecord.objects.filter(
            db_key="art:portrait:character:forest_bandit_chief"
        )
        self.assertEqual(records.count(), 1)
        record = records.first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertIn("黑鬍", record.db.source_description)
        self.assertNotIn("獨眼", record.db.source_description)
        self.assertTrue(
            (Path(self.tempdir.name) / "portrait" / "character" / "forest_bandit_chief.png").is_file()
        )

if __name__ == "__main__":
    unittest.main()
