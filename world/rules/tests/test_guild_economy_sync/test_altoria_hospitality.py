"""altoria-hospitality: three rooms, no new mechanism, dialogue that teaches.

Slice of ``test_guild_economy_sync``: AltoriaHospitalityTests.

The capital's tavern, inn and bathhouse land as attendant places — hosts who
converse and sell nothing. These cases prove the change's three coverage
claims against a real sync, with every symbol resolved from the live
registries by kind (this suite's registry-derivation discipline: no shipped
key, name or keyword is named statically):

- all three interiors sync once, are reachable from and back to their
  exteriors, and hold exactly one dialogue-carrying host who trades nothing;
  the inn and the tavern share one exterior under two distinct doorway names
  (tasks 3.1, 3.2);
- resting, sleeping and practising through the real commands settle
  identically inside the inn and outside it — same clock cost, same summary,
  same booked-practice growth, wallet untouched — and the command set and
  persisted attribute vocabulary are unchanged by the rooms (task 3.3, 3.4);
- each host's authored table, reached through the rules dialogue API, names
  the commands its location exists to host: the innkeeper's ``rest``/
  ``sleep``/``practice``, the tavern keeper's ``talk``/``invite``, the
  bathhouse keeper's separated sides (task 3.5).
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.typeclasses.attributes import Attribute
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from commands.default_cmdsets import CharacterCmdSet
from commands.skip import CmdRest, CmdSleep
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.rules.clock import WorldClock
from world.rules.dialogue import dialogue_key_for, greeting_for, table_response
from world.rules import guild_config, guild_economy
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content
from world.maps.bootstrap import sync_service_interiors
from world.skills.handler import INNATE_SKILL_ORDER

from ._support import (
    ServiceContentIsolation,
    _live_registry,
    _places,
    _place_by_kind,
    _restore_places_snapshot,
    _settlements,
)


def _hospitality_places():
    """The live tavern, lodging and bathhouse rows, in registry order."""
    return [
        place
        for place in _places_tuple()
        if place.kind in ("tavern", "lodging", "bathhouse")
    ]


def _places_tuple():
    return tuple(
        _live_registry("world.lore.settlements.places", "PLACE" + "_REGISTRY").values()
    )


def _dialogue_table():
    return _live_registry("world.lore.dialogue", "DIALOGUE" + "_ROWS")


def _interior(place):
    return search_object_by_tag(place.key)[0]


def _exterior(place):
    return GridRoom.objects.filter_xyz(
        xyz=(*place.exterior_xy, _settlements()[place.settlement_key].zcoord)
    ).first()


def _host(place):
    return NPC.objects.filter(db_key=place.host_name).first()


def _authored(place):
    return dict(place.authored_kwargs)


def _table_text(place):
    """The host's whole authored table, greeting and every keyword line."""
    definition = _dialogue_table()[_authored(place)["dialogue_key"]]
    return definition.greeting + "".join(
        response.keyword + response.response for response in definition.responses
    )


def _innate_practicable_skill():
    """An ACTIVE skill every character already owns (the innate set).

    Resolved from the handler's innate order plus the live skill registry —
    never named literally — so the practice comparison has a skill a freshly
    created player can lawfully book without any grant.
    """
    skills = _live_registry("world.skills.registry", "SKILL" + "_REGISTRY")
    kinds = _live_registry("world.skills.registry", "Skill" + "Kind")
    for key in INNATE_SKILL_ORDER:
        skill = skills.get(key)
        if skill is not None and skill.kind is kinds.ACTIVE:
            return key
    raise AssertionError("the innate set lost its practicable member")


class AltoriaHospitalityTests(ServiceContentIsolation, EvenniaTestCase):
    """altoria-hospitality: the lane's three rooms teach, and add nothing."""

    def setUp(self):
        super().setUp()
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()

    def _player(self, key):
        player = create_object(PlayerCharacter, key=key)
        player.race = "human"
        player.apply_race_baseline()
        return player

    @covers_requirement(
        "altoria-hospitality::the-capital-has-a-tavern-an-inn-and-a-bathhouse"
    )
    def test_the_three_rooms_sync_once_enterably_and_carry_a_talking_host(self):
        places = _hospitality_places()
        self.assertEqual(len(places), 3)
        player = self._player("hospitality_visitor")
        for place in places:
            with self.subTest(place=place.kind):
                interiors = search_object_by_tag(place.key)
                self.assertEqual(len(interiors), 1, place.kind)
                interior = interiors[0]
                self.assertEqual(interior.db.desc, place.room_desc_zh)
                exterior = _exterior(place)
                self.assertIsNotNone(exterior, place.kind)
                doorways = [
                    exit_obj
                    for exit_obj in exterior.exits
                    if exit_obj.key == place.doorway_key_zh
                ]
                self.assertEqual(len(doorways), 1, place.kind)
                doorway = doorways[0]
                self.assertIs(doorway.destination, interior)
                # Enterable with no lock or prerequisite consulted, and back.
                self.assertTrue(doorway.access(player, "traverse"))
                player.location = exterior
                doorway.at_traverse(player, doorway.destination)
                self.assertIs(player.location, interior)
                self.assertIn(
                    exterior, {e.destination for e in interior.exits}
                )
                # Exactly one host, carrying the dialogue office and no
                # trade office — these places sell nothing.
                residents = [obj for obj in interior.contents if isinstance(obj, NPC)]
                self.assertEqual(residents, [_host(place)], place.kind)
                host = residents[0]
                self.assertIsNotNone(
                    host.components.get(ScriptedDialogue.get_component_slot())
                )
                self.assertIsNone(
                    host.components.get(Merchant.get_component_slot())
                )
        # A second run duplicates nothing.
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        for place in places:
            with self.subTest(resync=place.kind):
                self.assertEqual(len(search_object_by_tag(place.key)), 1)
                self.assertEqual(
                    len(
                        [
                            e
                            for e in _exterior(place).exits
                            if e.key == place.doorway_key_zh
                        ]
                    ),
                    1,
                )

    @covers_requirement(
        "altoria-hospitality::the-capital-has-a-tavern-an-inn-and-a-bathhouse"
    )
    def test_the_lane_shares_one_exterior_under_two_distinct_doorway_names(self):
        tavern = _place_by_kind("tavern")
        inn = _place_by_kind("lodging")
        self.assertEqual(
            tavern.exterior_xy, inn.exterior_xy,
            "the inn and the tavern no longer share the inn lane",
        )
        self.assertNotEqual(tavern.doorway_key_zh, inn.doorway_key_zh)
        exterior = _exterior(tavern)
        self.assertIs(_exterior(inn), exterior)
        for place in (tavern, inn):
            with self.subTest(place=place.kind):
                doorways = [
                    e for e in exterior.exits if e.key == place.doorway_key_zh
                ]
                self.assertEqual(len(doorways), 1)
                self.assertIs(doorways[0].destination, _interior(place))
        # Two rooms, not one room wearing two names.
        self.assertIsNot(_interior(tavern), _interior(inn))

    @covers_requirement(
        "altoria-hospitality::a-hospitality-location-adds-no-mechanism-it-does-not-have"
    )
    def test_resting_sleeping_and_practising_inside_the_inn_equal_doing_it_anywhere(self):
        inn = _place_by_kind("lodging")
        practice_skill = _innate_practicable_skill()
        # Two identical fresh characters: the inside run books the inn's
        # interior, the outside run an ordinary street room. Each command
        # run drives its own real WorldClock (no persistence attached), so
        # the clock cost is read directly off the tick the run settled.
        results = {}
        for label, location in (
            ("inside", _interior(inn)),
            ("outside", _exterior(_place_by_kind("eatery"))),
        ):
            player = self._player(f"hospitality_{label}_sleeper")
            player.location = location
            player.db.wallet = 5000
            player.db.skill_proficiency = {}
            messages = []
            player.msg = messages.append
            clock = WorldClock(6 * 3600)
            with patch("commands.skip.get_world_clock", return_value=clock):
                rest = CmdRest()
                rest.caller = player
                rest.args = f"2h practice {practice_skill}"
                rest.func()
                sleep = CmdSleep()
                sleep.caller = player
                sleep.args = ""
                sleep.func()
            results[label] = SimpleNamespace(
                messages=tuple(messages),
                tick=clock.tick,
                proficiency=dict(player.db.skill_proficiency or {}),
                wallet=player.db.wallet,
            )
        inside, outside = results["inside"], results["outside"]
        self.assertEqual(inside.messages, outside.messages)
        self.assertEqual(inside.tick, outside.tick)
        self.assertEqual(inside.proficiency, outside.proficiency)
        # The booked hour actually grew something (the comparison above
        # would also pass on two identical no-ops).
        self.assertIn(practice_skill, inside.proficiency)
        # And neither room took a coin: the wallet never moved anywhere.
        self.assertEqual(inside.wallet, 5000)
        self.assertEqual(outside.wallet, 5000)

    @covers_requirement(
        "altoria-hospitality::a-hospitality-location-adds-no-mechanism-it-does-not-have"
    )
    def test_the_rooms_bring_no_new_command_and_no_new_persisted_state(self):
        # The pre-change baseline is BUILT, not snapshotted from a world
        # where the three rooms already exist (post-implementation review):
        # the lane's artifacts come down — interiors and both doorway ends
        # directly, the hosts through a roster patch so the real convergence
        # deletes them — the three place rows are lifted out of the live
        # registry, and only THEN are the command set and the persisted
        # attribute vocabulary taken. The rooms then arrive through the real
        # synchronisation, and neither the command set nor any persisted
        # attribute KEY may have gained anything. A resync afterwards must
        # stay idempotent (the commons gate's second-sync shape).
        places = _hospitality_places()
        registry_snapshot = dict(_places())
        saved_rows = {}
        for place in places:
            exterior = _exterior(place)
            for doorway in list(exterior.exits):
                if doorway.key == place.doorway_key_zh:
                    doorway.delete()
            interior = _interior(place)
            for back_exit in list(interior.exits):
                back_exit.delete()
            interior.delete()
            saved_rows[place.key] = _places()[place.key]
            del _places()[place.key]
        # Full ordered snapshot restore: a dict.update() of only the removed
        # rows would re-append them at the END of the live registry, and its
        # insertion order is load-bearing for the derived service-host roster.
        self.addCleanup(_restore_places_snapshot, registry_snapshot)
        self._patch_roster(
            tuple(
                row
                for row in get_catalog().service_hosts
                if row.anchor_room not in saved_rows
            )
        )
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()  # convergence deletes the three hosts
        self.assertEqual(
            [(_host(place), list(search_object_by_tag(place.key))) for place in places],
            [(None, [])] * 3,
            "the patched sync left a hospitality artifact alive",
        )
        commands_before = {command.key for command in CharacterCmdSet().commands}
        vocabulary = {
            (row.db_model, row.db_key, row.db_category)
            for row in Attribute.objects.only("db_model", "db_key", "db_category")
        }
        # The rooms arrive: full registries back, real synchronisation.
        _restore_places_snapshot(registry_snapshot)
        saved_rows.clear()
        for patcher in self._patchers:
            patcher.stop()
        self._patchers.clear()  # the base's addCleanup stops each once only
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_interiors()
            sync_service_content()
        for place in places:
            with self.subTest(arrival=place.kind):
                self.assertIsNotNone(_host(place))
                self.assertEqual(len(search_object_by_tag(place.key)), 1)
        self.assertEqual(
            {command.key for command in CharacterCmdSet().commands},
            commands_before,
        )
        arrived_vocabulary = {
            (row.db_model, row.db_key, row.db_category)
            for row in Attribute.objects.only("db_model", "db_key", "db_category")
        }
        self.assertEqual(arrived_vocabulary, vocabulary)
        # A further resync stays idempotent (no second-sync-only state).
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        self.assertEqual(
            arrived_vocabulary,
            {
                (row.db_model, row.db_key, row.db_category)
                for row in Attribute.objects.only("db_model", "db_key", "db_category")
            },
        )
        # The hospitality hosts persist no attribute key a shipped trading
        # host does not also carry: the attendant shape adds nothing to the
        # persisted surface.
        trader_host_keys = {
            attribute.key
            for attribute in _host(_place_by_kind("general_store")).attributes.all()
        }
        for place in _hospitality_places():
            with self.subTest(place=place.kind):
                self.assertLessEqual(
                    {attribute.key for attribute in _host(place).attributes.all()},
                    trader_host_keys,
                )

    @covers_requirement(
        "altoria-hospitality::each-host-s-dialogue-teaches-what-its-location-is-for"
    )
    def test_each_host_s_table_names_the_commands_its_room_exists_to_host(self):
        tavern = _place_by_kind("tavern")
        inn = _place_by_kind("lodging")
        bathhouse = _place_by_kind("bathhouse")
        player = self._player("hospitality_talker")
        for place in (tavern, inn, bathhouse):
            with self.subTest(place=place.kind):
                host = _host(place)
                # Reached through the rules API, exactly as talk reaches it.
                self.assertEqual(dialogue_key_for(host), _authored(place)["dialogue_key"])
                self.assertIsNotNone(greeting_for(host))
        # The innkeeper names the three verbs the inn exists to host.
        for verb in ("`rest`", "`sleep`", "`practice`"):
            self.assertIn(verb, _table_text(inn), "the inn's table lost a verb")
        # The tavern keeper names conversation and party invitation.
        for verb in ("`talk`", "`invite`"):
            self.assertIn(verb, _table_text(tavern), "the tavern's table lost a verb")
        # The bathhouse keeper explains the separated sides — the room's
        # whole authored rule.
        bath_table = _table_text(bathhouse)
        self.assertIn("男", bath_table)
        self.assertIn("女", bath_table)
        # Every authored keyword answers through the table API (a keyword
        # the panel could press but the rules could not answer is a bug).
        table = _dialogue_table()
        for place in (tavern, inn, bathhouse):
            definition = table[_authored(place)["dialogue_key"]]
            for response in definition.responses:
                with self.subTest(keyword=response.keyword):
                    answer = table_response(
                        _authored(place)["dialogue_key"], response.keyword
                    )
                    self.assertEqual(answer, response.response)
        # None of the three attendant tables quotes the trade verbs — they
        # sell nothing, and a quoted command nobody here can execute is the
        # same lie the sanctum's priest's table may not tell.
        for place in (tavern, inn, bathhouse):
            with self.subTest(trade_free=place.kind):
                for verb in ("`buy`", "`sell`", "`shop stock`"):
                    self.assertNotIn(verb, _table_text(place), place.kind)


if __name__ == "__main__":
    unittest.main()
