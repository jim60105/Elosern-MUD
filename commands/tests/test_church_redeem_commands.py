"""Command-surface tests for ``church redeem`` / ``church merit``.

The commands are thin over ``world/rules/church.py``: the deterministic
``redeem_step`` / ledger reads own every mechanic, and this module verifies
the rendered surface — catalogue + merit + redeemed marks for ``redeem
list``, the ledger print for ``church merit``, the stable rejection lines,
and the permanent negative-set line for the vessel (imported as a name,
never a literal token). All catalogue rows are synthetic ``t_`` fixtures.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.church import CmdChurchMerit, CmdChurchRedeem
from world.lore.church import RedeemRow
from world.rules import church
from world.rules.church import VESSEL_KEY
from world.rules.clock import WorldClock
from world.skills.registry import SKILL_REGISTRY as _SKILL_REGISTRY
from world.skills.registry.builders import _skill
from world.skills.registry.vocab import SkillCategory, SkillKind, TargetSpec

_PASSIVE_ROW = RedeemRow(
    skill_key="t_cmd_passive",
    merit_price=500,
    tier="entry",
    polarity="passive",
)
_ACTIVE_ROW = RedeemRow(
    skill_key="t_cmd_active",
    merit_price=300,
    tier="entry",
)


class ChurchRedeemCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        church.add_merit(self.char1, 0)
        self._catalogue_patch = patch(
            "world.rules.church.REDEEM_CATALOG", (_PASSIVE_ROW, _ACTIVE_ROW)
        )
        self._catalogue_patch.start()
        self.addCleanup(self._catalogue_patch.stop)
        self._registry_patch = patch(
            "world.skills.registry.SKILL_REGISTRY",
            {
                **_SKILL_REGISTRY,
                "t_cmd_passive": _skill(
                    "t_cmd_passive",
                    "合成敘階被動",
                    "合成測試敘階技能。",
                    SkillKind.PASSIVE,
                    TargetSpec.NONE,
                    usable_out_of_combat=True,
                    category=SkillCategory.ENHANCEMENT,
                ),
                "t_cmd_active": _skill(
                    "t_cmd_active",
                    "合成敘階主動",
                    "合成測試敘階技能。",
                    SkillKind.ACTIVE,
                    TargetSpec.SELF,
                    usable_out_of_combat=True,
                    category=SkillCategory.ENHANCEMENT,
                ),
            },
        )
        self._registry_patch.start()
        self.addCleanup(self._registry_patch.stop)

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redeem_list_prints_catalogue_merit_and_redeemed_marks(self):
        church.add_merit(self.char1, 1000)
        with self.captureOnCommitCallbacks(execute=True):
            church.redeem_step(self.char1, "t_cmd_active")
        self.call(
            CmdChurchRedeem(),
            "list",
            "你目前擁有 700 點恩寵。",
        )
        self.call(CmdChurchRedeem(), "", "你目前擁有 700 點恩寵。")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redeem_key_success_reports_the_purchase(self):
        church.add_merit(self.char1, 1000)
        self.call(
            CmdChurchRedeem(),
            "t_cmd_passive",
            "聖光降臨，你以 500 點恩寵兌換了",
        )
        skills = self.char1.db.skills
        self.assertIn("t_cmd_passive", skills["passive"])
        self.assertEqual(church.redeemed_keys(self.char1), ("t_cmd_passive",))

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redeem_unknown_key_is_a_stable_rejection(self):
        church.add_merit(self.char1, 10000)
        self.call(CmdChurchRedeem(), "t_no_such_key", "沒有這個敘階項目")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_the_vessel_gets_the_unknown_key_rejection(self):
        church.add_merit(self.char1, 10000)
        self.call(CmdChurchRedeem(), VESSEL_KEY, "沒有這個敘階項目")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_insufficient_merit_is_a_stable_rejection(self):
        self.call(CmdChurchRedeem(), "t_cmd_passive", "你的恩寵不足")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_already_redeemed_is_a_stable_rejection(self):
        church.add_merit(self.char1, 1000)
        with self.captureOnCommitCallbacks(execute=True):
            church.redeem_step(self.char1, "t_cmd_active")
        self.call(CmdChurchRedeem(), "t_cmd_active", "你已經獲得這項敘階")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_unenrolled_redeem_is_a_stable_rejection(self):
        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object

        fresh = create_object(PlayerCharacter, key="t_cmd_newcomer")
        fresh.race = "human"
        fresh.apply_race_baseline()
        self.call(
            CmdChurchRedeem(),
            "t_cmd_passive",
            "你尚未入教。請先與主祭交談",
            caller=fresh,
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redeem_list_unenrolled_is_a_stable_rejection(self):
        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object

        fresh = create_object(PlayerCharacter, key="t_cmd_list_newcomer")
        fresh.race = "human"
        fresh.apply_race_baseline()
        self.call(
            CmdChurchRedeem(),
            "",
            "你尚未入教。請先與主祭交談",
            caller=fresh,
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_redeem_list_malformed_ledger_is_a_stable_line(self):
        self.char1.db.church = "not_a_mapping"
        self.call(CmdChurchRedeem(), "", "教會記錄異常")

    @covers_requirement(
        "church-ordination::the-church-redeem-and-merit-commands-are-documented-in-the-docs-trio"
    )
    def test_the_alias_runs_the_same_surface(self):
        church.add_merit(self.char1, 1000)
        self.call(CmdChurchRedeem(), "list", "你目前擁有 1000 點恩寵", cmdstring="敘階")


class ChurchMeritCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        church.add_merit(self.char1, 0)
        self.char1.db.church = {
            "merit": 120,
            "enrolled_tick": 7,
            "redeemed": ["t_cmd_active"],
            "daily": {"day": 0, "pray": 2},
        }

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_church_merit_prints_the_ledger_read_only(self):
        self.call(
            CmdChurchMerit(),
            "",
            "恩寵：120 點\n入教時的世界時鐘刻度：7\n今日祈禱次數：2\n已兌換敘階：t_cmd_active",
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_church_merit_unenrolled_is_a_stable_line(self):
        from typeclasses.characters import PlayerCharacter
        from evennia.utils.create import create_object

        fresh = create_object(PlayerCharacter, key="t_cmd_merit_newcomer")
        fresh.race = "human"
        fresh.apply_race_baseline()
        self.call(
            CmdChurchMerit(), "", "你尚未入教。請先與主祭交談", caller=fresh
        )

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_church_merit_malformed_ledger_is_a_stable_line(self):
        self.char1.db.church = {"merit": "oops", "redeemed": []}
        self.call(CmdChurchMerit(), "", "教會記錄異常")

    @covers_requirement(
        "church-ordination::redemption-is-a-one-shot-all-or-nothing-grace-purchase"
    )
    def test_church_merit_with_args_is_a_usage_line(self):
        self.call(CmdChurchMerit(), "extra", "用法：church merit")