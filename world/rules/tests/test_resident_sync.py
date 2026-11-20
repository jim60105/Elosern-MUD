"""Behavior tests: the resident sync constructs chat-only persistent residents.

Every row, profile and dialogue table is fixture-owned (``t_`` keys under a
scoped synthetic race registry); no test pins a shipped village, room or
person. The assertions cover construction, the complete card, literal traits
and sex, the absence of every managed service capability, home placement and
schedule assignment, idempotent reuse that preserves player edits, duplicate
identity rejection, and wholesale rollback.
"""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit
from typeclasses.npcs import LLMNPC
from typeclasses.rooms import Room
from world.lore.dialogue.conditions import RaceIs
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    DialogueDefinition,
    KeywordResponse,
)
from world.lore.scenes import Scene, Speech
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines
from world.lore.residents import Resident
from world.rules import resident_sync
from world.rules.guild_economy import ServiceHostIntegrityError, _find_service_host
from world.rules.npc_capabilities import COMPONENT_TYPES
from world.rules.npc_schedules import get_world_clock, settle_npc_schedules
from world.rules.npc_services import inspect_npc_services
from world.rules.dialogue_availability import (
    TOPIC_LOCKED,
    TOPIC_OPEN,
    availability_context,
    project_topics,
)
from world.rules.resident_sync import RESIDENT_ATTRIBUTE, ResidentSyncError, sync_residents
from world.tests.synthetic_data import synthetic_registries

_STATS = {
    "hp": 130,
    "mp": 110,
    "sp": 120,
    "atk_phys": 11,
    "agility": 12,
    "defense": 13,
    "magic_power": 40,
}


_TABLE = DialogueDefinition(
    greeting="t-table-greeting",
    responses=(KeywordResponse("t-keyword", "t-response"),),
)


def _scene(scene_id: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(Speech("actor", "t-actor-line"), Speech("host", "t-host-line")),
    )


_TOPIC_TABLE = AuthoredDialogue(
    greeting="t-topic-greeting",
    topics=(
        AuthoredTopic(
            topic_id="t_resident_topics.topic_01",
            keyword="t-open",
            label="t-open",
            fallback=_scene("t_resident_topics.topic_01_scene"),
        ),
        AuthoredTopic(
            topic_id="t_resident_topics.topic_02",
            keyword="t-hidden",
            label="t-hidden",
            fallback=_scene("t_resident_topics.topic_02_scene"),
            requires=RaceIs("t_duskmari"),
            unavailable="hidden",
        ),
        AuthoredTopic(
            topic_id="t_resident_topics.topic_03",
            keyword="t-locked",
            label="t-locked",
            fallback=_scene("t_resident_topics.topic_03_scene"),
            requires=RaceIs("t_duskmari"),
            unavailable="locked",
            refusal=_scene("t_resident_topics.topic_03_refusal"),
        ),
    ),
)


def _synthetic_scope():
    return synthetic_registries(
        "races",
        "subraces",
        "dialogue",
        extra={
            "dialogue": {
                "t_resident_table": _TABLE,
                "t_resident_topics": _TOPIC_TABLE,
            }
        },
    )


def _card() -> NpcCard:
    return NpcCard(
        identity=NpcCardIdentity(public="t-public", hidden=""),
        appearance="t-appearance",
        personality="t-personality",
        speech_style="t-speech-style",
        life_story="t-life-story",
        habit="t-habit",
        social_connection="",
    )


def _profile(key: str, *, greeting: str | None) -> NpcProfile:
    return NpcProfile(
        key=key,
        card=_card(),
        age=40,
        apparent_age=41,
        voice=NpcVoiceLines(greeting=greeting, misunderstood="t-misunderstood"),
    )


def _resident(key: str, profile_key: str, *, home: str, **overrides) -> Resident:
    fields = {
        "key": key,
        "name": key.replace("_", "-"),
        "profile_key": profile_key,
        "race": "t_duskmari",
        "subrace": "t_duskmari_evensong",
        "sex": "female",
        "stats": dict(_STATS),
        "home_room": home,
    }
    fields.update(overrides)
    return Resident(**fields)


class ResidentSyncTests(EvenniaTest):
    """One authored resident is materialized once, completely, and safely."""

    def setUp(self):
        super().setUp()
        self.scope = _synthetic_scope()
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        get_world_clock().tick = 0
        self.home = create_object(Room, key="t-home", tags=["t_home"])
        self.public = create_object(Room, key="t-public-square")
        self.frontage = create_object(Room, key="t-frontage")
        self.routes = {
            "t_home": {
                "home": self.home,
                "public": self.public,
                "frontage": self.frontage,
            }
        }
        self.route_patch = patch.object(
            resident_sync,
            "resolve_public_route",
            side_effect=lambda home_room, settlement, node: self.routes[home_room],
        )
        self.route_patch.start()
        self.addCleanup(self.route_patch.stop)

    def _sync(self, residents, profiles, dialogue_rows=None, public_nodes=None):
        return sync_residents(
            residents=residents,
            profiles=profiles,
            dialogue_rows=dialogue_rows or {},
            public_nodes=public_nodes or {"t_hollow_tarn": "t_public_node"},
        )

    def test_first_sync_creates_a_complete_chat_only_resident(self):
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        (host,) = self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})

        self.assertIsInstance(host, LLMNPC)
        self.assertIs(host.location, self.home)
        self.assertEqual(host.attributes.get(RESIDENT_ATTRIBUTE), "t_resident_a")
        self.assertEqual((host.race, host.subrace, host.sex), ("t_duskmari", "t_duskmari_evensong", "female"))
        self.assertEqual((host.db.age, host.db.apparent_age), (40, 41))
        card = host.db.persona
        self.assertEqual(
            set(card),
            {"identity", "appearance", "personality", "speech_style", "life_story", "habit", "social_connection"},
        )
        for stat_key, expected in _STATS.items():
            self.assertEqual(host.traits[stat_key].base, expected, stat_key)
        for type_key, component_class in COMPONENT_TYPES.items():
            self.assertIsNone(
                host.components.get(component_class.get_component_slot()),
                f"resident carries managed component {type_key}",
            )

    def test_a_dialogue_key_attaches_one_unbound_scripted_table(self):
        profile = _profile("t_resident_profile", greeting=None)
        resident = _resident(
            "t_resident_a",
            "t_resident_profile",
            home="t_home",
            dialogue_key="t_resident_table",
        )
        (host,) = self._sync(
            {"t_resident_a": resident},
            {"t_resident_profile": profile},
            dialogue_rows={"t_resident_table": _TABLE},
        )
        live = host.components.get("scripted_dialogue")
        self.assertIsNotNone(live)
        self.assertEqual(live.dialogue_key, "t_resident_table")
        self.assertIsNone(live.service_binding)
        self.assertIsNone(live.anchor_room_id)

    def test_a_new_resident_starts_home_and_walks_the_schedule(self):
        create_object(Exit, key="out", location=self.home, destination=self.public)
        create_object(Exit, key="in", location=self.public, destination=self.home)
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        (host,) = self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})

        self.assertIs(host.location, self.home)
        schedule = host.db.schedule
        self.assertEqual(schedule["template"], "resident")
        self.assertEqual(schedule["overrides"]["0"]["target"], self.public.dbref)
        self.assertEqual(schedule["overrides"]["2"]["target"], self.home.dbref)

        settle_npc_schedules(0, 25200)
        self.assertIs(host.location, self.public)
        settle_npc_schedules(25200, 61200)
        self.assertIs(host.location, self.home)

    def test_resync_reuses_the_resident_and_preserves_edits(self):
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        (first,) = self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        first.db.persona = dict(first.db.persona, appearance="t-player-edited")
        away = create_object(Room, key="t-away")
        first.location = away
        first.save()

        (second,) = self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        self.assertEqual(second.pk, first.pk)
        self.assertIs(second.location, away)
        self.assertEqual(second.db.persona["appearance"], "t-player-edited")
        self.assertEqual(
            len(
                [
                    npc
                    for npc in LLMNPC.objects.all_family()
                    if npc.attributes.get(RESIDENT_ATTRIBUTE)
                ]
            ),
            1,
        )

    def test_two_live_npcs_claiming_one_identity_reject_before_any_write(self):
        create_object(LLMNPC, key="t-one").attributes.add(RESIDENT_ATTRIBUTE, "t_resident_a")
        create_object(LLMNPC, key="t-two").attributes.add(RESIDENT_ATTRIBUTE, "t_resident_a")
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        with self.assertRaises(ResidentSyncError) as caught:
            self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        self.assertIn("t_resident_a", str(caught.exception))
        self.assertEqual(
            len(
                [
                    npc
                    for npc in LLMNPC.objects.all_family()
                    if npc.attributes.get(RESIDENT_ATTRIBUTE) == "t_resident_a"
                ]
            ),
            2,
        )

    def test_a_resident_profile_owned_by_another_npc_rejects_before_any_write(self):
        other = create_object(LLMNPC, key="t-other")
        other.attributes.add("npc_profile_key", "t_resident_profile")
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        with self.assertRaises(ResidentSyncError) as caught:
            self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        self.assertIn("t_resident_profile", str(caught.exception))
        self.assertFalse(LLMNPC.objects.filter(db_key="t-resident-a").exists())

    def test_an_unresolved_room_rejects_before_any_write(self):
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_missing")
        with self.assertRaises(KeyError):
            self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        self.assertFalse(LLMNPC.objects.filter(db_key="t-resident-a").exists())

    def test_a_write_failure_rolls_back_every_created_resident(self):
        first = _resident("t_resident_a", "t_resident_profile_a", home="t_home")
        second = _resident("t_resident_b", "t_resident_profile_b", home="t_home")
        profiles = {
            "t_resident_profile_a": _profile("t_resident_profile_a", greeting="t-greeting-a"),
            "t_resident_profile_b": _profile("t_resident_profile_b", greeting="t-greeting-b"),
        }
        real = resident_sync.set_npc_schedule
        calls = []

        def fail_second(host, schedule):
            calls.append(host.pk)
            if len(calls) == 2:
                raise ResidentSyncError("t-write-failure")
            return real(host, schedule)

        with patch.object(resident_sync, "set_npc_schedule", side_effect=fail_second):
            with self.assertRaises(ResidentSyncError):
                self._sync(
                    {"t_resident_a": first, "t_resident_b": second},
                    profiles,
                )
        self.assertFalse(
            any(
                npc.attributes.get(RESIDENT_ATTRIBUTE)
                for npc in LLMNPC.objects.all_family()
            )
        )
        self.assertEqual(list(self.home.contents), [])
        # The evicted instances leave no stale identity-map entry behind: the
        # same batch syncs cleanly on retry.
        retried = self._sync(
            {"t_resident_a": first, "t_resident_b": second}, profiles
        )
        self.assertEqual(len(retried), 2)
        self.assertEqual(
            [host.location for host in retried], [self.home, self.home]
        )

    def test_service_host_lookup_refuses_an_authored_resident(self):
        host = create_object(LLMNPC, key="t-resident")
        host.attributes.add("npc_profile_key", "t_shared_profile")
        host.attributes.add(RESIDENT_ATTRIBUTE, "t_resident_a")
        with self.assertRaises(ServiceHostIntegrityError):
            _find_service_host("t_shared_profile")

    def test_a_locked_topic_discloses_only_its_label_and_refusal(self):
        profile = _profile("t_resident_profile", greeting=None)
        resident = _resident(
            "t_resident_a",
            "t_resident_profile",
            home="t_home",
            dialogue_key="t_resident_topics",
        )
        (host,) = self._sync(
            {"t_resident_a": resident},
            {"t_resident_profile": profile},
            dialogue_rows={"t_resident_topics": _TOPIC_TABLE},
        )
        self.char1.race = "t_starlit"
        self.char1.location = self.home
        self.char1.save()

        context = availability_context(self.char1, host)
        before = {row.topic_id: row for row in project_topics(context)}
        self.assertEqual(set(before), {"t_resident_topics.topic_01", "t_resident_topics.topic_03"})
        self.assertEqual(before["t_resident_topics.topic_01"].availability, TOPIC_OPEN)
        self.assertEqual(before["t_resident_topics.topic_03"].availability, TOPIC_LOCKED)

        self.char1.race = "t_duskmari"
        self.char1.save()
        after = {row.topic_id: row for row in project_topics(context)}
        self.assertEqual(
            set(after),
            {
                "t_resident_topics.topic_01",
                "t_resident_topics.topic_02",
                "t_resident_topics.topic_03",
            },
        )
        self.assertTrue(all(row.availability == TOPIC_OPEN for row in after.values()))
        self.assertEqual(inspect_npc_services(host).entries, ())

    def test_two_residents_cannot_share_one_dialogue_table(self):
        profiles = {
            "t_resident_profile_a": _profile("t_resident_profile_a", greeting=None),
            "t_resident_profile_b": _profile("t_resident_profile_b", greeting=None),
        }
        residents = {
            "t_resident_a": _resident(
                "t_resident_a",
                "t_resident_profile_a",
                home="t_home",
                dialogue_key="t_resident_topics",
            ),
            "t_resident_b": _resident(
                "t_resident_b",
                "t_resident_profile_b",
                home="t_home",
                dialogue_key="t_resident_topics",
            ),
        }
        with self.assertRaises(ResidentSyncError) as caught:
            self._sync(
                residents,
                profiles,
                dialogue_rows={"t_resident_topics": _TOPIC_TABLE},
            )
        message = str(caught.exception)
        self.assertIn("t_resident_a", message)
        self.assertIn("t_resident_b", message)
        self.assertIn("t_resident_topics", message)
        self.assertFalse(
            any(
                npc.attributes.get(RESIDENT_ATTRIBUTE)
                for npc in LLMNPC.objects.all_family()
            )
        )

    def test_a_reused_resident_carrying_a_service_component_rejects(self):
        from typeclasses.components import GuildStaff
        from world.rules.npc_capabilities import COMPONENT_TYPES

        staff_type_key = next(
            type_key
            for type_key, component_class in COMPONENT_TYPES.items()
            if component_class is GuildStaff
        )
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        (host,) = self._sync(
            {"t_resident_a": resident}, {"t_resident_profile": profile}
        )
        host.components.add(
            GuildStaff.create(host, service_id="t_staff_service", branch_key="t_branch")
        )
        host.save()

        with self.assertRaises(ResidentSyncError) as caught:
            self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        message = str(caught.exception)
        self.assertIn("t_resident_a", message)
        self.assertIn(staff_type_key, message)

    def test_a_reused_resident_tagged_as_a_service_host_rejects(self):
        profile = _profile("t_resident_profile", greeting="t-greeting")
        resident = _resident("t_resident_a", "t_resident_profile", home="t_home")
        (host,) = self._sync(
            {"t_resident_a": resident}, {"t_resident_profile": profile}
        )
        host.tags.add("service_host", category="content_source")

        with self.assertRaises(ResidentSyncError) as caught:
            self._sync({"t_resident_a": resident}, {"t_resident_profile": profile})
        self.assertIn("service host", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
