"""Frozen art-panel view model tests (task 1.4).

Pure ``unittest.TestCase`` coverage for entity classification, combat vs
exploration selection, shared-roster ordering, dialogue-host and named-policy
filtering, catalog cap, and scene-archetype resolution. Uses lightweight fake
entities and actors; no Evennia session or database is required.
"""

from types import SimpleNamespace
import unittest

from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.rules.art_view import (
    MAX_PORTRAIT_CATALOG,
    ROLE_ALLY,
    ROLE_DIALOGUE,
    ROLE_FOE,
    ROLE_PERSON,
    SUBJECT_CHARACTER,
    SUBJECT_MONSTER,
    SUBJECT_NONE,
    ArtViewError,
    build_art_view,
    portrait_catalog_key,
)


def _entity(pk, name="entity", threat_tier=None, portrait_policy=None, dialogue=False):
    """One lightweight fake present entity."""
    db = SimpleNamespace(
        threat_tier=threat_tier,
        portrait_policy=portrait_policy,
    )
    if dialogue:

        class _Components:
            def has(self, name):
                return name == "scripted_dialogue"

            def get(self, slot):
                return object()

        components = _Components()
    else:
        components = None
    return SimpleNamespace(
        pk=pk,
        key=name,
        db=db,
        threat_tier=threat_tier,
        components=components,
    )


def _room(contents, scene_archetype=None):
    return SimpleNamespace(contents=contents, scene_archetype=scene_archetype)


def _actor(location=None, active_combat=None, pk=0):
    return SimpleNamespace(
        pk=pk,
        location=location,
        db=SimpleNamespace(active_combat=active_combat),
    )


def _resolver(entities_by_id):
    return lambda identity: entities_by_id.get(int(identity))


class ArtViewSelectionTests(unittest.TestCase):
    def setUp(self):
        self.room = _room([], scene_archetype="tavern_interior")
        self.actor = _actor(self.room)

    def test_combat_mode_uses_shared_roster_order(self):
        player = _entity(1, name="hero")
        goblin = _entity(2, name="goblin", threat_tier="low")
        wolf = _entity(3, name="wolf", threat_tier="low")
        entities = {1: player, 2: goblin, 3: wolf}
        record = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 99,
            "player_ids": [1],
            "enemy_ids": [2, 3],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        actor = _actor(self.room, active_combat=record)
        view = build_art_view(actor, resolver=_resolver(entities))
        self.assertEqual(view.scene_archetype, "tavern_interior")
        self.assertEqual(
            [(entity.identity, entity.role) for entity in view.entities],
            [(1, ROLE_ALLY), (2, ROLE_FOE), (3, ROLE_FOE)],
        )
        self.assertEqual(view.entities[0].subject_kind, SUBJECT_NONE)
        self.assertEqual(view.entities[1].subject_kind, SUBJECT_MONSTER)
        self.assertEqual(view.entities[2].subject_kind, SUBJECT_MONSTER)

    def test_exploration_mode_filters_dialogue_hosts_and_named_policy(self):
        host = _entity(10, name="innkeeper", dialogue=True)
        named = _entity(
            11, name="guard", portrait_policy={"mode": "named", "stable_key": "guard-1"}
        )
        policy_less = _entity(12, name="peasant")
        monster = _entity(13, name="rat", threat_tier="low")
        room = _room([policy_less, host, named, monster], scene_archetype="forest_path")
        actor = _actor(room)
        view = build_art_view(actor)
        # Deterministic identity-sorted order; only the host and the named
        # character appear. Monsters are not dialogue hosts and carry no policy.
        self.assertEqual(
            [(entity.identity, entity.role) for entity in view.entities],
            [(10, ROLE_DIALOGUE), (11, ROLE_PERSON)],
        )
        self.assertEqual(view.entities[0].subject_kind, SUBJECT_NONE)
        self.assertEqual(view.entities[1].subject_kind, SUBJECT_CHARACTER)
        self.assertEqual(view.scene_archetype, "forest_path")

    def test_actor_is_not_their_own_exploration_focusable_subject(self):
        # Even when the actor carries an explicit named portrait policy, they
        # never appear in their own exploration catalog.
        actor_named = _entity(
            60, name="hero", portrait_policy={"mode": "named", "stable_key": "hero-1"}
        )
        host = _entity(61, name="host", dialogue=True)
        room = _room([actor_named, host], scene_archetype="tavern_interior")
        view = build_art_view(_actor(room, pk=60))
        self.assertEqual([entity.identity for entity in view.entities], [61])

    def test_exploration_order_is_sorted_by_identity_not_contents(self):
        # The catalog order is stable regardless of the contents iteration
        # order, so payloads are deterministic across database states.
        host_high = _entity(90, name="host-b", dialogue=True)
        host_low = _entity(70, name="host-a", dialogue=True)
        room = _room([host_high, host_low], scene_archetype="forest_path")
        view = build_art_view(_actor(room))
        self.assertEqual([entity.identity for entity in view.entities], [70, 90])

    def test_named_policy_dialogue_host_wins_role(self):
        host = _entity(
            20,
            name="village_head",
            dialogue=True,
            portrait_policy={"mode": "named", "stable_key": "head-1"},
        )
        room = _room([host], scene_archetype="city_street")
        view = build_art_view(_actor(room))
        self.assertEqual(view.entities[0].role, ROLE_DIALOGUE)
        self.assertEqual(view.entities[0].subject_kind, SUBJECT_CHARACTER)

    def test_non_present_entity_is_excluded(self):
        # Only the actor's location contents are considered; an entity in
        # another room is simply never enumerated.
        host = _entity(30, name="host", dialogue=True)
        room = _room([host], scene_archetype="dungeon_interior")
        actor = _actor(room)
        other = _entity(31, name="elsewhere", dialogue=True)
        other.location = _room([], scene_archetype=None)
        view = build_art_view(actor)
        self.assertEqual([entity.identity for entity in view.entities], [30])

    def test_catalog_cap_truncates_deterministically(self):
        entities = [
            _entity(index, name=f"npc-{index}", dialogue=True)
            for index in range(1, MAX_PORTRAIT_CATALOG + 5)
        ]
        room = _room(entities, scene_archetype="shrine_interior")
        view = build_art_view(_actor(room))
        self.assertEqual(len(view.entities), MAX_PORTRAIT_CATALOG)
        self.assertEqual(
            [entity.identity for entity in view.entities],
            list(range(1, MAX_PORTRAIT_CATALOG + 1)),
        )

    def test_titled_entity_catalog_entry_stays_plain_key(self):
        # npc-title-identity-core compact-row pin: a stored title on the
        # entity (the fake carries the attribute the real NPC persists) must
        # not reach the portrait catalog entry.
        host = _entity(40, name="塞提斯", dialogue=True)
        host.npc_title = "南門守衛"
        room = _room([host], scene_archetype="city_street")
        view = build_art_view(_actor(room))
        self.assertEqual(view.entities[0].display_name, "塞提斯")
        self.assertNotIn("\u3000", view.entities[0].display_name)

    def test_combat_roster_cap_is_bounded_by_the_shared_query(self):
        player = _entity(1, name="hero")
        enemies = [
            _entity(index, name=f"enemy-{index}", threat_tier="low")
            for index in range(2, MAX_PORTRAIT_CATALOG + 3)
        ]
        entities = {entity.pk: entity for entity in [player, *enemies]}
        record = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 99,
            "player_ids": [1],
            "enemy_ids": [entity.pk for entity in enemies],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        actor = _actor(_room([], scene_archetype="cave_interior"), active_combat=record)
        view = build_art_view(actor, resolver=_resolver(entities))
        self.assertEqual(len(view.entities), MAX_PORTRAIT_CATALOG)
        self.assertEqual(
            [entity.identity for entity in view.entities],
            [1, *[entity.pk for entity in enemies]][:MAX_PORTRAIT_CATALOG],
        )

    def test_scene_archetype_none_and_invalid_resolve_to_none(self):
        room = _room([], scene_archetype=None)
        self.assertIsNone(build_art_view(_actor(room)).scene_archetype)
        room = _room([], scene_archetype="not_a_scene")
        self.assertIsNone(build_art_view(_actor(room)).scene_archetype)
        self.assertIsNone(build_art_view(_actor(location=None)).scene_archetype)

    def test_no_location_yields_empty_view(self):
        view = build_art_view(_actor(location=None))
        self.assertIsNone(view.scene_archetype)
        self.assertEqual(view.entities, ())

    def test_malformed_portrait_policy_is_treated_as_no_subject(self):
        bad = _entity(40, name="broken", portrait_policy="not-a-mapping")
        room = _room([bad], scene_archetype="ruin_interior")
        view = build_art_view(_actor(room))
        self.assertEqual(view.entities, ())
        self.assertEqual(view.scene_archetype, "ruin_interior")

    def test_overlong_display_name_raises_view_error(self):
        long_name = _entity(50, name="長" * 200, dialogue=True)
        room = _room([long_name], scene_archetype="forest_path")
        with self.assertRaises(ArtViewError):
            build_art_view(_actor(room))

    def test_combat_missing_entity_is_skipped(self):
        player = _entity(1, name="hero")
        record = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 99,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        actor = _actor(_room([], scene_archetype="forest_path"), active_combat=record)
        view = build_art_view(actor, resolver=_resolver({1: player}))
        self.assertEqual([entity.identity for entity in view.entities], [1])


class PortraitCatalogKeyTests(unittest.TestCase):
    def test_key_is_the_bounded_decimal_string_form(self):
        self.assertEqual(portrait_catalog_key(42), "42")
        self.assertEqual(portrait_catalog_key("42"), "42")
        self.assertEqual(portrait_catalog_key(1), "1")
        self.assertNotEqual(portrait_catalog_key(42), 42)
        self.assertEqual(portrait_catalog_key(0), "0")


if __name__ == "__main__":
    unittest.main()
