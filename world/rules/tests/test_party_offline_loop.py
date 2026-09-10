"""Chained offline party-quest loop test (affinity-party design §7).

Proves the complete deterministic journey with every LLM layer disabled:
offline-threshold ``invite`` → companion follow through a real Exit (no
extra time cost) → joint combat (the companion joins the allied team and the
DEFEAT objective advances) → guild turn-in paying +2 affinity to the
then-in-party companion → ``leave`` dismissal. Each segment has its own
focused offline tests; this single test pins the whole loop so a future
regression cannot hide behind per-segment coverage.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.components import GuildStaff
from typeclasses.exits import Exit
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from commands.invite import CmdInvite
from commands.leave import CmdLeave
from world.ai import guardrail
from world.ai.fake_client import FakeLLMClient
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.quests.bootstrap import sync_quest_runtime
from world.quests.definitions import (
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
)
from world.quests.runtime import QuestState, read_records
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.combat_session import engage, read_session, submit_player_action
from world.rules.guild import (
    parse_reward_claims,
    register_adventurer,
    turn_in_quest,
)
from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    accept_guild_offer,
    list_guild_offers,
    register_guild_offer,
)
from world.rules.party import (
    DEGRADED_ACCEPT_MESSAGE,
    JOINED_MESSAGE,
    LEAVE_DISMISSED_MESSAGE,
    is_companion,
)
from world.rules.surfaces import read_counter_trait
from world.rules.tests._combat_session_helpers import (
    _monster_tier_key,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.tests.synthetic_data import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_ITEMS,
    SYNTH_SKILLS,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

# The offline loop runs entirely on kit rows: the issuing branch is the kit
# guild branch, the cast is a kit spell, and the reward item is a kit potion.
# The hunt definition is this file's own one-kill DEFEAT card (defeat-count
# progression is catalog-agnostic), with the monster tier arriving through the
# runtime probe so monster rounds keep resolving against the LIVE tier
# vocabulary (monster_tiers is deliberately never scoped).
ALTORIA_BRANCH = SYNTH_GUILD_BRANCH_KEY
_T_CAST = SYNTH_SKILLS["t_ember_burst"].key
_T_ITEM = "t_ember_spray"
_T_HUNT = "t_party_loop_hunt"
_T_COMPANION_KEY = "艾洛希雅"
_T_MONSTER_NAME = "合成微光蟲"
_T_MONSTER_HP = 1
_T_REWARD_COPPER = 50
_T_REWARD_MERIT = 25
_T_REWARD_QTY = 2
_T_SEED_AFFINITY = 70
_T_EXPECTED_AFFINITY_AFTER_TURNIN = 72
_T_MAGIC_POWER = 30
_MOVE = CLOCK_YAML["command_defaults"]["move"]
_SCOPE_LOGICALS = (
    "guild_branches",
    "skills",
    "elements",
    "items",
    "races",
    "subraces",
    "static_tiers",
)

def _hunt_definition() -> QuestDefinition:
    return QuestDefinition(
        key=_T_HUNT,
        display_name="合成微光蟲清剿",
        quest_type=QuestType.DEFEAT,
        rank="F",
        stages=(
            QuestStage(
                0,
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    monster_tier=_monster_tier_key(),
                ),
            ),
        ),
    )


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _reset_all():
    guardrail._semantic_validators.clear()
    guardrail._degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


class OfflinePartyQuestLoopTests(BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """The design §7 offline full loop: invite → follow → combat → turn-in → dismiss."""

    def setUp(self):
        # Scope before construction: staff branch validation, entity races,
        # the cast, and the reward item all resolve inside the synthetic
        # registries; the monster tier vocabulary stays live for the round.
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, extra=synth_innate_overlay()
        )
        super().setUp()
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._quest_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        self.addCleanup(self._restore_registries)
        _reset_all()
        register_npc_dialogue()
        # Runtime composition (planner registration + catalog vocabulary for
        # the affinity rulebook's cap-break validation) is restored as before;
        # the loop's visible board stays offer-driven.
        sync_quest_runtime()
        QUEST_DEFINITION_REGISTRY.setdefault(_T_HUNT, _hunt_definition())
        self.hall = create_object(Room, key="公會大廳")
        self.hunt_ground = create_object(Room, key="南郊狩獵場")
        self.door = create_object(
            Exit, key="城門", location=self.hall, destination=self.hunt_ground
        )
        self.staff = create_object(NPC, key="公會接待員", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=ALTORIA_BRANCH)
        )
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        # Static magic_power raised to the kit spell's tuning threshold.
        self.char1.traits.magic_power.base = _T_MAGIC_POWER
        grant_lineage(self.char1, [_T_CAST])
        self.char1.location = self.hall
        register_adventurer(self.char1, self.staff)
        register_guild_offer(
            GuildQuestOffer(
                definition_key=_T_HUNT,
                issuer_branch_key=ALTORIA_BRANCH,
                reward=QuestReward(
                    copper=_T_REWARD_COPPER,
                    items=(ItemQuantity(_T_ITEM, _T_REWARD_QTY),),
                    merit=_T_REWARD_MERIT,
                ),
            )
        )
        self.companion = create_object(
            LLMNPC, key=_T_COMPANION_KEY, location=self.hall
        )
        self.companion.race = _race_key()
        self.companion.apply_race_baseline()
        apply_affinity_change(
            self.companion,
            self.char1,
            AffinitySource.QUEST_COMPLETION,
            _T_SEED_AFFINITY,
        )

    def _restore_registries(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._quest_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)

    def tearDown(self):
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._quest_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        _reset_all()
        super().tearDown()

    @covers_requirement("party-system::the-invite-command-proposes-a-party-through-the-ai-judged-dialogue-seam")
    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    @covers_requirement("party-system::companions-assist-the-player-s-quest-objectives")
    @covers_requirement("party-system::completing-a-quest-rewards-each-then-in-party-companion-with-affinity")
    @covers_requirement("party-system::the-leave-command-dismisses-a-companion-without-affinity-change")
    def test_full_offline_loop_completes_with_no_llm_call(self):
        client = FakeLLMClient()
        disabled = {
            layer: {"enabled": False}
            for layer in ("narrator", "npc_dialogue", "scenario_director", "scene_builder")
        }
        with override_settings(LLM_PROFILES=_raw(**disabled)):
            with patch(
                "web.webclient.actions.dialogue_composition.build_dialogue_client",
                return_value=client,
            ):
                output = self.call(CmdInvite(), _T_COMPANION_KEY)
        self.assertIn(DEGRADED_ACCEPT_MESSAGE, output)
        self.assertIn(JOINED_MESSAGE, output)
        self.assertTrue(is_companion(self.companion, self.char1))
        self.assertEqual(len(client.calls), 0)

        offers = list_guild_offers(self.char1, self.staff)
        self.assertEqual([offer.definition_key for offer in offers], [_T_HUNT])
        record = accept_guild_offer(self.char1, self.staff, _T_HUNT)
        quest_id = record.quest_id

        tick_before = get_world_clock().tick
        self.door.at_traverse(self.char1, self.hunt_ground)
        self.assertIs(self.char1.location, self.hunt_ground)
        self.assertIs(self.companion.location, self.hunt_ground)
        self.assertEqual(get_world_clock().tick, tick_before + _MOVE)

        monster = create_object(
            Monster, key=_T_MONSTER_NAME, location=self.hunt_ground
        )
        monster.threat_tier = _monster_tier_key()
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = _T_MONSTER_HP
        monster.traits.hp.current = _T_MONSTER_HP
        engage(self.char1, monster)
        session = read_session(self.char1)
        self.assertIn(int(self.companion.pk), session.player_ids)
        with patch("world.rules.combat.roll_d100", return_value=100):
            outcome = submit_player_action(self.char1, _T_CAST, [monster])
        self.assertEqual(outcome["outcome"], "victory")
        self.assertIsNone(read_session(self.char1))
        completed = [r for r in read_records(self.char1) if r.quest_id == quest_id]
        self.assertEqual(completed[0].state, QuestState.COMPLETED)

        self.door.at_traverse(self.char1, self.hall)
        result = turn_in_quest(self.char1, self.staff, quest_id)
        self.assertEqual(result["copper"], _T_REWARD_COPPER)
        self.assertEqual(result["merit"], _T_REWARD_MERIT)
        self.assertEqual(self.char1.db.wallet, _T_REWARD_COPPER)
        self.assertEqual(
            read_counter_trait(self.char1, "guild_merit"), _T_REWARD_MERIT
        )
        self.assertIn(_T_ITEM, self.char1.db.inventory)
        self.assertEqual(parse_reward_claims(self.char1), [quest_id])
        self.assertEqual(
            self.companion.relations.affinity_for(self.char1),
            _T_EXPECTED_AFFINITY_AFTER_TURNIN,
        )

        before = self.companion.relations.affinity_for(self.char1)
        output = self.call(CmdLeave(), _T_COMPANION_KEY)
        self.assertIn(LEAVE_DISMISSED_MESSAGE, output)
        self.assertFalse(is_companion(self.companion, self.char1))
        self.assertIsNone(self.companion.db.party_member)
        self.assertEqual(self.companion.relations.affinity_for(self.char1), before)
