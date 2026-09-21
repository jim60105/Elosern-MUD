"""altoria-crown-and-watch: four rooms, two refusals, nothing else.

Slice of ``test_guild_economy_sync``: AltoriaCrownWatchTests.

The capital's palace, two watch posts and drill yard land as place rows.
These cases prove the change's three coverage claims against a real sync,
with every symbol resolved from the live registries by kind (the suite's
registry-derivation discipline, clone of test_altoria_hospitality: no
shipped key, name or keyword is named statically):

- all four interiors sync once and are reachable from AND back to their
  exteriors; the three staffed rooms hold exactly one dialogue-carrying
  host each, and the palace holds none — and a second sync duplicates
  neither the rooms nor (ever) a host for the palace (tasks 1.3, 4.1);
- a fresh player with no rank, no quest and no prior visit enters the
  palace and both watch posts with no lock consulted at all — the crown's
  rooms ship no gate (task 3.1);
- the watch posts carry no work surface: each host lacks the quest-issuer
  (and guild-staff, examiner, merchant) office, each room's whole non-exit
  contents is its one attendant, and lifting the four rows out of the live
  world changes neither the mounted command surface nor any persisted
  attribute key (task 3.2's state half);
- the mounted command surface equals the PRE-CHANGE curated command
  manifest — an immutable source this branch never touches — so a new
  work-listing command could not slip in beside the rows (task 3.2's
  command half; the dynamic baseline alone cannot see a static addition,
  which is why this comparison is the requirement's real evidence);
- each staffed host's table resolves through the rules dialogue API, the
  drill instructor names ``rest`` + ``practice`` and ``guild exam``, and
  no attendant table carries a trade verb (task 2.4).
"""

import re

from evennia.typeclasses.attributes import Attribute
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from commands.default_cmdsets import CharacterCmdSet
from typeclasses.exits import Exit
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
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
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


def _crown_watch_places():
    """The live palace, watch-post and drill-yard rows, in registry order.

    The kind cardinality is itself a pin: exactly one palace, two watch
    posts and one training ground exist in the shipped world, so resolving
    by kind selects this change's rows and nothing else — and the two
    watch posts are never told apart here (the suite never needs to know
    which door is the gate's; every watch-post claim is checked on both).
    """
    places = [
        place
        for place in _places_tuple()
        if place.kind in ("palace", "watch_post", "training_ground")
    ]
    kinds = sorted(place.kind for place in places)
    assert kinds == ["palace", "training_ground", "watch_post", "watch_post"], (
        f"the crown's rooms changed shape: {kinds}"
    )
    return places


def _palace():
    return next(place for place in _crown_watch_places() if place.kind == "palace")


def _watch_posts():
    return [place for place in _crown_watch_places() if place.kind == "watch_post"]


def _staffed_places():
    return [place for place in _crown_watch_places() if place.kind != "palace"]


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
    assert len(exits) == 1, place.key
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
        surface.update(
            re.findall(r"[a-z][a-z ]*", entry["syntax"])
        )
    return {token.strip() for token in surface}


class AltoriaCrownWatchTests(ServiceContentIsolation, EvenniaTestCase):
    """altoria-crown-and-watch: the crown's rooms are open, and post nothing."""

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
        "altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard"
    )
    def test_the_four_rooms_sync_once_and_the_palace_survives_resync_host_less(self):
        places = _crown_watch_places()
        player = self._player("crown_watch_visitor")
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
                # ...and BACK out, through the real return traversal —
                # an observed reciprocal destination is weaker than the
                # traversal the scenario names (pre-implementation review).
                back = _return_exit(place)
                self.assertIs(back.destination, exterior)
                self.assertTrue(back.access(player, "traverse"))
                back.at_traverse(player, back.destination)
                self.assertIs(player.location, exterior)
                residents = [obj for obj in interior.contents if isinstance(obj, NPC)]
                if place.kind == "palace":
                    # The emptiness IS the content: no service host ever.
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
        # A second sync duplicates nothing — and never hosts the palace.
        # (Two different failures: a duplicated room and a palace that
        # gained an attendant on rerun.)
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
                    len(residents), 0 if place.kind == "palace" else 1, place.kind
                )

    @covers_requirement(
        "altoria-crown-and-watch::the-crown-s-rooms-stand-open-until-a-story-closes-them"
    )
    def test_the_crown_s_rooms_stay_open_to_a_rankless_fresh_player(self):
        # No rank, no quest, no prior visit — and the scenario's second
        # half: the door's one traverse lock is the unconditional
        # everyone-open default (Evennia seeds every exit with a full
        # default lock set; the gate this change refuses would appear as a
        # conditional traverse string, which is exactly what may NOT be
        # here). Checked on the palace and BOTH watch posts (the noble
        # quarter's post is one of the two, and this suite never needs to
        # know which — the named identity is the registered roster test's
        # literal contract).
        player = self._player("crown_watch_rankless")
        self.assertFalse(player.db.quest_log)
        # The shipped shapes an open door takes: no traverse lock at all, or
        # the unconditional everyone-open default. Any conditional string
        # (perm/rank/quest check) is a gate, and a gate is what this
        # requirement forbids.
        open_traverse_strings = ("", "all()", "traverse:all()")
        open_rooms = [_palace(), *_watch_posts()]
        for place in open_rooms:
            with self.subTest(place=place.kind):
                doorway = _doorway(place)
                self.assertIn(
                    doorway.locks.get("traverse") or "", open_traverse_strings
                )
                self.assertTrue(doorway.access(player, "traverse"))
                player.location = _exterior(place)
                doorway.at_traverse(player, doorway.destination)
                self.assertIs(player.location, _interior(place))
                back = _return_exit(place)
                self.assertIn(
                    back.locks.get("traverse") or "", open_traverse_strings
                )
                self.assertTrue(back.access(player, "traverse"))
                back.at_traverse(player, back.destination)
                self.assertIs(player.location, _exterior(place))

    @covers_requirement(
        "altoria-crown-and-watch::the-watch-posts-no-work-of-its-own"
    )
    def test_the_watch_posts_carry_no_work_surface_of_their_own(self):
        # The scenario inspected concretely (pre-implementation review):
        # every component slot a work-offering NPC would need is absent,
        # AND the rooms hold no board-shaped object at all — each watch
        # post's whole contents is its one attendant, its whole exit
        # surface the one door back out. Checked on both posts; no work
        # board could hide in either room without failing this.
        for place in _watch_posts():
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
                        f"{component_class.name} on a watch host",
                    )
                interior = _interior(place)
                self.assertEqual(
                    [obj for obj in interior.contents if not isinstance(obj, Exit)],
                    [host],
                    "the watch post gained room contents beyond its attendant",
                )
                self.assertEqual(len(list(interior.exits)), 1)
        # And the derived roster carries no work-offering row for any of
        # them: three plain attendant rows, dialogue office only.
        anchors = {
            row.anchor_room: row for row in get_catalog().service_hosts
        }
        for place in _staffed_places():
            with self.subTest(row=place.kind):
                row = anchors[place.key]
                self.assertEqual(row.profession.key, "attendant")
                self.assertEqual(set(row.authored_kwargs), {"dialogue_key"})

    @covers_requirement(
        "altoria-crown-and-watch::the-watch-posts-no-work-of-its-own"
    )
    def test_the_rooms_add_no_new_command_and_no_new_persisted_state(self):
        # The dynamic half of task 3.2, the hospitality 3.4 gate's shape:
        # the four rows are lifted out of the live world — interiors and
        # both doorway ends torn down, hosts through a roster patch so the
        # real convergence deletes them — and ONLY THEN are the command
        # set and the persisted attribute vocabulary taken. The rooms then
        # arrive through the real synchronisation, and neither surface may
        # have gained anything. This proves the rooms do not dynamically
        # add surface; the STATIC command claim is the separate manifest
        # comparison below (a snapshot of current code cannot see a static
        # addition — post-implementation review). Restoration is
        # failure-safe: the rooms come back in a finally-block, so an
        # interrupted run never leaves the shard without the crown's rooms.
        places = _crown_watch_places()
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
        self.addCleanup(_places().update, saved_rows)
        self._patch_roster(
            tuple(
                row
                for row in get_catalog().service_hosts
                if row.anchor_room not in saved_rows
            )
        )
        try:
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()  # convergence deletes the hosts
            for place in places:
                with self.subTest(removed=place.kind):
                    self.assertEqual(
                        list(search_object_by_tag(place.key)),
                        [],
                        "the patched sync left a crown-watch artifact alive",
                    )
                    if place.kind != "palace":
                        self.assertIsNone(_host(place))
            commands_before = {command.key for command in CharacterCmdSet().commands}
            vocabulary = {
                (row.db_model, row.db_key, row.db_category)
                for row in Attribute.objects.only("db_model", "db_key", "db_category")
            }
        finally:
            # Rebuild the world whatever happened above: rows back, patches
            # stopped, real synchronisation. The base's addCleanup stops
            # each patcher once only, so clearing _patchers after stopping
            # is the idempotence contract here.
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
                if place.kind != "palace":
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
        "altoria-crown-and-watch::the-watch-posts-no-work-of-its-own"
    )
    def test_the_mounted_command_surface_equals_the_pre_change_manifest(self):
        # The command half of task 3.2's real evidence: the curated
        # command manifest in tests/test_command_docs.py is the PRE-CHANGE
        # immutable source — this branch never touches it — so the
        # mounted project command set may equal it and nothing more. A
        # bounty board or work-listing command added to the runtime
        # cmdsets would appear here as an undocumented new key while every
        # dynamic snapshot stayed green.
        self.assertEqual(
            set(mounted_command_classes()),
            set(EXPECTED_COMMANDS),
            "this change's data arrived alongside a new mounted command",
        )

    @covers_requirement(
        "altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard"
    )
    def test_each_staffed_table_resolves_teaches_and_never_shops(self):
        # Task 2.4, checked through the same API `talk` uses. The drill
        # instructor names the training commands that already work
        # everywhere (rest plus practice, guild exam); no attendant table
        # carries a trade verb — they sell nothing; and every backticked
        # command token across the three tables resolves to a REAL mounted
        # command key or alias, so the tables teach what exists and invent
        # nothing (a table naming a board command is exactly the lie this
        # change refuses).
        surface = _mounted_command_surface()
        for place in _staffed_places():
            with self.subTest(place=place.kind):
                host = _host(place)
                self.assertEqual(
                    dialogue_key_for(host), _authored(place)["dialogue_key"]
                )
                self.assertIsNotNone(greeting_for(host))
                definition = _dialogue_table()[_authored(place)["dialogue_key"]]
                self.assertEqual(len(definition.responses), 4, place.kind)
                for response in definition.responses:
                    with self.subTest(keyword=response.keyword):
                        answer = table_response(
                            _authored(place)["dialogue_key"], response.keyword
                        )
                        self.assertEqual(answer, response.response)
                text = _table_text(place)
                for verb in ("`buy`", "`sell`", "`shop stock`"):
                    self.assertNotIn(verb, text, place.kind)
                for token in _backticked_tokens(text):
                    self.assertIn(
                        token, surface, f"{place.kind} names a command that is not"
                    )
        # The instructor's table specifically names the practice and exam
        # commands its room exists to teach.
        instructor_text = _table_text(
            next(place for place in _crown_watch_places() if place.kind == "training_ground")
        )
        for verb in ("`rest`", "`practice`", "`guild exam`"):
            self.assertIn(verb, instructor_text, "the yard's table lost a verb")


if __name__ == "__main__":
    import unittest

    unittest.main()
