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
from .combat_fixtures import BattlefieldIsolation, grant_lineage

ALTORIA_BRANCH = "guild_branch_altoria"
MOVE = CLOCK_YAML["command_defaults"]["move"]


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
        super().setUp()
        from world.quests.catalog import register_catalog
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._quest_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        _reset_all()
        register_npc_dialogue()
        register_catalog()
        sync_quest_runtime()
        self.hall = create_object(Room, key="公會大廳")
        self.hunt_ground = create_object(Room, key="南郊狩獵場")
        self.door = create_object(
            Exit, key="城門", location=self.hall, destination=self.hunt_ground
        )
        self.staff = create_object(NPC, key="公會接待員", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(self.staff, service_id="staff", branch_key=ALTORIA_BRANCH)
        )
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        # Human static magic_power at 術師 tier so fire_ball casts pass.
        self.char1.traits.magic_power.base = 30
        grant_lineage(self.char1, ["fire_ball"])
        self.char1.location = self.hall
        register_adventurer(self.char1, self.staff)
        register_guild_offer(
            GuildQuestOffer(
                definition_key="introductory_hunt",
                issuer_branch_key=ALTORIA_BRANCH,
                reward=QuestReward(
                    copper=50,
                    items=(ItemQuantity("healing_potion", 2),),
                    merit=25,
                ),
            )
        )
        self.companion = create_object(LLMNPC, key="艾洛希雅", location=self.hall)
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        apply_affinity_change(
            self.companion, self.char1, AffinitySource.QUEST_COMPLETION, 70
        )

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
                output = self.call(CmdInvite(), "艾洛希雅")
        self.assertIn(DEGRADED_ACCEPT_MESSAGE, output)
        self.assertIn(JOINED_MESSAGE, output)
        self.assertTrue(is_companion(self.companion, self.char1))
        self.assertEqual(len(client.calls), 0)

        offers = list_guild_offers(self.char1, self.staff)
        self.assertEqual(
            [offer.definition_key for offer in offers], ["introductory_hunt"]
        )
        record = accept_guild_offer(self.char1, self.staff, "introductory_hunt")
        quest_id = record.quest_id

        tick_before = get_world_clock().tick
        self.door.at_traverse(self.char1, self.hunt_ground)
        self.assertIs(self.char1.location, self.hunt_ground)
        self.assertIs(self.companion.location, self.hunt_ground)
        self.assertEqual(get_world_clock().tick, tick_before + MOVE)

        monster = create_object(Monster, key="低階哥布林", location=self.hunt_ground)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 1
        monster.traits.hp.current = 1
        engage(self.char1, monster)
        session = read_session(self.char1)
        self.assertIn(int(self.companion.pk), session.player_ids)
        with patch("world.rules.combat.roll_d100", return_value=100):
            outcome = submit_player_action(self.char1, "fire_ball", [monster])
        self.assertEqual(outcome["outcome"], "victory")
        self.assertIsNone(read_session(self.char1))
        completed = [r for r in read_records(self.char1) if r.quest_id == quest_id]
        self.assertEqual(completed[0].state, QuestState.COMPLETED)

        self.door.at_traverse(self.char1, self.hall)
        result = turn_in_quest(self.char1, self.staff, quest_id)
        self.assertEqual(result["copper"], 50)
        self.assertEqual(result["merit"], 25)
        self.assertEqual(self.char1.db.wallet, 50)
        self.assertEqual(read_counter_trait(self.char1, "guild_merit"), 25)
        self.assertIn("healing_potion", self.char1.db.inventory)
        self.assertEqual(parse_reward_claims(self.char1), [quest_id])
        self.assertEqual(self.companion.relations.affinity_for(self.char1), 72)

        before = self.companion.relations.affinity_for(self.char1)
        output = self.call(CmdLeave(), "艾洛希雅")
        self.assertIn(LEAVE_DISMISSED_MESSAGE, output)
        self.assertFalse(is_companion(self.companion, self.char1))
        self.assertIsNone(self.companion.db.party_member)
        self.assertEqual(self.companion.relations.affinity_for(self.char1), before)
