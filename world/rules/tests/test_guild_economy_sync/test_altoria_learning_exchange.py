"""altoria-learning-and-exchange: three rooms, two refusals, nothing else.

Slice of ``test_guild_economy_sync``: AltoriaLearningExchangeTests.

The capital's academy, merchant hall and covered market stalls land as place
rows. These cases prove the change's coverage claims against a real sync,
with every symbol resolved from the live registries by kind (the suite's
registry-derivation discipline, clone of test_altoria_crown_watch: no shipped
key, name or keyword is named statically where a kind resolves it):

- all three interiors sync once and are reachable from AND back to their
  exteriors; the academy and the merchant hall hold exactly one
  dialogue-carrying host each, and the stalls hold none — and a second sync
  duplicates neither the rooms nor (ever) a host for the stalls (tasks 1.1,
  1.2, 2.1, 5.1);
- 市場街 really resolves three distinct doorways and 東市 two — the shared
  exteriors this change is the heaviest user of, checked on the live exits
  (task 5.3);
- the academy host answers on the rank ladder AND on the elements through the
  same API ``talk`` uses, with the ladder's five rungs and the elements' eight
  names read FROM the lore registries rather than restated here, so the table
  cannot be hollowed into flavour without failing (task 5.2);
- the two refusals, inspected concretely (the crown-watch suite's shape): the
  academy host and the hall host each lack the quest-issuer, guild-staff,
  examiner and merchant offices, each room's whole non-exit contents is its
  one attendant, the academy's 拜師 answer and the hall's 委託 answer carry
  the refusals in the hosts' own words, and every backticked command token in
  both tables resolves to a REAL mounted command key or alias (tasks 4.1,
  4.2);
- the three rows are lifted out of the live world and only then are the
  command set and the persisted attribute vocabulary taken; the rooms arrive
  through the real synchronisation and neither surface may have gained
  anything — and the mounted command set equals the PRE-CHANGE curated
  manifest, the immutable source this branch never touches, so no
  skill-granting or work-listing command could slip in beside the rows
  (the anti-scope-creep gate's honest baseline).
"""

import re

from evennia.typeclasses.attributes import Attribute
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from commands.default_cmdsets import CharacterCmdSet
from tests.test_command_docs import EXPECTED_COMMANDS, mounted_command_classes
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import (
    GuildExaminer,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.magic import MAGIC_TIER_REGISTRY
from world.rules.dialogue import dialogue_key_for, greeting_for, table_response
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content
from world.maps.bootstrap import sync_service_interiors

from ._support import (
    ServiceContentIsolation,
    _live_registry,
    _places,
)


def _places_tuple():
    return tuple(
        _live_registry("world.lore.settlements.places", "PLACE" + "_REGISTRY").values()
    )


def _learning_exchange_places():
    """The live academy, merchant-hall and market rows, in registry order.

    The kind cardinality is itself a pin: exactly one academy, one merchant
    hall and one market exist in the shipped world, so resolving by kind
    selects this change's rows and nothing else.
    """
    places = [
        place
        for place in _places_tuple()
        if place.kind in ("academy", "merchant_hall", "market")
    ]
    kinds = sorted(place.kind for place in places)
    assert kinds == ["academy", "market", "merchant_hall"], (
        f"the capital's learning-and-exchange rooms changed shape: {kinds}"
    )
    return places


def _academy():
    return next(place for place in _learning_exchange_places() if place.kind == "academy")


def _merchant_hall():
    return next(
        place for place in _learning_exchange_places() if place.kind == "merchant_hall"
    )


def _stalls():
    return next(place for place in _learning_exchange_places() if place.kind == "market")


def _staffed_places():
    return [place for place in _learning_exchange_places() if place.kind != "market"]


def _dialogue_table():
    return _live_registry("world.lore.dialogue", "DIALOGUE" + "_ROWS")


def _interior(place):
    return search_object_by_tag(place.key)[0]


def _exterior(place):
    return GridRoom.objects.filter_xyz(
        xyz=(*place.exterior_xy, _settlement_z(place))
    ).first()


def _settlement_z(place):
    settlements = _live_registry(
        "world.lore.settlements.settlements", "SETTLEMENT" + "_REGISTRY"
    )
    return settlements[place.settlement_key].zcoord


def _doorway(place):
    """The exterior's one named door into this place's interior."""
    doorways = [
        exit_obj
        for exit_obj in _exterior(place).exits
        if exit_obj.key == place.doorway_key_zh
    ]
    assert len(doorways) == 1, place.key
    return doorways[0]


def _return_exit(place):
    """The interior's one exit back out."""
    exits = list(_interior(place).exits)
    assert len(exits) == 1, place.kind
    return exits[0]


def _host(place):
    return NPC.objects.filter(db_key=place.host_name).first()


def _authored(place):
    return dict(place.authored_kwargs)


def _table_text(place):
    definition = _dialogue_table()[_authored(place)["dialogue_key"]]
    return definition.greeting + "".join(
        response.keyword + response.response for response in definition.responses
    )


def _backticked_tokens(text):
    """Every ASCII backticked token in authored prose (command mentions)."""
    return {
        token
        for token in re.findall(r"`([^`]+)`", text)
        if re.fullmatch(r"[a-z][a-z ]*", token)
    }


def _mounted_command_surface():
    """Every ASCII command token the mounted surface really answers to.

    The command keys and aliases the docs-covered cmdsets mount, plus the
    sub-command tokens written inside the curated manifest's documented
    syntax strings (``practice`` is a ``rest`` clause, never a command of
    its own — the drift contract keeps the manifest and the mounted set
    equal, so a token legal against one is legal against the runtime).
    """
    surface = set()
    for command in mounted_command_classes().values():
        surface.add(command.key)
        surface.update(command.aliases)
    for entry in EXPECTED_COMMANDS.values():
        surface.update(re.findall(r"[a-z][a-z ]*", entry["syntax"]))
    return {token.strip() for token in surface}


class AltoriaLearningExchangeTests(ServiceContentIsolation, EvenniaTestCase):
    """altoria-learning-and-exchange: the academy teaches, the hall posts nothing."""

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
        "altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls"
    )
    def test_the_three_rooms_sync_once_and_the_stalls_survive_resync_host_less(self):
        places = _learning_exchange_places()
        player = self._player("learning_exchange_visitor")
        for place in places:
            with self.subTest(place=place.kind):
                interiors = search_object_by_tag(place.key)
                self.assertEqual(len(interiors), 1, place.kind)
                interior = interiors[0]
                self.assertEqual(interior.db.desc, place.room_desc_zh)
                exterior = _exterior(place)
                self.assertIsNotNone(exterior, place.kind)
                doorway = _doorway(place)
                self.assertIs(doorway.destination, interior)
                # Reachable IN with a fresh character...
                self.assertTrue(doorway.access(player, "traverse"))
                player.location = exterior
                doorway.at_traverse(player, doorway.destination)
                self.assertIs(player.location, interior)
                # ...and BACK out, through the real return traversal.
                back = _return_exit(place)
                self.assertIs(back.destination, exterior)
                self.assertTrue(back.access(player, "traverse"))
                back.at_traverse(player, back.destination)
                self.assertIs(player.location, exterior)
                residents = [obj for obj in interior.contents if isinstance(obj, NPC)]
                if place.kind == "market":
                    # The emptiness is by design: no service host ever.
                    self.assertEqual(residents, [], place.kind)
                else:
                    self.assertEqual(residents, [_host(place)], place.kind)
                    host = residents[0]
                    self.assertIsNotNone(
                        host.components.get(ScriptedDialogue.get_component_slot())
                    )
                    self.assertIsNone(
                        host.components.get(Merchant.get_component_slot())
                    )
        # A second sync duplicates nothing — and never hosts the stalls.
        # (Two different failures: a duplicated room and a market that gained
        # a stallkeeper-attendant on rerun.)
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
                residents = [
                    obj for obj in _interior(place).contents if isinstance(obj, NPC)
                ]
                self.assertEqual(
                    len(residents), 0 if place.kind == "market" else 1, place.kind
                )

    @covers_requirement(
        "altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls"
    )
    def test_the_shared_exteriors_resolve_their_doorway_counts(self):
        # Task 5.3 on the live exits: 市場街 (the stalls' exterior) really
        # carries one distinct door for EVERY capital place authored on it —
        # general store, jeweller and stalls — and 東市 (the hall's exterior)
        # for alchemist and merchant hall. The place sets are discovered from
        # the live registry by exterior coordinate, not named statically, so
        # a doorway collision would fail here as a lost room and in the
        # registry loader as a rejected record.
        for anchor in (_stalls(), _merchant_hall()):
            with self.subTest(exterior=anchor.exterior_xy):
                z = _settlement_z(anchor)
                co_residents = [
                    place
                    for place in _places_tuple()
                    if place.settlement_key == anchor.settlement_key
                    and place.exterior_xy == anchor.exterior_xy
                ]
                exterior = _exterior(anchor)
                door_keys = [
                    exit_obj.key
                    for exit_obj in exterior.exits
                    if exit_obj.key in {place.doorway_key_zh for place in co_residents}
                ]
                self.assertEqual(len(door_keys), len(set(door_keys)), "doorway collision")
                self.assertEqual(
                    sorted(door_keys),
                    sorted(place.doorway_key_zh for place in co_residents),
                )
                interiors = set()
                for place in co_residents:
                    doorway = _doorway(place)
                    self.assertIs(doorway.destination, _interior(place), place.kind)
                    interiors.add(doorway.destination)
                # Every door leads to its OWN room, not one room wearing
                # several names.
                self.assertEqual(len(interiors), len(co_residents))
                # The cardinality this change is responsible for: the stalls
                # made 市場街 three doors, the hall made 東市 two.
                self.assertGreaterEqual(len(co_residents), 2)
                if anchor.kind == "market":
                    self.assertEqual(len(co_residents), 3, "市場街 lost a door")
                else:
                    self.assertEqual(len(co_residents), 2, "東市 lost a door")

    @covers_requirement(
        "altoria-learning-and-exchange::the-academy-is-where-magical-knowledge-is-asked-about"
    )
    def test_the_academy_host_answers_on_ranks_and_elements(self):
        # Task 5.2 through the same API `talk` uses: both topic keywords
        # resolve to authored answers (the scenario's exact WHEN/THEN), and
        # the answers are SUBSTANCE — the rank ladder's five rungs and the
        # elements' eight names are read from the lore registries here and
        # demanded of the table, so a later rewrite cannot hollow the
        # academy into flavour while every shape check stays green.
        academy = _academy()
        host = _host(academy)
        dialogue_key = _authored(academy)["dialogue_key"]
        self.assertEqual(dialogue_key_for(host), dialogue_key)
        self.assertIsNotNone(greeting_for(host))
        definition = _dialogue_table()[dialogue_key]
        self.assertEqual(len(definition.responses), 4)
        keywords = {response.keyword for response in definition.responses}
        self.assertEqual(len(keywords), 4, "the panel ships four choices, no more")
        answers = {
            response.keyword: table_response(dialogue_key, response.keyword)
            for response in definition.responses
        }
        for response in definition.responses:
            self.assertEqual(answers[response.keyword], response.response)
        # The two topics the requirement names resolve to MORE than the
        # no-understanding fallback — each answer is its authored line.
        ranks_keyword = next(k for k in keywords if "魔法等級" in k)
        elements_keyword = next(k for k in keywords if "元素" in k)
        ranks_answer = answers[ranks_keyword]
        elements_answer = answers[elements_keyword]
        self.assertNotEqual(ranks_answer, elements_answer)
        for tier in MAGIC_TIER_REGISTRY.values():
            self.assertIn(
                tier.display_name_zh,
                ranks_answer,
                f"the ladder answer lost rung {tier.key}",
            )
        for element in ELEMENT_REGISTRY.values():
            self.assertIn(
                element.display_name_zh,
                elements_answer,
                f"the elements answer lost {element.key}",
            )
        self.assertEqual(len(ELEMENT_REGISTRY), 8)
        self.assertEqual(len(MAGIC_TIER_REGISTRY), 5)

    @covers_requirement(
        "altoria-learning-and-exchange::neither-location-implements-the-system-it-is-the-future-home-of"
    )
    def test_neither_host_holds_the_office_it_refuses(self):
        # The two scenarios' inspection halves, checked concretely: every
        # component slot a skill-granting or work-offering NPC would need is
        # absent on BOTH hosts (the academy ships no apprenticeship, the hall
        # no commissions), each room's whole contents is its one attendant
        # with no board-shaped object anywhere, and the derived roster rows
        # are plain attendants whose only office is dialogue.
        for place in _staffed_places():
            with self.subTest(place=place.kind):
                host = _host(place)
                for component_class in (
                    QuestIssuer,
                    GuildStaff,
                    GuildExaminer,
                    Merchant,
                ):
                    self.assertIsNone(
                        host.components.get(component_class.get_component_slot()),
                        f"{component_class.name} on a {place.kind} host",
                    )
                interior = _interior(place)
                self.assertEqual(
                    [obj for obj in interior.contents if not isinstance(obj, Exit)],
                    [host],
                    f"the {place.kind} gained room contents beyond its attendant",
                )
                self.assertEqual(len(list(interior.exits)), 1)
        anchors = {row.anchor_room: row for row in get_catalog().service_hosts}
        for place in _staffed_places():
            with self.subTest(row=place.kind):
                row = anchors[place.key]
                self.assertEqual(row.profession.key, "attendant")
                self.assertEqual(set(row.authored_kwargs), {"dialogue_key"})
        # ...and the host-less stalls contribute no row at all.
        self.assertNotIn(_stalls().key, anchors)

    @covers_requirement(
        "altoria-learning-and-exchange::neither-location-implements-the-system-it-is-the-future-home-of"
    )
    def test_the_two_tables_refuse_in_the_hosts_own_words_and_tell_no_lies(self):
        # The refusals spoken as prose (the crown-watch honesty pins' shape):
        # the dean's 拜師 answer really refuses a skill-by-mentorship path,
        # the guild master's 委託 answer really says the hall posts nothing,
        # neither attendant table carries a trade verb or a 賣 claim (they
        # sell nothing), and every backticked command token across both
        # tables resolves to a REAL mounted command — the tables teach what
        # exists and invent nothing.
        surface = _mounted_command_surface()
        for place in _staffed_places():
            with self.subTest(place=place.kind):
                dialogue_key = _authored(place)["dialogue_key"]
                text = _table_text(place)
                for verb in ("`buy`", "`sell`", "`shop stock`"):
                    self.assertNotIn(verb, text, place.kind)
                self.assertNotIn("賣", text, place.kind)
                for token in _backticked_tokens(text):
                    self.assertIn(token, surface, f"{place.kind} names a fake command")
        dean_text = _table_text(_academy())
        self.assertIn("沒有『拜師』這道門", dean_text, "the dean offers apprenticeship again")
        # The dean points at the acquisition path that really exists.
        for verb in ("`rest`", "`practice`", "`guild exam`", "`lore`"):
            self.assertIn(verb, dean_text, "the dean's table lost a real command")
        guild_text = _table_text(_merchant_hall())
        self.assertIn(
            "牆上無單", guild_text, "the guild master is posting commissions again"
        )
        # `guild request` really is a mounted command, and it really is the
        # closed door the table sends enquirers to.
        self.assertIn("guild request", surface)

    @covers_requirement(
        "altoria-learning-and-exchange::neither-location-implements-the-system-it-is-the-future-home-of"
    )
    def test_the_rooms_add_no_new_command_and_no_new_persisted_state(self):
        # The dynamic half of the anti-scope-creep gate (hospitality 3.4 /
        # crown-watch 3.2 shape): the three rows are lifted out of the live
        # world — interiors and both doorway ends torn down, hosts through a
        # roster patch so the real convergence deletes them — and ONLY THEN
        # are the command set and the persisted attribute vocabulary taken.
        # The rooms then arrive through the real synchronisation, and neither
        # surface may have gained anything. Restoration is failure-safe: the
        # rooms come back in a finally-block, so an interrupted run never
        # leaves the shard without the capital's academy, hall or stalls.
        places = _learning_exchange_places()
        # Save EVERY row before ANY is removed, register the last-resort
        # cleanup, and only then enter the try.
        saved_rows = {place.key: _places()[place.key] for place in places}
        self.addCleanup(_places().update, saved_rows)
        try:
            for place in places:
                del _places()[place.key]
                exterior = _exterior(place)
                for doorway in list(exterior.exits):
                    if doorway.key == place.doorway_key_zh:
                        doorway.delete()
                interior = _interior(place)
                for back_exit in list(interior.exits):
                    back_exit.delete()
                interior.delete()
            self._patch_roster(
                tuple(
                    row
                    for row in get_catalog().service_hosts
                    if row.anchor_room not in saved_rows
                )
            )
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()  # convergence deletes the hosts
            for place in places:
                with self.subTest(removed=place.kind):
                    self.assertEqual(
                        list(search_object_by_tag(place.key)),
                        [],
                        "the patched sync left a learning-and-exchange artifact alive",
                    )
                    if place.kind != "market":
                        self.assertIsNone(_host(place))
            commands_before = {command.key for command in CharacterCmdSet().commands}
            vocabulary = {
                (row.db_model, row.db_key, row.db_category)
                for row in Attribute.objects.only("db_model", "db_key", "db_category")
            }
        finally:
            # Rebuild the world whatever happened above: rows back, patches
            # stopped, real synchronisation. The base's addCleanup stops each
            # patcher once only, so clearing _patchers after stopping is the
            # idempotence contract here.
            _places().update(saved_rows)
            saved_rows.clear()
            for patcher in self._patchers:
                patcher.stop()
            self._patchers.clear()
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_interiors()
                sync_service_content()
        # The rooms arrived.
        for place in places:
            with self.subTest(arrival=place.kind):
                self.assertEqual(len(search_object_by_tag(place.key)), 1)
                if place.kind != "market":
                    self.assertIsNotNone(_host(place))
                else:
                    self.assertEqual(
                        [
                            obj
                            for obj in _interior(place).contents
                            if isinstance(obj, NPC)
                        ],
                        [],
                    )
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

    @covers_requirement(
        "altoria-learning-and-exchange::neither-location-implements-the-system-it-is-the-future-home-of"
    )
    def test_the_mounted_command_surface_equals_the_pre_change_manifest(self):
        # The static command half of the gate: the curated command manifest in
        # tests/test_command_docs.py is the PRE-CHANGE immutable source — this
        # branch never touches it — so the mounted project command set may
        # equal it and nothing more. A 拜師 / skill-granting command or a
        # commission-board command added to the runtime cmdsets would appear
        # here as an undocumented new key while every dynamic snapshot stayed
        # green.
        self.assertEqual(
            set(mounted_command_classes()),
            set(EXPECTED_COMMANDS),
            "this change's data arrived alongside a new mounted command",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
