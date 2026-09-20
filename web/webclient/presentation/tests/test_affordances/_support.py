"""Shared module-level helpers for the ``test_affordances`` test package."""


from tools.spec_traceability import covers_requirement

import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, Merchant, ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_CARDS,
    SUGGESTIBLE_ACTION_IDS,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    suggestible_candidates,
)
from web.webclient.actions.exploration_actions import validate_move_payload
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    deliver,
    quest,
    register,
)
from world.rules.combat_session import engage
from world.rules.party import PARTY_MAX_COMPANIONS, join_party
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.tests.synthetic_data import synthetic_registries
from world.rules.time_skip import DAYPARTS, unsafe_rejection
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS

# Kit-authored scripted-dialogue row: the scripted hosts' keywords come from
# here (inside a dialogue scope).
T_DIALOGUE_KEY = "t_synth_lodgekeeper"
_T_KEYWORDS = [response.keyword for response in SYNTH_DIALOGUE[T_DIALOGUE_KEY].responses]
_T_SPRAY = SYNTH_ITEMS["t_ember_spray"].key


def _player(key="詞彙測試"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _monster(key="哥布林", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster


class VocabularyTestCase(EvenniaTestCase):
    """Base fixture class that isolates the module-level battlefield registry.

    The skip-safety registry is keyed by actor pk; a retained test database
    can reuse pks across tests, so any engaged combat must be cleared in both
    directions to keep every test deterministic.
    """

    def setUp(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()

    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        super().tearDown()
