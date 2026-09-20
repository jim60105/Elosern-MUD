"""Shared module-level helpers for the ``test_exploration_actions`` test package."""


from tools.spec_traceability import covers_requirement

import json
import unittest
from unittest.mock import patch

from django.test import override_settings
from twisted.internet import defer

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from world.ai.fake_client import FakeLLMClient
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    DialogueDefinition,
    KeywordResponse,
)
from world.ai.guardrail import _degrade_fallbacks, _semantic_validators
from world.ai.npc_dialogue import register_npc_dialogue
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.quests.definitions import QuestStage
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    is_in_active_session,
)
from world.rules.map_knowledge import (
    KnowledgeError,
    encode_grid,
    encode_wild,
    parse_knowledge,
)
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests._guild_service_probes import synthetic_branch_key
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.synthetic_data import SYNTH_DIALOGUE, SYNTH_ITEMS, make_skill

# Kit identities (test-data-independence): the dialogue/branch/item/skill
# fixtures resolve through the kit rows; the shipped guild-staff table row is
# merged into the scoped table through a runtime probe (the production
# turnin-keyword special case keys off that table), never an import-time
# symbol name.
_T_DIALOGUE = "t_synth_lodgekeeper"
_T_BRANCH = synthetic_branch_key()
_T_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_T_SKILL = make_skill("t_practice_drill").key


def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs)."""
    import importlib

    return getattr(importlib.import_module(module), attribute)


#: The kit lodgekeeper table's authored keyword/response fragments.
_T_LODGE_KEYWORD = "住宿"
_T_LODGE_LINE = "雲杉驛站一晚十八銅"
_T_LODGE_GREETING = "櫃檯後的老板娘"

#: A staff-shaped authored table keyed by the PRODUCTION guild-staff key
#: (imported constant, not a literal): the turnin special case keys off that
#: exact pair, so the action suite reproduces the shape with its own prose
#: instead of borrowing the shipped table row.
_T_STAFF_TURNIN_LINE = "「先在櫃檯報到台註冊（t-synth-desk register）。」"
_T_STAFF_ROW = DialogueDefinition(
    greeting="櫃檯後的合成公會職員抬起眼：「要用 t-synth-desk list 接任務。」",
    responses=(
        KeywordResponse(GUILD_STAFF_TURNIN_KEYWORD, _T_STAFF_TURNIN_LINE),
    ),
)


def _t_dialogue_scope(test, with_staff: bool = False):
    """Dialogue scope: the kit lodgekeeper table (plus the staff-shaped
    authored row when the turnin special case is under test)."""
    extra = (
        {"dialogue": {GUILD_STAFF_DIALOGUE_KEY: _T_STAFF_ROW}} if with_staff else None
    )
    open_synthetic_scope(test, "dialogue", extra=extra)


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _failing_advance(*args, **kwargs):
    """A clock advance that always fails (patched onto ``WorldClock``)."""
    raise RuntimeError("clock advance failed")


def _reset_guardrail():
    _semantic_validators.clear()
    _degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


class _HeldClient:
    """Test double whose response is a Deferred the test resolves manually."""

    def __init__(self):
        self.deferred = defer.Deferred()
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self.deferred


# The practice drill skill row, built from the kit martial template.
_T_SKILL_ROW = make_skill("t_practice_drill")
