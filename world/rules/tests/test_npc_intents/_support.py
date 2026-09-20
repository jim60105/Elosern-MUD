"""NPC-intent fixtures and isolation bases for the `test_npc_intents` slices.

Module-level fixtures, helpers, and the registry-isolation base moved verbatim
from the original flat module (not a collected test module).
"""
import inspect


from unittest.mock import patch


import unittest


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from typeclasses.components import GuildExaminer, GuildStaff, QuestIssuer


from typeclasses.npcs import NPC


from typeclasses.rooms import Room


from world.quests.catalog import register_catalog


from world.quests.definitions import QuestStage


from world.quests.runtime import QuestState, read_records


from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire as _acquire,
    quest as _quest,
    register as _register_quest,
)


from world.rules.combat_session import read_session


from world.rules.guild import GuildDataError, register_adventurer


from world.rules.guild_config import CATALOG


from world.rules.guild_exams import ExamState, _read_exams


from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)


from world.rules.npc_intents import (
    STALE_CONTEXT_REASON,
    IntentOutcome,
    _apply_plan,
    apply_npc_intent,
    intent_context_ok,
    is_stale_context,
)


from world.rules.quest_issuance import (
    QuestIssuance,
    Settlement,
    guild_issuer_key,
    npc_issuer_key,
    register_quest_issuance,
    resolve_issuance,
)


from world.rules.surfaces import write_counter_trait


from world.rules.tests._combat_session_helpers import open_synthetic_scope


from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
)


from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS


from tools.spec_traceability import covers_requirement


# Intent application runs on kit rows: the exam/offer branch is the kit guild
# branch and transferred items are the kit potion row (scoped registries
# validate them), so no shipped content key is named below.
BRANCH = SYNTH_GUILD_BRANCH_KEY


T_ITEM = SYNTH_ITEMS["t_ember_spray"].key


class ExamRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        # Examiner/staff branches resolve against the kit branch row, and the
        # exam path reads the synthetic catalog (invented E-through-S
        # thresholds) instead of the shipped rulebook.
        open_synthetic_scope(self, "guild_branches")
        super().setUp()
        register_catalog()
        install_synthetic_catalog(self, synth_catalog())
        self._previous_catalog = CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        import world.rules.guild_config as guild_config
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        guild_config.CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


def _exam_intent(target_rank="E"):
    return {"kind": "request_guild_exam", "target_rank": target_rank}


if __name__ == "__main__":
    unittest.main()


