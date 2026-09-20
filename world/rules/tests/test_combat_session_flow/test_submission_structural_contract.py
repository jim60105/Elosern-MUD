"""Slice of ``test_combat_session_flow``: SubmissionStructuralTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch
from dataclasses import replace
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill
from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from ..combat_fixtures import grant_lineage


class SubmissionStructuralTests(unittest.TestCase):
    """combat-session-opening-dispatch 5.3/5.8: structural tripwires."""

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    def test_in_session_entries_never_request_or_judge_compression(self):
        import ast as _ast

        import world.rules.combat_session as session

        for func in (session.submit_player_action, session.submit_player_item_use):
            tree = _ast.parse(inspect.getsource(func))
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Call):
                    self.assertNotIn(
                        "opening",
                        [kw.arg for kw in node.keywords if kw.arg],
                        func.__name__,
                    )
                    callee = node.func
                    name = callee.id if isinstance(callee, _ast.Name) else getattr(callee, "attr", "")
                    self.assertNotEqual(name, "classify_overwhelm", func.__name__)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_resolve_overwhelm_has_a_single_production_call_site(self):
        import ast as _ast

        # One level deeper than the flat module: parents[4] is the repo root.
        root = Path(__file__).resolve().parents[4]
        callers = []
        for directory in ("commands", "typeclasses", "world"):
            for path in (root / directory).rglob("*.py"):
                if "tests" in path.parts:
                    continue
                tree = _ast.parse(path.read_text(encoding="utf-8"))
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.Call):
                        callee = node.func
                        name = callee.id if isinstance(callee, _ast.Name) else getattr(callee, "attr", "")
                        if name == "resolve_overwhelm":
                            callers.append(path)
        session_dir = (root / "world" / "rules" / "combat_session").resolve()
        self.assertEqual({p.resolve().parent for p in callers}, {session_dir})
