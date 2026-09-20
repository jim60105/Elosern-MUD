"""Shared module-level helpers for the ``exploration`` test package."""

import unittest
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.exploration import EXPLORATION_SCHEMA_VERSION


# Kit-authored scripted-dialogue row: the host's keywords come from here.
T_DIALOGUE_KEY = "t_synth_lodgekeeper"


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _keyword(**overrides):
    value = {"keyword_id": "公會", "label": "公會"}
    value.update(overrides)
    return value


def _affordance(**overrides):
    value = {
        "kind": "action",
        "action_id": "explore.talk_scripted",
        "label": "交談",
        "enabled": True,
        "disabled_reason": None,
    }
    value.update(overrides)
    return value


def _move_row(**overrides):
    value = {
        "exit_ref": "42",
        "label": "東",
        "destination": "room:7",
        "enabled": True,
        "disabled_reason": None,
    }
    value.update(overrides)
    return value


def _entity(**overrides):
    value = {
        "identity": 5,
        "display_name": "南門守衛",
        "kind": "npc",
        "portrait_ref": None,
    }
    value.update(overrides)
    return value


def _object(**overrides):
    value = {"identity": 6, "display_name": "木箱"}
    value.update(overrides)
    return value


def _target(**overrides):
    value = {
        "identity": 5,
        "display_name": "南門守衛",
        "portrait_ref": None,
        "affordances": [_affordance()],
        "keywords": [_keyword()],
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": EXPLORATION_SCHEMA_VERSION,
        "available": True,
        "kind": "exploration",
        "move": [_move_row()],
        "look": {
            "room": {"identity": 3, "display_name": "南門", "room": True},
            "entities": [_entity()],
            "objects": [_object()],
        },
        "interact": [_target()],
        "character": {"available": True},
        "quests": {"available": True},
        "inventory": {"available": True},
    }
    value.update(overrides)
    return value
