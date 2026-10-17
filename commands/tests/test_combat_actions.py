"""Command tests for combat actions and token-parsed session casts (tasks 2.4-2.5)."""

from tools.spec_traceability import covers_requirement

import inspect
import re
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.action import CmdCast
from commands.combat import CmdCombatActions, CmdCombatCommand
from commands.items import CmdUseItem
from world.lore.elements import Element
from world.rules.player_messages import rejection_message, session_reason_message
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    parse_session_targets,
    read_session,
    resolve_target_token,
)
from world.rules.combat_view import build_combat_view
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill

# File-local synthetic spells carry invented element groups, so the
# category/sub-heading ordering mechanics render fully synthetic rows. The
# kit's own element row (t_glowmire) ships in the scoped element registry;
# only the second group is added through the scope extra.
_FEN = Element("t_fenlight", "沼光", "Synthetic element.")
# Row objects, not string keys: SkillDef validates a raw string against the
# LIVE registry at construction time, before any scope is open. The scoped
# registry carries the same-key rows, so runtime resolution still lands.
_GLOW = Element("t_glowmire", "光沼", "Synthetic element.")
_TIDE_ARC = make_skill(
    "t_tide_arc",
    label="潮弧",
    description="彎彎的合成水弧。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 10},
    usable_out_of_combat=True,
    element=_GLOW,
    effects=["damage:t_glowmire:magic"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="t_glowmire",
)
_GALE_JAB = make_skill(
    "t_gale_jab",
    label="風刺",
    description="輕快的合成突刺。",
    kind=SkillKind.ACTIVE,
    # AREA spec: the multi-token cast exercises the multi-target path, which
    # a SINGLE-target skill rejects as a target-spec mismatch.
    target_spec=TargetSpec.AREA,
    cost={"mp": 9},
    usable_out_of_combat=True,
    element=_FEN,
    effects=["damage:t_fenlight:magic"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    group="t_fenlight",
)
# The kit spell borrows the shipped first-element row (a closed vocabulary
# the kit cannot widen); its key and display label arrive as runtime values
# through the kit row, never as source literals.
_SPELL = SYNTH_SKILLS["t_ember_burst"].key
_SPELL_LABEL = SYNTH_SKILLS["t_ember_burst"].label
_BORROWED_ELEMENT_LABEL = SYNTH_SKILLS["t_ember_burst"].element.display_name_zh

_REED_CUT = make_skill("t_reed_cut", label="蘆斷", description="斷蘆的合成一斬。")

_SCOPE_LOGICALS = (
    "races",
    "static_tiers",
    "subraces",
    "skills",
    "elements",
    "buffs",
    "items",
    "prices",
)


@contextmanager
def _deterministic_round():
    """Freeze every dice read the ordinary round pipeline performs."""
    with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
        "world.rules.combat.damage.roll_d100", return_value=100
    ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
        yield


def _scope_extra() -> dict:
    extra = synth_innate_overlay()
    extra["skills"].update(
        {
            _TIDE_ARC.key: _TIDE_ARC,
            _GALE_JAB.key: _GALE_JAB,
            _REED_CUT.key: _REED_CUT,
        }
    )
    extra["elements"] = {_FEN.key: _FEN}
    return extra


def _player(key="token player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "t_duskmari"
    player.apply_race_baseline()
    return player


def _monster(key="token goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class TokenParsingTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "races", "static_tiers", "subraces")
        super().setUp()
        self.room = create_object(Room, key="token arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("token goblin")
        self.monster.location = self.room

    def test_single_token_resolves_from_active_record(self):
        engage(self.player, self.monster)
        self.assertIs(
            resolve_target_token(self.player, "e1"),
            self.monster,
        )
        self.assertIs(
            resolve_target_token(self.player, "a1"),
            self.player,
        )

    def test_token_bounds_reject_unknown_index(self):
        engage(self.player, self.monster)
        for token in ("a2", "e2", "x1", "e0", ""):
            with self.subTest(token=token):
                with self.assertRaises(CombatSessionError):
                    resolve_target_token(self.player, token)

    def test_comma_tokens_resolve_to_explicit_list(self):
        second = _monster("token goblin2")
        second.location = self.room
        engage(self.player, self.monster)
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        record = from_storage(
            {**to_storage(read_session(self.player)), "enemy_ids": [self.monster.pk, second.pk]}
        )
        _persist(self.player, record)
        targets = parse_session_targets(self.player, "e1,e2")
        self.assertEqual(
            [target.key for target in targets],
            ["token goblin", "token goblin2"],
        )

    def test_shorthand_is_passed_through_intact(self):
        engage(self.player, self.monster)
        for shorthand in ("all-enemies", "all-allies", "all"):
            self.assertEqual(
                parse_session_targets(self.player, shorthand),
                shorthand,
            )

    def test_mixed_and_duplicate_syntax_rejects(self):
        engage(self.player, self.monster)
        for value in ("e1,e1", "e1,token goblin", "all-enemies,e1", "token goblin,token goblin"):
            with self.subTest(value=value):
                with self.assertRaises(CombatSessionError):
                    parse_session_targets(self.player, value)

    def test_empty_value_is_empty_list(self):
        engage(self.player, self.monster)
        self.assertEqual(parse_session_targets(self.player, ""), [])
        self.assertEqual(parse_session_targets(self.player, "   "), [])

    def test_display_name_search_retained(self):
        engage(self.player, self.monster)
        result = parse_session_targets(
            self.player,
            "token goblin",
            search=lambda name: self.monster if name == "token goblin" else None,
        )
        self.assertEqual(result, [self.monster])


class CombatActionsCommandTests(BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="combat actions room")
        self.char1.location = self.room
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        grant_lineage(self.char1, [_SPELL])
        self.monster = _monster("actions goblin")
        self.monster.location = self.room

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_combat_actions_lists_skills_and_tokens(self):
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = " ".join(messages)
        self.assertIn("可用技能與目標代號：", messages[0])
        self.assertIn(f"{_SPELL}（{_SPELL_LABEL}）", joined)
        self.assertIn("e1＝actions goblin", joined)
        self.assertIn("a1＝", joined)

    @covers_requirement("webclient-combat-menu::telnet-combat-actions-renders-identical-category-and-group-structure")
    def test_combat_actions_renders_category_headings_and_element_sub_headings(self):
        # Owning skills across two element sub-groups plus a no-group
        # martial-arts skill.
        self.char1.db.skills = {
            "active": [_SPELL, _GALE_JAB.key, _REED_CUT.key],
            "passive": [],
        }
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = "\n".join(messages)
        # Category headings in SkillCategory declaration order: elemental
        # magic, then martial arts (which carries the innate flee and
        # basic_attack rows under the consolidated six-member taxonomy).
        self.assertIn("◆ 元素魔法", joined)
        self.assertIn("◆ 武技", joined)
        self.assertLess(joined.index("◆ 元素魔法"), joined.index("◆ 武技"))
        # The consolidated taxonomy dropped the movement category: it can
        # never render, even with the innate flee row owned.
        self.assertNotIn("◆ 移動", joined)
        # Element sub-headings in ELEMENT_REGISTRY order (the borrowed row
        # stays first in the scoped registry; the invented row follows).
        self.assertIn(f"  {_BORROWED_ELEMENT_LABEL}", joined)
        self.assertIn("  沼光", joined)
        self.assertLess(
            joined.index(f"  {_BORROWED_ELEMENT_LABEL}"), joined.index("  沼光")
        )
        # Skills stay under their element sub-heading in owned_keys order.
        self.assertLess(
            joined.index(f"  {_BORROWED_ELEMENT_LABEL}"),
            joined.index(f"{_SPELL}（{_SPELL_LABEL}）"),
        )
        self.assertLess(joined.index("  沼光"), joined.index("t_gale_jab（風刺）"))
        # The no-group martial-arts category renders no sub-heading: the
        # skill lines follow the heading directly.
        # "\n目標代號：" is unique as the section header; the bare substring
        # also occurs inside the opening "可用技能與目標代號：" line.
        martial = joined[
            joined.index("◆ 武技") + len("◆ 武技"):joined.index("\n目標代號：")
        ]
        self.assertNotIn("◆", martial)
        self.assertIn("t_reed_cut（蘆斷）", martial)
        # The allied flee row is gone from the session skill list (§6): the
        # party's escape is the confirmed party exit, so no personal-flee
        # bypass is advertised here.
        self.assertNotIn("flee（合成逃跑）", martial)
        # The innate overlay re-seeds the production-forced basic-attack key
        # with a synthetic row whose label is authored in the helper.
        self.assertIn("basic_attack（合成基本攻擊）", martial)

    @covers_requirement("webclient-combat-menu::telnet-combat-actions-renders-identical-category-and-group-structure")
    def test_combat_actions_no_group_category_renders_no_sub_heading(self):
        self.char1.db.skills = {"active": [_REED_CUT.key], "passive": []}
        engage(self.char1, self.monster)
        messages = self._run(CmdCombatActions, "")
        joined = "\n".join(messages)
        martial = joined[
            joined.index("◆ 武技") + len("◆ 武技"):joined.index("\n目標代號：")
        ]
        # The martial-arts heading is followed directly by skill lines; no
        # indented sub-heading line sits between them.
        self.assertIn("◆ 武技\n", joined)
        self.assertIn("t_reed_cut（蘆斷）", martial)

    def test_combat_actions_requires_active_session(self):
        self.call(CmdCombatActions(), "", "目前沒有進行中的戰鬥。")

    def _run(self, cmd_cls, args):
        from unittest.mock import Mock

        self.char1.msg = Mock()
        command = cmd_cls()
        command.caller = self.char1
        command.args = args
        command.func()
        return [call.args[0] for call in self.char1.msg.call_args_list]

    def test_combat_actions_tokens_stable_across_round(self):
        engage(self.char1, self.monster)
        view = build_combat_view(self.char1)
        token_before = next(p.token for p in view.participants if p.identity == self.monster.pk)
        from world.rules.clock import WorldClock
        from world.rules.combat_session import submit_player_action

        with patch("world.rules.clock.get_world_clock", return_value=WorldClock()), patch(
            "world.rules.combat.battlefield.roll_d100", return_value=100
        ), patch("world.rules.combat.damage.roll_d100", return_value=100), patch(
            "world.rules.combat.rounds.roll_d100", return_value=100
        ):
            submit_player_action(self.char1, _SPELL, [self.monster])
        view_after = build_combat_view(self.char1)
        token_after = next(p.token for p in view_after.participants if p.identity == self.monster.pk)
        self.assertEqual(token_before, token_after)

    def test_cast_accepts_single_token(self):
        engage(self.char1, self.monster)
        from world.rules.combat_session import read_session

        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            messages = self._run(CmdCast, f"{_SPELL}=e1")
        self.assertTrue(
            any("繼續戰鬥。" in message for message in messages),
            messages,
        )
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    def test_cast_accepts_comma_tokens(self):
        second = _monster("actions goblin2")
        second.location = self.room
        engage(self.char1, self.monster)
        from world.rules.combat_session import from_storage, read_session, to_storage, _persist

        record = from_storage(
            {**to_storage(read_session(self.char1)), "enemy_ids": [self.monster.pk, second.pk]}
        )
        _persist(self.char1, record)
        self.char1.db.skills = {"active": [_GALE_JAB.key], "passive": []}
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            messages = self._run(CmdCast, f"{_GALE_JAB.key}=e1,e2")
        self.assertTrue(any("繼續戰鬥。" in m for m in messages), messages)
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    def test_cast_rejects_unknown_token_before_initiative(self):
        engage(self.char1, self.monster)
        with patch("world.rules.combat.damage.roll_d100") as roll:
            messages = self._run(CmdCast, f"{_SPELL}=e9")
        roll.assert_not_called()
        self.assertEqual(self.char1.db.active_combat["rounds_elapsed"], 0)
        self.assertTrue(
            any("無法確認當前戰鬥。" in m for m in messages), messages
        )


class CombatCommandTests(BattlefieldIsolation, EvenniaTest):
    """The actor-scoped text party-command surface (party-combat-text-commands).

    ``combat command`` is exercised exactly as a player meets it: one allied
    actor token, one skill/item/tactic selection through the shared draft
    admission, and the auto-resolving final confirmation. Evidence records the
    rendered command output alongside the durable record each step produced.
    """

    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="combat command room")
        self.char1.location = self.room
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        self.char1.traits.mp.base = 50
        self.char1.traits.mp.current = 50
        grant_lineage(self.char1, [_SPELL])
        self.companion = self._companion()
        self.monster = _monster("command goblin", hp=200)
        self.monster.location = self.room
        self.sent: list[str] = []
        self.char1.msg = lambda text="", **kwargs: self.sent.append(str(text))

    def _companion(self):
        """One bound, co-located ally with its own skill, MP and item."""
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        npc = create_object(NPC, key="command companion")
        npc.location = self.room
        npc.race = "t_duskmari"
        npc.apply_race_baseline()
        npc.traits.hp.base = 100
        npc.traits.hp.current = 50
        npc.traits.mp.base = 50
        npc.traits.mp.current = 50
        npc.db.skills = {"active": [_TIDE_ARC.key], "passive": []}
        npc.db.inventory = ["t_ember_spray"]
        join_party(npc, self.char1)
        return npc

    def _run(self, command_class, args=""):
        command = command_class()
        command.caller = self.char1
        command.args = args
        self.sent.clear()
        command.func()
        return "\n".join(self.sent)

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_actor_and_target_tokens_are_independent(self):
        engage(self.char1, self.monster)
        companion_text = self._run(
            CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1"
        )
        # The companion's own selection is admitted: the round stays open for
        # the commander, so nothing resolved and nothing was paid yet.
        self.assertIn("指令已確認，等待其他成員。", companion_text)
        self.assertIn("尚需選擇：a1", companion_text)
        record = read_session(self.char1)
        self.assertEqual(
            record.draft_entries[self.companion.pk]["payload"]["skill_key"],
            _TIDE_ARC.key,
        )
        self.assertEqual(self.char1.traits.mp.current, 50)
        self.assertEqual(self.companion.traits.mp.current, 50)
        self.assertEqual(record.rounds_elapsed, 0)
        # a1-as-actor with e1-as-target is a different pairing on the same
        # immutable token space: the commander's own entry completes the round.
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        record = read_session(self.char1)
        self.assertEqual(record.rounds_elapsed, 1)
        # Each actor paid its own selection's cost and nothing else.
        self.assertEqual(self.companion.traits.mp.current, 40)
        self.assertLess(self.char1.traits.mp.current, 50)

    @covers_requirement("player-combat-session::commander-may-select-only-currently-controllable-allied-actors")
    def test_actor_token_must_name_a_party_member(self):
        engage(self.char1, self.monster)
        before = read_session(self.char1)
        self.assertEqual(
            self._run(CmdCombatCommand, f"e1 skill {_SPELL}=e1"),
            session_reason_message("forbidden_actor"),
        )
        self.assertEqual(
            self._run(CmdCombatCommand, f"a9 skill {_SPELL}=e1"),
            session_reason_message("unknown_session_id"),
        )
        self.assertEqual(read_session(self.char1), before)

    @covers_requirement("player-combat-session::all-personal-skill-choices-and-costs-are-actor-scoped")
    def test_scale_token_reaches_the_shared_mastery_gate(self):
        from world.rules.action import RejectReason

        engage(self.char1, self.monster)
        before = read_session(self.char1)
        # The companion owns no freeform mastery: the shared gate rejects the
        # scale before any entry exists.
        self.assertEqual(
            self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}@2=e1"),
            rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
        )
        # A non-label magnitude is the same stable rejection at the text layer.
        self.assertEqual(
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}@7=e1"),
            rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
        )
        self.assertEqual(read_session(self.char1), before)

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_target_syntax_rejections_leave_the_draft_untouched(self):
        engage(self.char1, self.monster)
        before = read_session(self.char1)
        for value, reason in (
            ("e1,e1", "duplicate_participant"),
            ("e9", "unknown_session_id"),
            ("e1,command goblin", "unknown_session_id"),
            ("all-enemies,e1", "unknown_session_id"),
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    self._run(CmdCombatCommand, f"a1 skill {_SPELL}={value}"),
                    session_reason_message(reason),
                )
                self.assertEqual(read_session(self.char1), before)

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_combat_actions_lists_one_actor_with_costs_items_and_progress(self):
        engage(self.char1, self.monster)
        commander_text = self._run(CmdCombatActions, "")
        self.assertIn("a1＝", commander_text)
        self.assertIn(f"{_SPELL}（{_SPELL_LABEL}）", commander_text)
        self.assertIn("可使用道具：", commander_text)
        self.assertIn("戰術：", commander_text)
        self.assertIn("本回合指令進度", commander_text)
        self.assertIn("必要成員：a1、a2", commander_text)
        companion_text = self._run(CmdCombatActions, "a2")
        self.assertIn("a2＝command companion", companion_text)
        self.assertIn(_TIDE_ARC.key, companion_text)
        # The listing is actor scoped: the companion's menu never advertises
        # the commander's own skill.
        self.assertNotIn(_SPELL, companion_text)
        self.assertEqual(
            self._run(CmdCombatActions, "e1"),
            session_reason_message("forbidden_actor"),
        )
        self.assertEqual(
            self._run(CmdCombatActions, "a9"),
            session_reason_message("unknown_session_id"),
        )

    @covers_requirement("player-combat-session::confirmed-round-selections-persist-as-one-editable-session-draft")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_replacing_an_earlier_choice_keeps_one_entry(self):
        engage(self.char1, self.monster)
        self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1")
        first = read_session(self.char1)
        text = self._run(CmdCombatCommand, "a2 item t_ember_spray")
        record = read_session(self.char1)
        self.assertEqual(record.draft_version, first.draft_version + 1)
        self.assertEqual(list(record.draft_entries), [self.companion.pk])
        self.assertEqual(record.draft_entries[self.companion.pk]["kind"], "item")
        self.assertIn("道具 t_ember_spray", text)
        self.assertEqual(record.rounds_elapsed, 0)

    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    @covers_requirement("inventory-item-actions::text-clients-expose-the-same-deterministic-item-operations")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_no_cost_before_the_complete_round_and_local_item_consumption(self):
        engage(self.char1, self.monster)
        # Fault isolation: the enemy deals no damage, so only the companion's
        # own item effect is observed.
        self.monster.traits.atk_phys.base = 0
        self._run(CmdCombatCommand, "a2 item t_ember_spray")
        self.assertEqual(read_session(self.char1).rounds_elapsed, 0)
        self.assertEqual(self.companion.traits.hp.current, 50)
        self.assertEqual(self.companion.db.inventory.count("t_ember_spray"), 1)
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        # The completing confirmation is the round's own execution: the item
        # is consumed and heals its own actor there, never at selection.
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)
        self.assertEqual(self.companion.db.inventory.count("t_ember_spray"), 0)
        self.assertGreater(self.companion.traits.hp.current, 50)

    @covers_requirement("player-combat-session::taunt-selects-one-enemy-and-resolves-competing-declarations-by-initiative")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_tactics_are_actor_scoped_draft_entries(self):
        engage(self.char1, self.monster)
        self._run(CmdCombatCommand, "a2 defend")
        self.assertEqual(
            read_session(self.char1).draft_entries[self.companion.pk]["payload"],
            {"tactical_key": "defend", "target_id": None},
        )
        self._run(CmdCombatCommand, "a2 dodge")
        self.assertEqual(
            read_session(self.char1).draft_entries[self.companion.pk]["payload"],
            {"tactical_key": "dodge", "target_id": None},
        )
        self._run(CmdCombatCommand, "a2 taunt=e1")
        self.assertEqual(
            read_session(self.char1).draft_entries[self.companion.pk]["payload"],
            {"tactical_key": "taunt", "target_id": self.monster.pk},
        )
        # Shape rejections: a target on a targetless tactic, a missing taunt
        # target and a stray argument all refuse without touching the draft.
        before = read_session(self.char1)
        for invalid in ("a2 taunt", "a2 defend=e1", "a2 defend x"):
            with self.subTest(invalid=invalid):
                text = self._run(CmdCombatCommand, invalid)
                self.assertTrue(text.strip())
                self.assertEqual(read_session(self.char1), before)
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_commander_cast_and_use_confirm_only_the_commander_entry(self):
        engage(self.char1, self.monster)
        cast_text = self._run(CmdCast, f"{_SPELL}=e1")
        self.assertIn("指令已確認，等待其他成員。", cast_text)
        record = read_session(self.char1)
        self.assertEqual(list(record.draft_entries), [self.char1.pk])
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.char1.traits.mp.current, 50)
        self.char1.db.inventory = ["t_ember_spray"]
        self.char1.traits.hp.base = 100
        self.char1.traits.hp.current = 10
        self.assertEqual(self._run(CmdUseItem, "t_ember_spray"), "指令已確認，等待其他成員。")
        record = read_session(self.char1)
        self.assertEqual(record.draft_entries[self.char1.pk]["kind"], "item")
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.char1.db.inventory.count("t_ember_spray"), 1)

    @covers_requirement("player-combat-session::reconnect-and-restart-restore-confirmed-selection-progress-without-execution")
    def test_partial_text_draft_survives_restart_without_executing(self):
        engage(self.char1, self.monster)
        revision_text = self._run(CmdCombatActions, "")
        self.assertIn("本回合指令進度", revision_text)
        self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1")
        # Simulate a server restart / reconnect: every in-process battlefield
        # is discarded and the session is restored from its durable record.
        from world.rules.combat_session import restore_active_session
        from world.rules.skip_safety import _BATTLEFIELDS

        _BATTLEFIELDS.clear()
        restore_active_session(self.char1)
        restored = read_session(self.char1)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.rounds_elapsed, 0)
        self.assertEqual(list(restored.draft_entries), [self.companion.pk])
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)

    @covers_requirement("inventory-item-actions::text-clients-expose-the-same-deterministic-item-operations")
    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_text_payloads_match_the_guarded_wire_translation(self):
        from web.webclient.actions.combat_actions import (
            _rules_command,
            validate_command_payload,
        )

        engage(self.char1, self.monster)
        record = read_session(self.char1)
        envelope = {
            "session_id": record.session_id,
            "round_revision": record.round_revision,
            "draft_version": record.draft_version,
            "actor_id": self.companion.pk,
        }

        def translated(command):
            payload = validate_command_payload({**envelope, "command": command})
            return _rules_command(payload["command"])

        def typed(verb, kind_argument, target_value):
            probe = CmdCombatCommand()
            probe.caller = self.char1
            probe.args = ""
            return probe._command_for(verb, kind_argument, target_value)

        # The typed spellings build the exact internal commands the guarded
        # browser payloads translate into, so both entry points admit the same
        # draft entry through the same facade call.
        self.assertEqual(
            typed("skill", _TIDE_ARC.key, "e1"),
            translated(
                {
                    "kind": "skill",
                    "payload": {
                        "skill_key": _TIDE_ARC.key,
                        "target_ids": [self.monster.pk],
                    },
                }
            ),
        )
        self.assertEqual(
            typed("item", "t_ember_spray", "e1"),
            translated(
                {
                    "kind": "item",
                    "payload": {
                        "item_key": "t_ember_spray",
                        "target_id": self.monster.pk,
                    },
                }
            ),
        )
        self.assertEqual(
            typed("taunt", "", "e1"),
            translated(
                {
                    "kind": "tactic",
                    "payload": {"key": "taunt", "target_id": self.monster.pk},
                }
            ),
        )

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_self_and_none_skills_ignore_supplied_target_tokens(self):
        heal = SYNTH_SKILLS["t_moss_veil"]
        breath = SYNTH_SKILLS["t_cinder_breath"]
        grant_lineage(self.companion, [heal.key, breath.key])
        engage(self.char1, self.monster)
        # A SELF skill named for a2 binds a2 inside the rules layer and a NONE
        # skill takes no target at all: a supplied foe token is ignored, never
        # forwarded as a target.
        for skill_key in (heal.key, breath.key):
            with self.subTest(skill_key=skill_key):
                self._run(CmdCombatCommand, f"a2 skill {skill_key}=e1")
                entry = read_session(self.char1).draft_entries[self.companion.pk]
                self.assertEqual(entry["payload"]["targets_or_shorthand"], [])
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        self.assertEqual(read_session(self.char1).rounds_elapsed, 1)
        self.assertLess(self.companion.traits.mp.current, 50)

    @covers_requirement("player-combat-session::all-personal-skill-choices-and-costs-are-actor-scoped")
    def test_valid_scale_admits_the_actors_own_cost(self):
        mastery = SYNTH_SKILLS["t_glowmire_mastery"]
        grant_lineage(
            self.companion,
            [_TIDE_ARC.key],
            [mastery.key],
            rungs={_TIDE_ARC.key: 1},
        )
        engage(self.char1, self.monster)
        self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}@1/2=e1")
        entry = read_session(self.char1).draft_entries[self.companion.pk]
        self.assertEqual(entry["payload"]["scale"], 0.5)
        self.assertEqual(entry["payload"]["targets_or_shorthand"], [self.monster.pk])
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        # Half of the companion's own 10 MP cost, charged to the companion.
        self.assertEqual(self.companion.traits.mp.current, 45)

    @covers_requirement("inventory-item-actions::text-clients-expose-the-same-deterministic-item-operations")
    def test_item_rejections_keep_the_item_reason_prose(self):
        from world.rules.service_messages import rejection_message as item_message

        engage(self.char1, self.monster)
        before = read_session(self.char1)
        self.assertEqual(
            self._run(CmdCombatCommand, "a1 item t_ember_spray"),
            item_message("item_not_held"),
        )
        self.companion.traits.hp.current = self.companion.traits.hp.base
        self.assertEqual(
            self._run(CmdCombatCommand, "a2 item t_ember_spray"),
            item_message("hp_full"),
        )
        self.assertEqual(read_session(self.char1), before)

    @covers_requirement("player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_draft_progress_names_the_member_specific_reason(self):
        from world.rules.action import RejectReason

        engage(self.char1, self.monster)
        self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1")
        # The companion's own resources change before the leader confirms, so
        # its admitted entry is no longer valid and the reason is reported
        # with the member it belongs to.
        self.companion.traits.mp.current = 0
        text = self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
        self.assertIn("指令已確認，等待其他成員。", text)
        self.assertIn("a2 需要重新選擇", text)
        self.assertIn(rejection_message(RejectReason.INSUFFICIENT_RESOURCE), text)
        self.assertEqual(read_session(self.char1).rounds_elapsed, 0)

    @covers_requirement("player-combat-session::telnet-combat-discovery-and-target-tokens-have-rule-parity")
    def test_default_listing_stays_on_the_commander_after_a_saved_entry(self):
        engage(self.char1, self.monster)
        self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1")
        text = self._run(CmdCombatActions, "")
        self.assertIn("a1＝", text)
        self.assertIn(_SPELL, text)
        self.assertIn(f"a2 已選：技能 {_TIDE_ARC.key}=e1", text)
        # The default listing is the commander's own menu, even while the
        # companion is the member still to choose.
        self.assertNotIn(_TIDE_ARC.key, text[: text.index("目標代號：")])


class FullTextPartyRoundTests(BattlefieldIsolation, EvenniaTest):
    """One real text path through skill, item, revision and confirmed exit."""

    def setUp(self):
        open_synthetic_scope(self, *_SCOPE_LOGICALS, extra=_scope_extra())
        super().setUp()
        self.room = create_object(Room, key="text party room")
        self.char1.location = self.room
        self.char1.race = "t_duskmari"
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        self.char1.traits.mp.base = 50
        self.char1.traits.mp.current = 50
        grant_lineage(self.char1, [_SPELL])
        self.companion = self._companion()
        self.monster = _monster("text party goblin", hp=400)
        self.monster.location = self.room
        self.sent: list[str] = []
        self.char1.msg = lambda text="", **kwargs: self.sent.append(str(text))

    def _companion(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        npc = create_object(NPC, key="text party companion")
        npc.location = self.room
        npc.race = "t_duskmari"
        npc.apply_race_baseline()
        npc.traits.hp.base = 100
        npc.traits.hp.current = 50
        npc.db.skills = {"active": [_TIDE_ARC.key], "passive": []}
        npc.db.inventory = ["t_ember_spray"]
        join_party(npc, self.char1)
        return npc

    def _run(self, command_class, args=""):
        command = command_class()
        command.caller = self.char1
        command.args = args
        self.sent.clear()
        command.func()
        return "\n".join(self.sent)

    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    def test_multi_actor_text_rounds_then_confirmed_exit(self):
        from commands.combat import CmdCombatRetreat

        engage(self.char1, self.monster)
        self.assertIn("必要成員：a1、a2", self._run(CmdCombatActions, ""))
        self.assertIn(
            "指令已確認，等待其他成員。",
            self._run(CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1"),
        )
        with _deterministic_round():
            self._run(CmdCombatCommand, f"a1 skill {_SPELL}=e1")
            self.assertIn(
                "指令已確認，等待其他成員。",
                self._run(CmdCombatCommand, "a2 item t_ember_spray"),
            )
            self._run(CmdCombatCommand, "a1 defend")
        record = read_session(self.char1)
        self.assertEqual(record.rounds_elapsed, 2)
        self.assertEqual(record.draft_entries, {})
        self.assertEqual(self.companion.db.inventory.count("t_ember_spray"), 0)
        # The confirmed exit is the party-scoped retreat prompt's own token;
        # the party is faster than its pursuer, so the contest succeeds.
        self.char1.traits.agility.base = 500
        self.monster.traits.agility.base = 0
        prompt = self._run(CmdCombatRetreat, "")
        self.assertIn("combat retreat confirm", prompt)
        token = re.search(r"confirm ([A-Z0-9]+-[0-9]+-[0-9A-F]{20})", prompt).group(1)
        self.assertTrue(self._run(CmdCombatRetreat, f"confirm {token}").strip())
        self.assertIsNone(self.char1.db.active_combat)

    @covers_requirement("player-combat-session::text-clients-can-complete-and-revise-every-party-command-kind")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_failed_retreat_keeps_the_party_and_discards_the_whole_text_draft(self):
        """The assembled text transcript: actor menu/target parity, then a
        failed retreat that runs one enemy round and discards the saved draft.

        The listing for the companion is the same actor-local menu the browser
        card renders (its own skill and item, never the commander's spell),
        the enemy target token reaches the same candidate, and the confirmed
        retreat prompt's token is what settles. A failing contest keeps the
        whole party together, consumes exactly one round and leaves the
        discarded command unexecuted and its resources unspent.
        """
        from commands.combat import CmdCombatRetreat
        from world.rules.combat_session import engage, resolve_target_token
        from world.rules.party import party_ids

        engage(self.char1, self.monster)
        panel = self._panel_for_actor(self.companion)
        listing = self._run(CmdCombatActions, "a2")
        for skill in (
            skill
            for category in panel["choices"]["skills"]
            for group in category.get("groups") or []
            for skill in group.get("skills") or []
        ):
            self.assertIn(skill["key"], listing, "the text menu names the same skill rows")
        for item in panel["choices"]["items"]:
            self.assertIn(item["key"], listing, "the text menu names the same item rows")
        self.assertNotIn(_SPELL, listing, "the commander's own spell is never offered")

        # The panel's own candidate token reaches the enemy the command names.
        foe = next(
            participant["identity"]
            for participant in panel["participants"]
            if participant["team"] == "foes"
        )
        self.assertEqual(getattr(resolve_target_token(self.char1, "e1"), "pk", None), foe)
        confirmed = self._run(
            CmdCombatCommand, f"a2 skill {_TIDE_ARC.key}=e1"
        )
        self.assertIn("指令已確認", confirmed)
        record = read_session(self.char1)
        self.assertEqual(list(record.draft_entries), [self.companion.pk])
        mp_before = self.companion.traits.mp.current

        # The pursuer is far faster: the contested retreat fails
        # deterministically, running the ordinary enemy round once.
        self.char1.traits.agility.base = 0
        self.monster.traits.agility.base = 500
        prompt = self._run(CmdCombatRetreat, "")
        self.assertIn("撤退", prompt)
        token = re.search(r"confirm ([A-Z0-9]+-[0-9]+-[0-9A-F]{20})", prompt).group(1)
        with _deterministic_round():
            settled = self._run(CmdCombatRetreat, f"confirm {token}")
        self.assertTrue(settled.strip())
        current = read_session(self.char1)
        self.assertTrue(current.session_id)
        self.assertEqual((current.rounds_elapsed, current.round_revision), (1, 1))
        self.assertEqual(current.draft_entries, {}, "the whole saved draft was discarded")
        # The discarded command never executed: no item, no MP spent.
        self.assertEqual(self.companion.db.inventory.count("t_ember_spray"), 1)
        self.assertEqual(self.companion.traits.mp.current, mp_before)
        self.assertEqual(
            party_ids(self.char1),
            [self.companion.pk],
            "a failed retreat carries no member out of the party",
        )

    def _panel_for_actor(self, actor):
        from world.rules.combat_view import build_combat_view

        view = build_combat_view(self.char1, for_actor=actor)
        return {
            "choices": {
                "skills": [
                    {
                        "label": category.label,
                        "key": category.category,
                        "groups": [
                            {
                                "skills": [
                                    {"key": skill.key}
                                    for skill in group.skills
                                ]
                            }
                            for group in category.groups
                        ],
                    }
                    for category in view.choices.skills
                ],
                "items": [{"key": item.item_key} for item in view.choices.items],
            },
            "participants": [
                {"identity": participant.identity, "team": participant.team}
                for participant in view.participants
            ],
        }


class CastCommandSettlementSurfaceTests(unittest.TestCase):
    """Source-inspection: the out-of-combat cast boundary is the settlement API.

    The settlement call returns only after the outer transaction commits, so
    the command's success rendering is post-commit by construction; the
    in-combat session path must never touch the settlement or the clock.
    """

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_out_of_combat_cast_delegates_to_the_settlement(self):
        import inspect

        source = inspect.getsource(CmdCast._cast_out_of_combat)
        self.assertIn("cast_in_field", source)
        self.assertNotIn("get_world_clock", source)
        self.assertNotIn("ActionResolver.resolve", source)
        self.assertNotIn("AdvanceSource", source)

        from world.rules.field_cast import cast_in_field

        field_source = inspect.getsource(cast_in_field)
        self.assertIn("settle_out_of_combat_cast", field_source)
        self.assertNotIn("get_world_clock", field_source)
        self.assertNotIn("ActionResolver.resolve", field_source)
        self.assertNotIn("AdvanceSource", field_source)

    def test_in_combat_session_cast_path_is_unchanged(self):
        import inspect

        source = inspect.getsource(CmdCast._cast_in_session)
        self.assertIn("submit_player_action", source)
        self.assertNotIn("settle_out_of_combat_cast", source)
        self.assertNotIn("get_world_clock", source)
        self.assertNotIn("AdvanceSource", source)


if __name__ == "__main__":
    import unittest

    unittest.main()
