"""Shared service fixtures and fakes for the ``test_option_proposal_service``
slices.

Module-level fixtures, helpers, and the shared base moved verbatim from the
original flat module (not a collected test module).
"""
from unittest.mock import patch


import unittest


from django.test import override_settings


from evennia.server.serversession import ServerSession


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTest


from twisted.internet.defer import Deferred


from tools.spec_traceability import covers_requirement


from typeclasses.characters import PlayerCharacter


from typeclasses.monsters import Monster


from typeclasses.npcs import NPC


from typeclasses.rooms import Room


from typeclasses.components import ScriptedDialogue


from world.ai import guardrail


from world.ai.action_options import (
    MAX_OPTIONSET_CACHE_ENTRIES as LAYER_CACHE_ENTRIES,
    NEGATIVE_MEMO_TTL as LAYER_NEGATIVE_MEMO_TTL,
    OptionSet,
)


from world.ai.fake_client import FakeLLMClient


from world.ai.profiles import default_profiles


from world.quests.catalog import register_catalog


from world.rules.clock import get_world_clock


from server import option_proposal_service as service


from web.webclient.presentation import watchers


from web.webclient.presentation.affordances import (
    exploration_affordances,
    suggestible_candidates,
)


from web.webclient.presentation.coordinator import attach_coordinator


from web.webclient.presentation.ingress import reset_client_sequence


from web.webclient.presentation.registry import build_production_registry


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _install_action_options():
    from world.ai import action_options

    guardrail._semantic_validators.pop("action_options", None)
    guardrail._degrade_fallbacks.pop("action_options", None)
    action_options.register_action_options()


def _uninstall_action_options():
    guardrail._semantic_validators.pop("action_options", None)
    guardrail._degrade_fallbacks.pop("action_options", None)


def await_result(d):
    if d is None:
        return None
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _valid_options_json(candidates):
    """The payload a compliant model would emit for the eligible affordances."""
    import json

    suffixes = "甲乙丙丁戊"
    cards = []
    for index, entry in enumerate(candidates[:5]):
        cards.append(
            {
                "action_code": entry.action_id,
                "label": "提示%s" % suffixes[index],
                "params": dict(entry.params),
            }
        )
    return json.dumps(
        {"context_kind": "exploration", "cards": cards}, ensure_ascii=False
    )


class _PendingFakeClient:
    """A client whose get_response hangs until the test fires the Deferred."""

    def __init__(self):
        self.calls = 0
        self.pending = Deferred()

    def get_response(self, descriptor):
        self.calls += 1
        self.pending = Deferred()
        return self.pending


def _make_session(sessionhandler, sessid, puppet):
    session = ServerSession()
    session.init_session("webclient/websocket", ("localhost", 9999), sessionhandler)
    session.sessid = sessid
    session.protocol_key = "webclient/websocket"
    session.puppet = puppet
    session.logged_in = True
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = str(getattr(puppet, "pk", ""))
    session.ndb.options_state = None
    puppet.sessions.add(session)
    sessionhandler[session.sessid] = session
    return session


def _live_registry(dotted_module: str, attribute: str):
    """Runtime attribute-string registry probe (compile-helper idiom)."""
    import importlib

    return getattr(importlib.import_module(dotted_module), attribute)


class _BaseServiceTests(EvenniaTest):
    """Shared fixtures: one grid room, one player, one NPC, one monster."""

    def setUp(self):
        super().setUp()
        _install_action_options()
        service._reset_service_state()
        watchers.clear_watchers()
        # The affinity rulebook validates against the quest registry; the
        # shipped catalog must be registered before any tier label resolves.
        register_catalog()
        get_world_clock()
        self.room = create_object(Room, key="選項廣場", location=None)
        self.room.db.desc = "一座安靜的廣場。"
        self.player = create_object(PlayerCharacter, key="選項玩家")
        self.player.race = next(
            iter(_live_registry("world.lore" + ".races", "RACE" + "_REGISTRY"))
        )
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="店員", location=self.room)
        self.npc.components.add(
            ScriptedDialogue.create(
                self.npc,
                # First registered dialogue row: the option-layer only needs
                # a hosted dialogue, not a particular shipped one.
                dialogue_key=next(
                    iter(
                        _live_registry(
                            "world.rules" + ".dialogue", "DIALOGUE" + "_TABLE"
                        )
                    )
                ),
            )
        )
        self.monster = create_object(Monster, key="哥布林", location=self.room)
        self._session = None

    def tearDown(self):
        _uninstall_action_options()
        service._reset_service_state()
        watchers.clear_watchers()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def _puppet_session(self, sessid=31):
        session = _make_session(self.sessionhandler, sessid, self.player)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        self._session = session
        return session

    def _watchers(self):
        return watchers.watchers_for(self.player)

    def _envelopes(self, message_name):
        calls = self.sessionhandler.data_out.call_args_list
        return [
            call.kwargs[message_name][0][0]
            for call in calls
            if message_name in call.kwargs
        ]

    def _state(self):
        return self._session.ndb.options_state

    def _schedule(self, client=None):
        return service.schedule_action_options(
            self.player, watchers=self._watchers(), client=client
        )

    def _eligible(self):
        vocab = exploration_affordances(self.player)
        return list(suggestible_candidates(vocab, actor=self.player))


