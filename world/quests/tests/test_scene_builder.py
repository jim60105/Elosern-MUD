"""Tests for the deterministic SceneBuilder materialization layer (scene-builder).

Covers the occupant prototype whitelist, the requirements->prototype->spawn
rules (anti-hallucination by construction), atomic and idempotent instance
materialization, permanent-layer located-only behavior, DEFEAT/ESCORT binding
sets, rollback and re-entry, the lore-backed stat derivation, the offline
end-to-end loop through the two new commands, and the repository boundary
invariants (offline tests only, no live client, no startup re-sync).
"""

from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

from django.db import transaction
from django.test import override_settings

from evennia.objects.models import ObjectDB
from evennia.prototypes import prototypes as prototypes_module
from evennia.prototypes import spawner as spawner_module
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import AnchorRoom, InstanceRoom, Room
from world.ai.profiles import default_profiles
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.subjects import ArtSubjectKind
from world.art.worker import drain_synchronous
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.maps.bootstrap import sync_grid
from world.quests.compile import (
    SCENE_REQUIREMENT_REGISTRY,
    StageNpcCharacterization,
    StageSpawnRequirement,
    compile_quest_blueprint,
    register_generated_quest,
)
from world.quests.definitions import DestinationKind, ObjectiveKind, RoomLocator
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.scene_builder import (
    SCENE_OCCUPANT_PROTOTYPE_WHITELIST,
    SceneBuilderLocationError,
    SceneBuilderNoRequirements,
    SceneBuilderNotActive,
    SceneBuilderSpawnError,
    _validate_occupant_parent,
    apply_scene_flavor,
    materialize_stage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.traits import build_initial_traits, trait_config_for_values

from commands.guild import CmdGuildAccept, CmdGuildRequest, CmdGuildTurnIn
from commands.scene import CmdEnterScene

from tools.spec_traceability import covers_requirement


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


class SceneOccupantPrototypeTests(EvenniaTest):
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
    def test_escort_permanent_stage_is_located_without_spawning_or_binding(self):
        record, _ = self._accept(_escort_anchor_payload())
        rooms_before = InstanceRoom.objects.all().count()
        result = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertIs(result.room, self.anchor)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
        fresh = self._fresh(record.quest_id)
        self.assertIsNone(fresh.stage_room_id)
        self.assertEqual(fresh.objective_target_ids, ())
        self.assertEqual(fresh.protected_entity_ids, ())

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
        race = RACE_REGISTRY[tier.race_key]
        values = build_initial_traits(tier.race_key, tier=tier.static_tier_key)
        values["magic_level"] = race.starting_magic_level
        config = trait_config_for_values(values, race.magic_cap)
        for key in ("hp", "atk_phys", "agility", "defense", "magic_level"):
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
        race = RACE_REGISTRY[tier.race_key]
        values = build_initial_traits(tier.race_key, tier=tier.static_tier_key)
        values["magic_level"] = race.starting_magic_level
        config = trait_config_for_values(values, race.magic_cap)
        for key in ("hp", "atk_phys", "agility", "defense", "magic_level"):
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
        self.assertEqual(callbacks, [])
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
        self.assertEqual(len(callbacks), 1)
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
    def test_role_based_occupant_without_characterization_is_untouched(self):
        npc = self._spawned_npc(self._characterized())
        self.assertIsNone(npc.db.display_name)
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


class SceneBuilderOfflineLoopTests(SceneBuilderIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        self.anchor = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.player = create_object(PlayerCharacter, key="offline-scene-player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.skills = {"active": ["fire_ball"], "passive": []}
        self.player.location = self.anchor
        self.staff = create_object(NPC, key="scene staff", location=self.anchor)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key="guild_branch_altoria"
            )
        )
        from world.rules.guild import register_adventurer

        register_adventurer(self.player, self.staff)
        from world.quests.bootstrap import sync_quest_runtime

        sync_quest_runtime()
        _install_scenario_director()

    def _resolve_lethal(self, target):
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.combat import Battlefield, BattlefieldActionContext

        field = Battlefield(
            {"party": frozenset({self.player.key}), "foes": frozenset({target.key})},
            {self.player.key: self.player, target.key: target},
        )
        request = ActionRequest(
            self.player,
            "fire_ball",
            [target],
            BattlefieldActionContext(field),
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            return ActionResolver.resolve(request)

    def _accept(self, payload):
        compiled = compile_quest_blueprint(payload)
        register_generated_quest(compiled)
        return accept_quest(self.player, compiled.definition.key), compiled

    def _fresh(self, quest_id):
        return next(r for r in read_records(self.player) if r.quest_id == quest_id)

    def _generated_definition_key(self, display_name):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        matches = [
            key
            for key, definition in QUEST_DEFINITION_REGISTRY.items()
            if definition.display_name == display_name
        ]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_offline_loop_materializes_an_instance_scene_without_an_llm(self):
        disabled = {
            layer: {"enabled": False}
            for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")
        }
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            output = self.call(CmdGuildRequest(), "", "你張貼了一份委託", caller=self.player)
        self.assertIn("討伐林間盜匪", output)
        definition_key = self._generated_definition_key("討伐林間盜匪")
        self.assertIn(definition_key, output)

        self.call(CmdGuildAccept(), definition_key, "你接取了任務", caller=self.player)
        records = [
            r for r in read_records(self.player) if r.definition_key == definition_key
        ]
        self.assertEqual(len(records), 1)
        self.assertIs(records[0].state, QuestState.IN_PROGRESS)

        # Entering spawns the scene and moves the player; the room's look text
        # is prepended, so invoke the command directly and assert the movement.
        enter = CmdEnterScene()
        enter.caller = self.player
        enter.cmdstring = "進入"
        enter.args = ""
        with patch.object(self.player, "msg") as player_msg:
            enter.parse()
            enter.func()
        self.assertIsInstance(self.player.location, InstanceRoom)
        sent = " ".join(
            str(call.args[0]) for call in player_msg.call_args_list if call.args
        )
        self.assertIn("走入", sent)

        bandit = next(
            obj for obj in self.player.location.contents if isinstance(obj, NPC)
        )
        bandit.traits.hp._data["current"] = 1
        result = self._resolve_lethal(bandit)
        self.assertEqual(result.outcome, "success")

        completed = [
            r
            for r in read_records(self.player)
            if r.definition_key == definition_key and r.state is QuestState.COMPLETED
        ]
        self.assertTrue(completed, "bound DEFEAT did not auto-complete offline")

        self.player.move_to(self.anchor, quiet=True)
        output = self.call(CmdGuildTurnIn(), completed[0].quest_id, "你回報了任務", caller=self.player)
        self.assertIn("50 銅", output)
        self.assertEqual(self.player.db.wallet, 50)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_without_an_instance_stage_is_side_effect_free(self):
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        self.call(CmdEnterScene(), "", "你目前沒有需要進入的任務場景", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_from_inside_the_bound_room_is_side_effect_free(self):
        record, _ = self._accept(_instance_bound_payload())
        materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.player.move_to(
            next(
                e.destination
                for e in self.anchor.exits
                if isinstance(e.destination, InstanceRoom)
            ),
            quiet=True,
        )
        rooms_before = InstanceRoom.objects.all().count()
        self.call(CmdEnterScene(), "", "你已經在任務場景裡了", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_selects_the_enterable_instance_stage(self):
        # Quest A anchors near capital_altoria and is not enterable from a
        # plain room; quest B declares no anchor and is enterable from anywhere.
        # The command must skip A and select B rather than failing on A.
        anchored_payload = _instance_bound_payload(name="先在王都的委託")
        unanchored = _instance_bound_payload(name="無錨點的委託")
        unanchored["stages"][0]["location_req"]["anchor_near"] = None
        self._accept(anchored_payload)
        _, compiled_b = self._accept(unanchored)
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        enter = CmdEnterScene()
        enter.caller = self.player
        enter.cmdstring = "進入"
        enter.args = ""
        enter.parse()
        enter.func()
        self.assertIsInstance(self.player.location, InstanceRoom)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before + 1)
        entered = self._fresh(next(
            r.quest_id for r in read_records(self.player)
            if r.definition_key == compiled_b.definition.key
        ))
        self.assertEqual(entered.stage_room_id, self.player.location.pk)

    @covers_requirement("scene-builder::scene-entry-and-generated-quest-triggers-are-deterministic-commands-that-keep-the-offline-loop-playable")
    def test_enter_from_a_mismatched_origin_is_a_named_side_effect_free_rejection(self):
        self._accept(_instance_bound_payload())
        self.player.move_to(self.room1, quiet=True)
        rooms_before = InstanceRoom.objects.all().count()
        # The only instance quest anchors near capital_altoria, which the
        # caller's plain room does not match, so the command reports no
        # enterable scene and creates nothing.
        self.call(CmdEnterScene(), "", "你目前沒有需要進入的任務場景", caller=self.player)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)


class SceneFlavorContextAndApplyTests(SceneBuilderTestBase):
    """The deterministic flavor-context seam and the idempotent sole-writer apply."""

    def _materialize_first(self, payload):
        record, _ = self._accept(payload)
        return record, materialize_stage(self.player, record.quest_id, origin_room=self.anchor)

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_fresh_instance_scene_carries_the_four_key_flavor_context(self):
        record, result = self._materialize_first(_instance_bound_payload())
        self.assertIsInstance(result.room, InstanceRoom)
        self.assertEqual(
            result.flavor_context,
            {
                "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                "quest_context": "討伐林間盜匪（討伐任務）",
                "room_name": "林間小徑",
                "region": "聖潔王都",
            },
        )

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_fresh_scene_without_anchor_has_empty_region(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["location_req"]["anchor_near"] = None
        _, result = self._materialize_first(payload)
        self.assertEqual(result.flavor_context["region"], "")
        self.assertEqual(
            set(result.flavor_context),
            {"scene_sentence", "quest_context", "room_name", "region"},
        )

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_requirement_sentence_falls_back_to_the_archetype_registry(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["location_req"]["scene_sentence"] = None
        _, result = self._materialize_first(payload)
        from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

        self.assertEqual(
            result.flavor_context["scene_sentence"],
            SCENE_ARCHETYPE_REGISTRY["forest_path"].scene_sentence,
        )

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_sentence_less_scene_carries_no_flavor_context(self):
        payload = _instance_bound_payload()
        payload["stages"][0]["location_req"]["scene_sentence"] = None
        payload["stages"][0]["location_req"]["archetype"] = None
        _, result = self._materialize_first(payload)
        self.assertIsNone(result.flavor_context)

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_reentered_bound_stage_carries_no_flavor_context(self):
        record, first = self._materialize_first(_instance_bound_payload())
        self.assertIsNotNone(first.flavor_context)
        second = materialize_stage(self.player, record.quest_id, origin_room=self.anchor)
        self.assertIs(second.room, first.room)
        self.assertIsNone(second.flavor_context)

    @covers_requirement("scene-builder::scene-materialization-exposes-deterministic-flavor-context-for-fresh-instance-scenes")
    def test_permanent_layer_scene_carries_no_flavor_context(self):
        _, result = self._materialize_first(_reach_anchor_payload())
        self.assertIs(result.room, self.anchor)
        self.assertIsNone(result.flavor_context)

    @covers_requirement("scene-builder::the-scene-flavor-write-is-deterministic-and-never-affects-materialization", "scene-flavor::the-flavor-write-is-deterministic-idempotent-and-sole-writer")
    def test_apply_scene_flavor_writes_once_and_never_touches_desc(self):
        _, result = self._materialize_first(_instance_bound_payload())
        room = result.room
        desc_before = room.db.desc
        self.assertTrue(apply_scene_flavor(room, "苔石在幽暗中泛著微光。"))
        self.assertEqual(room.db.scene_flavor, "苔石在幽暗中泛著微光。")
        self.assertEqual(room.db.desc, desc_before)
        self.assertFalse(apply_scene_flavor(room, "另一段氛圍。"))
        self.assertEqual(room.db.scene_flavor, "苔石在幽暗中泛著微光。")
        self.assertEqual(room.db.desc, desc_before)

    @covers_requirement("scene-builder::the-scene-flavor-write-is-deterministic-and-never-affects-materialization", "scene-flavor::the-flavor-write-is-deterministic-idempotent-and-sole-writer")
    def test_apply_scene_flavor_rejects_non_string_text(self):
        room = create_object(InstanceRoom, key="reject", location=None)
        self.assertFalse(apply_scene_flavor(room, None))
        self.assertFalse(apply_scene_flavor(room, "   "))
        self.assertIsNone(room.db.scene_flavor)

    @covers_requirement("scene-builder::the-scene-flavor-write-is-deterministic-and-never-affects-materialization", "scene-flavor::the-flavor-write-is-deterministic-idempotent-and-sole-writer")
    def test_apply_scene_flavor_skips_a_vanished_room_without_raising(self):
        _, result = self._materialize_first(_instance_bound_payload())
        room = result.room
        stale = room
        ObjectDB.objects.filter(pk=room.pk).delete()
        self.assertFalse(InstanceRoom.objects.filter(pk=room.pk).exists())
        self.assertFalse(apply_scene_flavor(stale, "殘影般的氛圍。"))
        self.assertEqual(InstanceRoom.objects.filter(pk=room.pk).count(), 0)

    @covers_requirement("scene-builder::the-scene-flavor-write-is-deterministic-and-never-affects-materialization", "scene-flavor::the-flavor-write-is-deterministic-idempotent-and-sole-writer")
    def test_apply_scene_flavor_swallows_a_simulated_lookup_failure(self):
        _, result = self._materialize_first(_instance_bound_payload())
        room = result.room
        with patch(
            "world.quests.scene_builder.ObjectDB.objects.filter",
            side_effect=RuntimeError("injected lookup failure"),
        ):
            self.assertFalse(apply_scene_flavor(room, "失敗的氛圍。"))
        self.assertIsNone(room.db.scene_flavor)

    def test_flavor_context_helper_is_ban_clean_and_returns_plain_data(self):
        from world.quests import scene_builder
        import inspect

        source = inspect.getsource(scene_builder.build_flavor_context).lower()
        for fragment in ("world.ai", "ollama", "llm_client"):
            self.assertNotIn(fragment, source)
        _, result = self._materialize_first(_instance_bound_payload())
        for key, value in result.flavor_context.items():
            self.assertIsInstance(value, str)


class SceneBuilderBoundaryTests(unittest.TestCase):
    @covers_requirement("scene-builder::scenebuilder-is-the-deterministic-requirements-to-spawn-materialization-layer")
    def test_scene_builder_module_stays_inside_the_deterministic_path_ban(self):
        import pathlib

        from world.quests import scene_builder

        source = pathlib.Path(scene_builder.__file__).read_text(encoding="utf-8").lower()
        for fragment in ("world.ai", "ollama", "llm_client"):
            self.assertNotIn(fragment, source)

    @covers_requirement("scene-builder::scenebuilder-is-the-deterministic-requirements-to-spawn-materialization-layer")
    def test_no_generative_module_imports_the_scene_builder(self):
        import ast
        from pathlib import Path

        ai_root = Path(__file__).resolve().parents[3] / "world" / "ai"
        for module_path in sorted(ai_root.rglob("*.py")):
            if "tests" in module_path.parts or "__init__.py" in module_path.parts:
                continue
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module and "scene_builder" in node.module:
                    self.fail(f"{module_path} imports {node.module}")

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_requirements_registry_is_written_only_by_the_compile_boundary(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        writers = []
        for path in sorted((repo / "world").rglob("*.py")):
            if "tests" in path.parts:
                continue
            if "SCENE_REQUIREMENT_REGISTRY" in path.read_text(encoding="utf-8"):
                writers.append(path.relative_to(repo).as_posix())
        self.assertEqual(writers, ["world/quests/compile.py"])

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_no_startup_resync_populates_generated_requirements(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        source = (repo / "server" / "conf" / "at_server_startstop.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("SCENE_REQUIREMENT_REGISTRY", source)
        self.assertNotIn("scene_builder", source)

    @covers_requirement("scene-builder::every-scene-builder-test-runs-offline-and-the-boundary-invariants-stay-green")
    def test_scene_builder_and_service_tests_never_construct_the_live_client(self):
        import pathlib

        repo = pathlib.Path(__file__).resolve().parents[3]
        for relative in (
            "world/quests/tests/test_scene_builder.py",
            "server/conf/tests/test_ai_director_service.py",
        ):
            source = (repo / relative).read_text(encoding="utf-8")
            client_constructor = "OpenAICompatClient" + "("
            socket_import = "import so" + "cket"
            socket_from = "from so" + "cket"
            self.assertNotIn(client_constructor, source, relative)
            self.assertNotIn(socket_import, source, relative)
            self.assertNotIn(socket_from, source, relative)


if __name__ == "__main__":
    unittest.main()
