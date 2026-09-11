"""Command-level integration tests for the talk dialogue turn-in surface.

These EvenniaCommandTestMixin cases drive ``talk <npc> 回報`` and
``talk <npc> 回報 <quest_id>`` end to end against a local guild-staff host
carrying the authored ``guild_staff`` dialogue table. The branch identity is
the kit synthetic branch (test-data-independence); the reported quest, its
issuance (resolved from the board offer), and its offer are locally
registered rows restored by the shared quest-registry isolation.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.talk import CmdsTalk
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
)
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestStage,
    QuestType,
    register_quest_definition,
)
from world.quests.catalog import register_catalog
from world.quests.runtime import fulfill_record, read_records
from world.quests.tests._fixtures import QuestRegistryIsolation, defeat
from world.quests.transitions import apply_quest_log_replacement
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    QuestReward,
    register_guild_offer,
)
from world.rules.quest_issuance import (
    guild_issuer_key,
)
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY

# Locally authored quest surface: one bronze-keyed defeat quest, its guild
# commission, and its board offer. Reward copper is this fixture's number.
BRANCH = SYNTH_GUILD_BRANCH_KEY
_QUEST_KEY = "alpha_report"
_REWARD = QuestReward(copper=50, items=(), merit=25)


def _install_reportable_quest() -> None:
    """Register the local definition and board offer (guild issuance seam)."""
    if _QUEST_KEY not in QUEST_DEFINITION_REGISTRY:
        register_quest_definition(
            QuestDefinition(
                key=_QUEST_KEY,
                display_name="測試回報委託",
                quest_type=QuestType.DEFEAT,
                rank="F",
                stages=(QuestStage(0, defeat()),),
            )
        )
    register_guild_offer(
        GuildQuestOffer(
            definition_key=_QUEST_KEY,
            issuer_branch_key=BRANCH,
            reward=_REWARD,
        )
    )


class TalkTurnInCommandIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        # The affinity rulebook validates its cap-break quest key against the
        # live definition registry whenever it (re)loads.
        register_catalog()
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class TalkTurnInCommandTests(TalkTurnInCommandIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "guild_branches")
        super().setUp()
        from world.rules.guild import register_adventurer

        _install_reportable_quest()
        self.hall = create_object(Room, key="guild hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="公會職員", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key=BRANCH
            )
        )
        self.staff.components.add(
            ScriptedDialogue.create(self.staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        register_adventurer(self.char1, self.staff)

    def _complete_quest(self) -> str:
        record = next(
            r for r in read_records(self.char1) if r.definition_key == _QUEST_KEY
        )
        completed = fulfill_record(record, QUEST_DEFINITION_REGISTRY[_QUEST_KEY])
        records = read_records(self.char1)
        apply_quest_log_replacement(
            self.char1,
            [completed if r.quest_id == record.quest_id else r for r in records],
        )
        return completed.quest_id

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_talk_turnin_keyword_lists_reportable_quests(self):
        from commands.guild import CmdGuildAccept

        self.call(CmdGuildAccept(), _QUEST_KEY, "你接取了任務")
        quest_id = self._complete_quest()
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        self.assertIn(quest_id, output)
        self.assertIn("可以交回", output)
        self.assertEqual(read_records(self.char1)[0].state.value, "completed")
        self.assertEqual(self.char1.db.wallet, 0)  # listing never settles

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_talk_turnin_with_quest_id_settles_once(self):
        from commands.guild import CmdGuildAccept

        self.call(CmdGuildAccept(), _QUEST_KEY, "你接取了任務")
        quest_id = self._complete_quest()
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {quest_id}")
        self.assertIn("你回報了任務", output)
        # First-ever claim echoes the starter-epithet grant on this surface.
        self.assertIn("獲得異名：南門新客", output)
        self.assertNotIn("你的第一個日子在這裡圓滿結束", output)
        self.assertEqual(self.char1.db.wallet, _REWARD.copper)
        second = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {quest_id}")
        self.assertIn("無法回報任務", second)
        self.assertEqual(self.char1.db.wallet, _REWARD.copper)

    @covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")
    def test_talk_turnin_later_claims_stay_title_silent(self):
        from commands.guild import CmdGuildAccept

        self.call(CmdGuildAccept(), _QUEST_KEY, "你接取了任務")
        quest_id = self._complete_quest()
        first = self.call(
            CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {quest_id}"
        )
        self.assertIn("獲得異名：南門新客", first)
        from world.quests.runtime import accept_quest
        from world.rules.quest_issuance import guild_issuer_key

        second_record = accept_quest(
            self.char1, _QUEST_KEY, guild_issuer_key(BRANCH)
        )
        completed = fulfill_record(
            second_record, QUEST_DEFINITION_REGISTRY[_QUEST_KEY]
        )
        records = read_records(self.char1)
        apply_quest_log_replacement(
            self.char1,
            [completed if r.quest_id == second_record.quest_id else r for r in records],
        )
        second = self.call(
            CmdsTalk(),
            f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {completed.quest_id}",
        )
        self.assertIn("你回報了任務", second)
        self.assertNotIn("獲得異名", second)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_talk_turnin_keyword_without_reportable_quests_says_so(self):
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        self.assertIn("目前沒有可以交回", output)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_unregistered_player_gets_register_first_guidance(self):
        unregistered = self.char2
        unregistered.location = self.hall
        unregistered.race = "human"
        unregistered.apply_race_baseline()
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}", caller=unregistered)
        self.assertIn("guild register", output)
        self.assertNotIn("可以交回", output)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_turnin_with_ambiguous_staff_is_rejected(self):
        second = create_object(NPC, key="second clerk", location=self.hall)
        second.components.add(
            GuildStaff.create(second, service_id="second", branch_key=BRANCH)
        )
        second.components.add(
            ScriptedDialogue.create(second, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        self.assertIn("這裡沒有公會服務人員", output)

    @covers_requirement("guild-quest-board::player-facing-guild-commands-resolve-one-local-service-host")
    def test_turnin_with_quest_id_and_ambiguous_staff_uses_the_standard_line(self):
        from commands.guild import CmdGuildAccept

        self.call(CmdGuildAccept(), _QUEST_KEY, "你接取了任務")
        quest_id = self._complete_quest()
        second = create_object(NPC, key="second clerk", location=self.hall)
        second.components.add(
            GuildStaff.create(second, service_id="second", branch_key=BRANCH)
        )
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {quest_id}")
        self.assertIn("這裡沒有公會服務人員", output)
        self.assertEqual(self.char1.db.wallet, 0)
        self.assertIn(quest_id, [r["quest_id"] for r in (self.char1.db.quest_log or [])])

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_turnin_keyword_on_a_staff_table_without_staff_component_is_plain(self):
        # A non-staff NPC reusing the guild_staff table answers 回報 with the
        # no-understanding line and never enters the turn-in branch.
        bard = create_object(NPC, key="吟遊詩人", location=self.hall)
        bard.components.add(
            ScriptedDialogue.create(bard, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        output = self.call(CmdsTalk(), f"吟遊詩人 {GUILD_STAFF_TURNIN_KEYWORD} q-1")
        self.assertIn("明白", output)
        self.assertEqual(self.char1.db.wallet, 0)

    def test_unknown_keyword_behaviour_is_unchanged(self):
        output = self.call(CmdsTalk(), "公會職員 謎語")
        self.assertIn("明白", output)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_blocks_scripted_talk_without_any_state_writes(self):
        self.staff.db.schedule_state = "busy"
        before = self.staff.relations.affinity_for(self.char1)
        output = self.call(CmdsTalk(), "公會職員 公會")
        self.assertIn("她現在正忙著，沒有理會你。", output)
        self.assertEqual(self.staff.relations.affinity_for(self.char1), before)

    @covers_requirement("npc-schedule-runtime::schedule-state-gates-npc-directed-interactions-at-every-host-resolving-surface")
    def test_busy_host_blocks_the_turnin_keyword_without_a_claim(self):
        from commands.guild import CmdGuildAccept

        self.call(CmdGuildAccept(), _QUEST_KEY, "你接取了任務")
        quest_id = self._complete_quest()
        self.staff.db.schedule_state = "resting"
        output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} {quest_id}")
        self.assertIn("她現在正忙著，沒有理會你。", output)
        self.assertEqual(self.char1.db.wallet, 0)
        self.assertEqual(read_records(self.char1)[0].state.value, "completed")
