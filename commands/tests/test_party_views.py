"""Command tests for the ``狀態`` and ``技能`` member text views.

The commands resolve the commander by default and a named party member by
token (membership only), render the version-9 character read model, and write
nothing. The assertions establish the true-value guarantee under disguise, the
possession-identical output, the shared refusal line, and parity between every
printed skill fact and the presenter payload for the same member.

Canonical requirement IDs for the added ``party-member-text-views`` capability
(``covers_requirement`` annotations follow the archive spec sync; the
pre-archive traceability tool rejects delta-only IDs):

- ``party-member-text-views::狀態-shows-a-member-s-true-status``
- ``party-member-text-views::技能-shows-a-member-s-skills-and-growth``
- ``party-member-text-views::member-views-are-documented-and-possession-identical``
"""

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.default_cmdsets import CharacterCmdSet
from commands.party_views import (
    CmdMemberSkills,
    CmdMemberStatus,
    member_status_text,
    skills_text,
)
from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import PartyViewSelection
from web.webclient.presentation.registry import build_production_registry
from world.rules.buffs import apply_buff
from world.rules.clock import read_world_clock
from world.rules.combat_modifiers import Rule
from world.rules.party import join_party
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    REASON_NOT_PARTY_MEMBER,
)
from world.rules.possession import enter_possession
from world.rules.progression import SKILL_PROFICIENCY_XP_PER_LEVEL
from world.rules.status_display import ConditionDisplay
from world.rules.status_query import TRAIT_LABELS, build_character_read_model
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.unlock_notices import MemberUnlocks, unlock_flags
from world.skills.registry import validate_prerequisite_graph
from world.tests.synthetic_data import SYNTH_BUFFS, SYNTH_RACES, SYNTH_SKILLS

T_EMBER = SYNTH_SKILLS["t_ember_burst"].key
T_COMET = SYNTH_SKILLS["t_ember_comet"].key
T_HUSH = SYNTH_SKILLS["t_hush_mend"].key
T_STEADY = SYNTH_SKILLS["t_steady_stride"].key
T_BLOOM = SYNTH_SKILLS["t_glowmire_bloom"].key
T_MASTERY = SYNTH_SKILLS["t_glowmire_mastery"].key


def _g(value):
    """The command's number form (an integer-looking float prints bare)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return format(value, "g")


def _owners(cmdset, token):
    return [
        command
        for command in cmdset.commands
        if command.key == token
        or token
        in (
            (command.aliases,)
            if isinstance(command.aliases, str)
            else command.aliases
        )
    ]


def _revalidate_lineage() -> None:
    validate_prerequisite_graph(live_skill_registry())


def _attribute_state(entity):
    return sorted(
        (
            (
                attribute.key,
                attribute.category or "",
                deepcopy(attribute.value),
            )
            for attribute in entity.attributes.all()
        ),
        key=lambda item: item[:2],
    )


class MemberViewCommandTests(
    BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest
):
    def setUp(self):
        self.addCleanup(_revalidate_lineage)
        open_synthetic_scope(
            self,
            "races",
            "static_tiers",
            "subraces",
            "skills",
            "elements",
            "buffs",
            "items",
        )
        _revalidate_lineage()
        super().setUp()
        self.commander = self.char1
        self.commander.race = next(iter(SYNTH_RACES))
        self.commander.apply_race_baseline()
        self.commander.location = self.room1
        self.companion = create_object(
            NPC, key="艾拉", location=self.room1, home=self.room1
        )
        self.companion.race = next(iter(SYNTH_RACES))
        self.companion.apply_race_baseline()
        join_party(self.companion, self.commander)

    def _payload(self, member, *, skill_key=None, recent=frozenset()):
        selection = (
            None
            if skill_key is None
            else PartyViewSelection(
                int(self.commander.pk), int(member.pk), "skills", skill_key
            )
        )
        context = PresentationContext(
            actor=self.commander,
            protocol_version=1,
            party_view=selection,
            unlocks={
                int(member.pk): MemberUnlocks(False, frozenset(recent)),
            },
        )
        return build_production_registry().render("character", context)

    def _rows(self, payload):
        return {
            row["key"]: row
            for category in payload["actives"]
            for group in category["groups"]
            for row in group["skills"]
        }

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    def test_status_default_names_the_commander_and_shows_the_breakdown(self):
        output = self.call(CmdMemberStatus(), "")
        self.assertEqual(output, member_status_text(self.commander))
        model = build_character_read_model(self.commander)
        for row in model.breakdown:
            label = TRAIT_LABELS.get(row.key, row.key)
            if row.key in ("hp", "mp", "sp"):
                head = f"{label}：{_g(row.current)}／{_g(row.effective)}"
            else:
                head = f"{label}：{_g(row.current)}"
            self.assertIn(head, output)
            self.assertIn(f"基礎 {_g(row.base)}", output)

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    def test_a_disguised_companion_keeps_true_traits_and_labels_the_display(self):
        self.companion.db.disguised_stats = {"atk_phys": 999, "agility": 888}
        output = self.call(CmdMemberStatus(), "艾拉")
        model = build_character_read_model(self.companion)
        atk = next(row for row in model.breakdown if row.key == "atk_phys")
        agility = next(row for row in model.breakdown if row.key == "agility")
        self.assertIn(f"攻擊：{_g(atk.current)}", output)
        self.assertIn(f"敏捷：{_g(agility.current)}", output)
        self.assertIn("偽裝（顯示數值，非真實數值）：", output)
        self.assertIn("攻擊：999", output)
        self.assertIn("敏捷：888", output)
        # The disguised values never replace the true trait rows.
        self.assertNotIn("攻擊：999（基礎", output)
        self.assertNotIn("敏捷：888（基礎", output)

    @covers_requirement(
        "party-member-text-views::member-views-are-documented-and-possession-identical"
    )
    def test_possession_does_not_change_the_view(self):
        before = self.call(CmdMemberStatus(), "")
        enter_possession(self.commander, self.companion)
        after = self.call(CmdMemberStatus(), "", caller=self.companion)
        self.assertEqual(after, before)
        explicit = self.call(CmdMemberStatus(), "艾拉", caller=self.companion)
        self.assertEqual(explicit, self.call(CmdMemberStatus(), "艾拉"))

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    def test_a_non_member_is_refused_with_only_the_shared_message(self):
        output = self.call(CmdMemberStatus(), "不存在的人")
        self.assertEqual(output, PARTY_SCOPE_MESSAGES[REASON_NOT_PARTY_MEMBER])

    def test_an_absent_member_is_still_viewable(self):
        self.companion.location = None
        output = self.call(CmdMemberStatus(), "艾拉")
        self.assertIn("狀態：艾拉", output)

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    def test_conditions_carry_duration_modifiers_and_source(self):
        buff_key = next(iter(SYNTH_BUFFS))
        rule = Rule(
            "t_synthetic_condition", {"dual_wielding": False}, {"defense": -2}
        )
        apply_buff(self.companion, buff_key)

        with patch("world.rules.combat_modifiers._RULES", [rule]), patch.dict(
            "world.rules.status_display.STATUS_DISPLAY",
            {
                buff_key: ConditionDisplay(
                    buff_key, "合成苔幕", "beneficial"
                ),
                rule.id: ConditionDisplay(rule.id, "合成疲勞", "warning"),
            },
        ):
            output = self.call(CmdMemberStatus(), "艾拉")
        duration = SYNTH_BUFFS[buff_key].duration
        self.assertIn(f"合成苔幕｜剩餘 {duration} 秒｜來源：狀態", output)
        self.assertIn("合成疲勞｜持續｜防禦 -2｜來源：狀態", output)

    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    def test_skill_rows_match_the_v9_presenter_facts(self):
        grant_lineage(
            self.commander,
            [T_EMBER, T_COMET, T_HUSH],
            [T_STEADY],
        )
        proficiency = dict(self.commander.db.skill_proficiency or {})
        proficiency[T_EMBER] = 10_000.0
        proficiency[T_HUSH] = SKILL_PROFICIENCY_XP_PER_LEVEL + 20
        self.commander.db.skill_proficiency = proficiency
        self.commander.db.practice_booking = T_HUSH
        recent = frozenset({T_EMBER})
        self.session.ndb.party_unlocks = {
            int(self.commander.pk): MemberUnlocks(False, recent),
        }

        payload = self._payload(self.commander, recent=recent)
        rows = self._rows(payload)
        output = self.call(CmdMemberSkills(), "")

        for key in (T_EMBER, T_COMET, T_HUSH):
            row = rows[key]
            line = f"{row['label']} Lv.{row['level']}"
            self.assertIn(line, output)
            if row["capped"]:
                self.assertIn(f"{line}（見頂）", output)
            else:
                total = row["xp_into_level"] + row["xp_to_next_level"]
                self.assertIn(
                    f"{line}（熟練 {_g(row['xp_into_level'])}/{_g(total)}）",
                    output,
                )
        self.assertIn(f"{rows[T_HUSH]['label']} Lv.{rows[T_HUSH]['level']}", output)
        self.assertIn("［修煉中］", output)
        self.assertIn("［新］", output)
        passives = {
            row["key"]: row
            for category in payload["passives"]
            for group in category["groups"]
            for row in group["skills"]
        }
        self.assertIn(passives[T_STEADY]["label"], output)

        # The printed lineage equals the presenter's selected-skill position.
        for key in (T_EMBER, T_COMET):
            selected = self._payload(
                self.commander, skill_key=key, recent=recent
            )["selected_skill"]["lineage"]
            for edge in selected["prerequisites"]:
                self.assertIn(f"前置：{edge['label']} Lv.{edge['level']}", output)
            for edge in selected["next"]:
                self.assertIn(f"解鎖：{edge['label']} Lv.{edge['min_level']}", output)
        self.assertTrue(
            self._payload(self.commander, skill_key=T_EMBER)["selected_skill"][
                "lineage"
            ]["next"]
        )

    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    def test_ladder_matches_the_v9_selected_skill(self):
        grant_lineage(
            self.companion,
            [T_BLOOM],
            [T_MASTERY],
            rungs={T_BLOOM: 10},
        )
        payload = self._payload(self.companion, skill_key=T_BLOOM)
        ladder = payload["selected_skill"]["freeform_ladder"]
        self.assertTrue(ladder)
        output = self.call(CmdMemberSkills(), "艾拉")
        for rung in ladder:
            if "mp_cost" in rung:
                self.assertIn(f"{rung['label']} MP {rung['mp_cost']}", output)
            else:
                self.assertIn(
                    f"{rung['label']} 需 Lv.{rung['unlock_level']}", output
                )

    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    def test_member_view_keys_and_aliases_are_unique_in_the_character_cmdset(self):
        cmdset = CharacterCmdSet()
        for token, key in (
            ("狀態", "狀態"),
            ("status", "狀態"),
            ("技能", "技能"),
            ("skills", "技能"),
        ):
            owners = _owners(cmdset, token)
            self.assertEqual(len(owners), 1, f"{token!r} is not uniquely owned")
            self.assertEqual(owners[0].key, key)

    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    def test_skill_helper_equals_the_command_output(self):
        output = self.call(CmdMemberSkills(), "")
        self.assertEqual(output, skills_text(self.commander))

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    def test_both_views_write_nothing(self):
        grant_lineage(
            self.companion,
            [T_BLOOM],
            [T_MASTERY],
            rungs={T_BLOOM: 10},
        )
        before = _attribute_state(self.companion)
        clock_before = read_world_clock()
        self.call(CmdMemberStatus(), "艾拉")
        self.call(CmdMemberSkills(), "艾拉")
        self.assertEqual(_attribute_state(self.companion), before)
        self.assertEqual(read_world_clock(), clock_before)

    @covers_requirement(
        "party-member-text-views::技能-shows-a-member-s-skills-and-growth"
    )
    @covers_requirement(
        "party-member-text-views::member-views-are-documented-and-possession-identical"
    )
    def test_skill_session_marks_survive_possession(self):
        grant_lineage(self.commander, [T_EMBER, T_HUSH])
        grant_lineage(
            self.companion,
            [T_BLOOM],
            [T_MASTERY],
            rungs={T_BLOOM: 10},
        )
        self.commander.db.practice_booking = T_HUSH
        self.session.ndb.party_unlocks = {
            int(self.commander.pk): MemberUnlocks(False, frozenset({T_EMBER})),
            int(self.companion.pk): MemberUnlocks(False, frozenset({T_BLOOM})),
        }
        commander_before = self.call(CmdMemberSkills(), "")
        companion_before = self.call(CmdMemberSkills(), "艾拉")

        def line_for(output, key):
            label = SYNTH_SKILLS[key].label
            return next(line for line in output.splitlines() if label in line)

        self.assertIn("［新］", line_for(commander_before, T_EMBER))
        self.assertIn("［修煉中］", line_for(commander_before, T_HUSH))
        self.assertIn("［新］", line_for(companion_before, T_BLOOM))

        enter_possession(self.commander, self.companion)
        self.assertEqual(
            self.call(CmdMemberSkills(), "", caller=self.companion),
            commander_before,
        )
        self.assertEqual(
            self.call(CmdMemberSkills(), "艾拉", caller=self.companion),
            companion_before,
        )

    @covers_requirement("party-member-text-views::狀態-shows-a-member-s-true-status")
    def test_both_views_resolve_in_active_combat(self):
        from typeclasses.monsters import Monster
        from world.rules.combat_session import engage
        from world.rules.tests._combat_session_helpers import _monster

        monster = _monster("合成魔物", hp=100, atk=1)
        monster.location = self.room1
        engage(self.commander, monster)
        cmdset = self.commander.cmdset.current
        for token, command_class in (
            ("狀態", CmdMemberStatus),
            ("技能", CmdMemberSkills),
        ):
            command = cmdset.get(token)
            self.assertIsInstance(command, command_class)
            output = self.call(command, "", caller=self.commander)
            self.assertNotEqual(output, command_class.unavailable)
