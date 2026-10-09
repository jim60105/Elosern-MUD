"""Synthetic normal-person identity, lineage, rollback and connected routine behavior."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from typeclasses.exits import Exit
from world.lore.guild_adventurers import GuildAdventurer, ExamQualification
from world.lore.items import EquipmentModifierKey
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines
from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.rules import human_guild_hosts as hosts, npc_schedules as schedules
from world.rules.action import ActionRequest, ActionResolver
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.progression import can_use_skill
from world.skills.registry import SkillKind, SkillPrerequisite
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import make_item, make_skill, synthetic_registries


class PersistentHumanGuildHostTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.home = create_object(Room, key="t_home")
        self.frontage = create_object(Room, key="t_frontage")
        self.guild = create_object(Room, key="t_guild")
        for source, target in ((self.home, self.frontage), (self.frontage, self.guild),
                               (self.guild, self.frontage), (self.frontage, self.home)):
            create_object(Exit, key=f"t_to_{target.pk}", location=source, destination=target)
        self.skill = make_skill("t_host_top", effects=[], cost={},
                                prerequisites=(SkillPrerequisite("t_host_root", 5),))
        root = make_skill("t_host_root", effects=[], cost={}, prerequisites=())
        passive = make_skill("t_host_passive", kind=SkillKind.PASSIVE, effects=[], cost={}, prerequisites=())
        modifier_key = next(iter(EquipmentModifierKey))
        sword = make_item("t_host_sword", equipment_slot=EquipmentSlot.WEAPON_MAIN, modifier_key=modifier_key)
        armor = make_item("t_host_armor", equipment_slot=EquipmentSlot.ARMOR, modifier_key=modifier_key)
        scope = synthetic_registries("items", "skills", extra={
            "skills": {row.key: row for row in (root, self.skill, passive)},
            "items": {row.key: row for row in (sword, armor)},
        })
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        card = NpcCard(identity=NpcCardIdentity(public="街屋裡的旅人"),
                       appearance="灰髮，穿旅行外衣。", personality="沉穩。",
                       speech_style="語調平緩。", life_story="在港口長大。",
                       habit="睡前讀書。", social_connection="認識街坊。")
        self.profile = NpcProfile("t_host_profile", card, age=42, apparent_age=39,
                                 voice=NpcVoiceLines(greeting="「來坐吧。」", misunderstood="「再說一次吧。」"))
        self.person = GuildAdventurer(
            "t_person", "合成旅人", "旅人", self.profile.key, "t_home", "t_rank",
            "human_plains", (150, 120, 120, 15, 15, 15, 25), self.skill.key,
            (sword.key, armor.key), "t_person_weekly",
            branch_key="t_branch",
        )
        self.people = {self.person.key: self.person}
        self.profiles = {self.profile.key: self.profile}
        self.bindings = (ExamQualification("t_branch", "t_rank", self.person.key),)
        template = schedules.ScheduleTemplate(
            key="t_person_weekly", default_state="duty", cycle_days=7,
            entries=(schedules.ScheduleEntry(10, "move", target="frontage"),
                     schedules.ScheduleEntry(40, "move", target="guild"),
                     schedules.ScheduleEntry(70, "move", target="frontage"),
                     schedules.ScheduleEntry(100, "move", target="home")),
        )
        home_place = PlaceDefinition("t_home", "t_settlement", PlaceKind.HOME,
                                     "合成住家", "小屋", (1, 1), "住家", ())
        for target, value in (
            ("world.lore.guild.GUILD_RANK_REGISTRY", {"t_rank": object()}),
            ("world.lore.guild.GUILD_BRANCH_REGISTRY", {"t_branch": object()}),
            ("world.lore.settlements.places.PLACE_REGISTRY", {"t_home": home_place}),
            ("world.rules.human_guild_hosts.UTILITY_SKILLS", ("t_host_passive",)),
            ("world.rules.npc_schedules._RULEBOOK", schedules.ScheduleRulebook(1, ("duty", "resting", "busy"), (template,))),
        ):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(hosts, "resolve_residence_route", return_value={
            "home": self.home, "frontage": self.frontage, "guild": self.guild,
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        schedules.get_world_clock().tick = 0

    def sync(self):
        return hosts.sync_persistent_adventurers(people=self.people, profiles=self.profiles,
                                               qualifications=self.bindings)

    @covers_requirement(
        "human-guild-hosts::altoria-qualifications-select-one-persistent-adventurer-per-branch-and-target"
    )
    def test_occupied_key_is_suffixed_once_and_reuse_preserves_all_live_state(self):
        create_object(NPC, key=self.person.name, location=self.room1)
        host, = self.sync()
        identity = (host.pk, host.key)
        self.assertEqual(host.key, f"{self.person.name}-{host.pk}")
        host.location = self.guild
        host.db.persona = {"identity": {"public": "edited"}}
        host.db.inventory = []
        host.db.active_combat = {"exam": "synthetic"}
        host.db.schedule_state = "busy"
        before = (host.db.persona, host.db.inventory, host.db.active_combat, host.db.schedule)
        again, = self.sync()
        self.assertEqual((again.pk, again.key), identity)
        self.assertEqual(again.location, self.guild)
        self.assertEqual((again.db.persona, again.db.inventory, again.db.active_combat, again.db.schedule), before)
        self.assertEqual(again.db.schedule_state, "busy")
        self.assertEqual(again.attributes.get(hosts.PERSON_ATTRIBUTE), self.person.key)

    @covers_requirement(
        "human-guild-hosts::normal-hosts-own-literal-bases-gear-and-usable-complete-human-skill-lineages"
    )
    def test_normal_lineage_has_prerequisites_and_resolver_accepts_top_skill(self):
        host, = self.sync()
        self.assertTrue(can_use_skill(host, self.skill))
        self.assertIn("t_host_root", host.db.skills["active"])
        self.assertIn("t_host_passive", host.db.skills["passive"])
        self.assertNotIn("t_host_passive", host.db.skills["active"])
        target = create_object(NPC, key="t_target", location=self.home)
        target.race = "human"
        target.apply_race_baseline()
        context = BattlefieldActionContext(Battlefield(
            teams={"hosts": frozenset({host.key}), "targets": frozenset({target.key})},
            roster={host.key: host, target.key: target},
        ))
        result = ActionResolver.preflight(ActionRequest(host, self.skill.key, [target], context))
        self.assertNotEqual(result.outcome, "rejected", result.reason)
        self.assertEqual(host.db.equipment["weapon_main"], "t_host_sword")
        self.assertEqual(host.db.equipment["armor"], "t_host_armor")
        self.assertEqual((host.db.age, host.db.apparent_age), (42, 39))

    @covers_requirement(
        "human-guild-hosts::altoria-qualifications-select-one-persistent-adventurer-per-branch-and-target"
    )
    def test_qualification_selects_actual_person_when_hosts_colocate_and_fails_closed(self):
        for index in (1, 2):
            profile = replace(self.profile, key=f"t_other_profile_{index}")
            self.profiles[profile.key] = profile
            person = replace(self.person, key=f"t_other_person_{index}",
                             name=f"合成旅人{index}", profile_key=profile.key)
            self.people[person.key] = person
            self.bindings += (ExamQualification("t_branch", f"t_other_rank_{index}", person.key),)
        with patch("world.lore.guild.GUILD_RANK_REGISTRY", {
            key: object() for key in ("t_rank", "t_other_rank_1", "t_other_rank_2")
        }):
            normal_hosts = self.sync()
        for host in normal_hosts:
            host.location = self.guild
        create_object(NPC, key="t_unqualified", location=self.guild)
        selected = hosts.qualified_host("t_branch", "t_other_rank_1",
                                       people=self.people, qualifications=self.bindings)
        self.assertEqual(selected.pk, normal_hosts[1].pk)
        self.assertEqual(selected.location, self.guild)
        for branch, bindings in (("t_other", self.bindings), ("t_branch", self.bindings * 2),
                                 ("t_branch", (replace(self.bindings[0], person_key="t_missing"),))):
            with self.subTest(branch=branch, bindings=bindings):
                with self.assertRaises(hosts.GuildHostIntegrityError):
                    hosts.qualification_for(branch, "t_rank", people=self.people, qualifications=bindings)
        with self.assertRaises(hosts.GuildHostIntegrityError):
            hosts.qualification_for("t_other", "t_rank", people=self.people,
                                    qualifications=(replace(self.bindings[0], branch_key="t_other"),))

    @covers_requirement(
        "human-guild-hosts::normal-hosts-own-literal-bases-gear-and-usable-complete-human-skill-lineages"
    )
    def test_invalid_age_gear_voice_or_duplicate_person_rejects_before_creation(self):
        before = NPC.objects.all_family().count()
        for bad in (True, -1, 10001):
            self.profiles[self.profile.key] = SimpleNamespace(**{**vars(self.profile), "age": bad})
            with self.assertRaises(hosts.GuildHostIntegrityError):
                self.sync()
        self.profiles[self.profile.key] = self.profile
        self.people[self.person.key] = replace(self.person, equipment=("t_unknown_item",))
        with self.assertRaises(hosts.GuildHostIntegrityError):
            self.sync()
        self.people[self.person.key] = self.person
        self.profiles[self.profile.key] = replace(self.profile, voice=NpcVoiceLines(greeting="hello"))
        with self.assertRaises(hosts.GuildHostIntegrityError):
            self.sync()
        self.assertEqual(NPC.objects.all_family().count(), before)
        self.profiles[self.profile.key] = self.profile
        host, = self.sync()
        duplicate = create_object(NPC, key="t_duplicate", location=self.home)
        duplicate.attributes.add(hosts.PERSON_ATTRIBUTE, self.person.key)
        before = (host.location, host.db.persona)
        with self.assertRaises(hosts.GuildHostIntegrityError):
            self.sync()
        self.assertEqual((host.location, host.db.persona), before)

    @covers_requirement(
        "human-guild-hosts::hosts-live-in-connected-residences-and-traverse-authored-recurring-guild-visits"
    )
    def test_connected_weekly_occurrences_traverse_real_exits_and_repeat(self):
        host, = self.sync()
        for start, end, destination in ((0, 10, self.frontage), (10, 40, self.guild),
                                        (40, 70, self.frontage), (70, 100, self.home),
                                        (100, 604810, self.frontage), (604810, 604840, self.guild)):
            events = schedules.settle_npc_schedules(start, end)
            self.assertEqual(host.location, destination)
            self.assertEqual([event.kind for event in events], ["npc_departed", "npc_arrived"])
            self.assertEqual(host.db.schedule_state, "duty")

    @covers_requirement(
        "human-guild-hosts::hosts-live-in-connected-residences-and-traverse-authored-recurring-guild-visits"
    )
    def test_locked_weekly_arrival_remains_absent_with_no_teleport(self):
        host, = self.sync()
        schedules.settle_npc_schedules(0, 10)
        arrival = next(exit_obj for exit_obj in self.frontage.exits if exit_obj.destination == self.guild)
        arrival.locks.add("traverse:false()")
        before = (host.location, host.db.schedule_state)
        events = schedules.settle_npc_schedules(10, 40)
        self.assertEqual(events, [])
        self.assertEqual((host.location, host.db.schedule_state), before)
        self.assertNotEqual(host.location, self.guild)

    def test_creation_failure_rolls_back_identity_and_gear(self):
        before = NPC.objects.all_family().count()
        with patch.object(hosts, "set_npc_schedule", side_effect=RuntimeError("synthetic write failure")):
            with self.assertRaises(RuntimeError):
                self.sync()
        self.assertEqual(NPC.objects.all_family().count(), before)
        self.assertIsNone(hosts.find_persistent_adventurer(self.person.key))
