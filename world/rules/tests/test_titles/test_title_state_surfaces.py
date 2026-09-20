"""Slice of ``test_titles``: TitleStateTests."""
from tools.spec_traceability import covers_requirement
import ast
import contextlib
import functools
import inspect
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.titles import (
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.rules import titles as titles_module
from world.rules.titles import removal as titles_removal_module
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    ActionRequest,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import CLOCK_YAML, WorldClock, _EVENT_SOURCES
from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.guild import register_adventurer
from world.rules.titles import (
    DECLINED_LOG_KEY,
    MAX_DECLINE_RECORDS,
    MAX_REMOVAL_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
    accept_epithet,
    bank_epithet,
    bank_fixed,
    banked_epithets,
    banked_fixed_keys,
    compose_full_title,
    compose_title,
    decline_epithet_ballot,
    decline_records,
    declined_digest,
    equip_epithet,
    equip_fixed,
    epithet_removal_gate,
    fixed_display_name,
    grant_rank_title,
    grant_first_quest_epithet,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    predicate_satisfied,
    read_pending_ballot,
    read_title_state,
    register_title_planner,
    remove_epithet,
    removal_digest,
    removal_records,
    safe_full_title,
    safe_pending_ballot,
    title_context_entries,
    title_event_effect_planner,
)
from world.rules.tests.test_cast_settlement import (
    _CastSettlementTestCase,
    _raising_stage,
)
from world.lore.guild import GuildRank
from world.tests.synthetic_data import make_title
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._knowledge_probes import basic_attack_key, live_fixed_title_registry, live_guild_rank_registry, live_registry

from ._support import (
    T_E_KEY,
    T_F_KEY,
    _EPITHET,
    _FIXED,
    _open_title_scope,
    _starter,
)


class TitleStateTests(EvenniaTest):
    """The two attributes, the strict reader, and the swap-only surface."""
    def setUp(self):
        _open_title_scope(self)
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="title-state-holder")

    def _prime(self, collection, equipped):
        self.entity.attributes.add(TITLE_COLLECTION_KEY, collection)
        self.entity.attributes.add(TITLE_EQUIPPED_KEY, equipped)

    def _malformed_states(self):
        return {
            "collection is not a list": ("not a list", {"fixed": None, "epithet": None}),
            "collection holds a non-mapping": (["x"], {"fixed": None, "epithet": None}),
            "entry has unknown fields": (
                [{**_FIXED, "extra": 1}],
                {"fixed": None, "epithet": None},
            ),
            "entry has unknown kind": (
                [{"kind": "rank", "key": T_F_KEY, "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "fixed entry misses its key": (
                [{"kind": "fixed", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "epithet entry misses its quote": (
                [{"kind": "epithet", "display": _starter().display, "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "granted_tick is boolean": (
                [{**_FIXED, "granted_tick": True}],
                {"fixed": None, "epithet": None},
            ),
            "granted_tick is negative": (
                [{**_FIXED, "granted_tick": -1}],
                {"fixed": None, "epithet": None},
            ),
            "identifier is blank": (
                [{"kind": "epithet", "display": "", "origin_quote": "x", "granted_tick": 1}],
                {"fixed": None, "epithet": None},
            ),
            "duplicate fixed key": (
                [_FIXED, dict(_FIXED)],
                {"fixed": T_F_KEY, "epithet": None},
            ),
            "duplicate epithet display": (
                [_EPITHET, dict(_EPITHET)],
                {"fixed": None, "epithet": _starter().display},
            ),
            "equipped is not a mapping": ([], "fixed"),
            "equipped has unknown fields": (
                [],
                {"fixed": None, "epithet": None, "extra": 1},
            ),
            "equipped misses a field": ([], {"fixed": None}),
            "equipped slot is blank": ([], {"fixed": "", "epithet": None}),
            "non-empty collection with an empty fixed slot": (
                [_FIXED],
                {"fixed": None, "epithet": None},
            ),
            "non-empty collection with an empty epithet slot": (
                [_EPITHET],
                {"fixed": None, "epithet": None},
            ),
            "fixed slot names an unbanked key": (
                [_FIXED],
                {"fixed": T_E_KEY, "epithet": None},
            ),
            "fixed slot names a banked epithet": (
                [_FIXED, _EPITHET],
                {"fixed": _starter().display, "epithet": _starter().display},
            ),
            "epithet slot names an unbanked display": (
                [_EPITHET],
                {"fixed": None, "epithet": "夜行者"},
            ),
        }

    @covers_requirement("title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip", "title-system::title-state-is-a-two-kind-collection-and-a-two-slot-equip-record")
    def test_module_exposes_epithet_removal_as_the_only_delete_surface(self):
        # title-codex-removal tightened this pin from "no delete mutator at
        # all" to "exactly ONE delete surface": the epithet removal family.
        # Every other deletion/undress name stays forbidden.
        forbidden = (
            "clear",
            "delete",
            "unequip",
            "unbank",
            "discard",
            "withdraw",
            "forget",
            "reset",
        )
        allowed_removal_family = {
            "remove_epithet",
            "epithet_removal_gate",
            "removal_records",
            "removal_digest",
            "TitleRemovalError",
            "TitleRemovalReason",
        }
        defined = {
            name
            for name, member in vars(titles_module).items()
            if not name.startswith("_") and callable(member)
        }
        offenders = {
            name
            for name in defined
            for word in (*forbidden, "remove", "removal")
            if word in name.lower()
        }
        self.assertEqual(offenders, allowed_removal_family)
        # The command surface mirrors it: a `remove` verb exists, and no
        # other deletion/undress word appears anywhere in the command.
        from commands import title as title_command

        methods = {
            name
            for name, member in inspect.getmembers(
                title_command.CmdTitle, predicate=inspect.isfunction
            )
            if not name.startswith("_")
        }
        offenders = {
            name
            for name in methods
            for word in (*forbidden, "remove")
            if word in name.lower()
        }
        self.assertEqual(offenders, set())
        source = inspect.getsource(title_command.CmdTitle)
        for word in ("clear", "unequip", "卸下"):
            self.assertNotIn(word, source)
        self.assertIn("remove", source)

    @covers_requirement(
        "title-system::epithet-removal-is-the-only-delete-path-and-gates-precede-confirmation"
    )
    def test_removal_source_structurally_preserves_equipment_and_fixed(self):
        # Body-level AST pin (complements the name-level scan): the sole
        # delete path writes the EQUIPPED record back unchanged and its
        # comprehension filters only epithet rows — no fixed-kind token,
        # no assignment to the slots. The command dispatcher mirrors this:
        # ``parts[1]`` is never gated on ``fixed``, so a bare
        # ``title remove fixed …`` falls through to usage.
        tree = ast.parse(inspect.getsource(titles_removal_module))
        fn = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "remove_epithet"
        )
        writes = [
            node
            for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_write_title_state"
        ]
        self.assertEqual(len(writes), 1)
        self.assertEqual(ast.unparse(writes[0].args[2]), "equipped")
        stores = [
            target
            for node in ast.walk(fn)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name) and target.id == "equipped"
        ]
        self.assertEqual(stores, [])
        # Structural (not source-text): ast.unparse would emit a fixed-kind
        # literal as 'fixed', so a text scan for the double-quoted form would
        # be vacuous. Assert on the constant VALUES instead — no "fixed" kind
        # string appears anywhere in the sole delete path — and positively
        # pin that the one collection-filter compares kind ONLY to the
        # epithet marker.
        literal_values = {
            node.value
            for node in ast.walk(fn)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("fixed", literal_values)
        self.assertNotIn(
            "_FIXED_KIND",
            {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)},
        )
        kind_comparisons = {
            ast.unparse(node.comparators[0])
            for node in ast.walk(fn)
            if isinstance(node, ast.Compare)
            and ast.unparse(node.left) in ('entry["kind"]', "entry['kind']")
        }
        self.assertEqual(kind_comparisons, {"_EPITHET_KIND"})
        # Non-vacuity: the IDENTICAL detector (every string constant's value)
        # catches a fixed-kind mutant — proving the pin above can actually
        # fire, unlike a source-text scan for '"fixed"' that ast.unparse's
        # single-quote canonicalization would render always-green.
        mutant_fn = ast.parse(
            "def f(collection):\n"
            "    return [e for e in collection if e['kind'] == 'fixed']\n"
        ).body[0]
        mutant_literals = {
            node.value
            for node in ast.walk(mutant_fn)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertIn("fixed", mutant_literals)

        from commands import title as title_command

        command_tree = ast.parse(inspect.getsource(title_command))
        gated = {
            comparator.value
            for node in ast.walk(command_tree)
            if isinstance(node, ast.Compare)
            and ast.unparse(node.left) == "parts[1].lower()"
            for comparator in node.comparators
            if isinstance(comparator, ast.Constant)
        }
        self.assertEqual(gated, {"epithet"})
