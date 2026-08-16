"""Shared module-level helpers for the npc-dialogue test modules.

The helpers centralize the ``_raw`` profile builder, the guardrail/registry
reset primitives, the ``await_result`` deferred unwrapper, the NPC/player
context and memory builders, the reply-payload builder, and the held-dialogue
client double used by the interleaving tests. They are kept here, not in
``world/ai/tests/_director_helpers.py``: the dialogue and director families
belong to different domains and stay separate.
"""

import json

from twisted.internet import defer

from world.ai import guardrail
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS


def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _semantic_reset():
    guardrail._semantic_validators.clear()


def _fallback_reset():
    guardrail._degrade_fallbacks.clear()


def _schema_reset():
    _OUTPUT_SCHEMAS.clear()


def _reset_all():
    _semantic_reset()
    _fallback_reset()
    _schema_reset()


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _npc_context():
    return {"name": "艾洛希雅", "desc": "南門的守衛", "location": "王都阿爾托利亞"}


def _player_context(disguised=None):
    return {
        "name": "薇歐蕾",
        "disguised_stats": disguised
        if disguised is not None
        else {"atk_phys": 5, "agility": 6, "defense": 6},
    }


def _memory(n=3):
    return [f"第{i}則對話" for i in range(1, n + 1)]


def _reply_text(speech="艾洛希雅對你點頭。", intent=None):
    return json.dumps(
        {"speech": speech, "intent": intent if intent is not None else {"kind": "none"}},
        ensure_ascii=False,
    )


class _HeldDialogueClient:
    """Dialogue test double whose response is a Deferred the test resolves."""

    def __init__(self):
        self.deferred = defer.Deferred()
        self.calls = []

    def get_response(self, descriptor):
        self.calls.append(descriptor)
        return self.deferred
