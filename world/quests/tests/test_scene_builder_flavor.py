"""Scene flavor context and apply tests (deterministic flavor seam).

Covers ``SceneFlavorContextAndApplyTests``: the deterministic flavor-context
seam for fresh instance scenes and the idempotent sole-writer flavor apply.
The shared base is imported from ``test_scene_builder`` (single fixed home).
"""
from unittest.mock import patch
import unittest

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.rooms import InstanceRoom

from world.quests.scene_builder import apply_scene_flavor, materialize_stage
from world.quests.tests.test_scene_builder import (
    SceneBuilderTestBase,
    _instance_bound_payload,
    _reach_anchor_payload,
)

from tools.spec_traceability import covers_requirement

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
if __name__ == "__main__":
    unittest.main()
