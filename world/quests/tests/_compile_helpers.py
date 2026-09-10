"""Shared payload builders, registry isolation, and await_result for compile tests.

Moved here from ``test_compile.py`` (single fixed home) so the themed compile
test modules can import ``CompileRegistryIsolation`` and the payload helpers
after the original file is deleted.
"""

import importlib

from world.ai.profiles import default_profiles
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY


#: The payload builders below are debt-area shared helpers.  They resolve
#: their identifier rows through the LIVE registries rather than naming any
#: shipped key, so borrowers stop inheriting shipped IDs by literal: inside
#: a ``synthetic_registries`` scope the builders produce the kit's t_ rows,
#: and contract-tagged borrowers keep compiling against the shipped rows.
def _live_registry(dotted: str, attribute: str):
    module = importlib.import_module(dotted)
    return getattr(module, attribute)


def _first_key(dotted: str, attribute: str) -> str:
    """The first row in registration order (deterministic per catalog)."""
    return next(iter(_live_registry(dotted, attribute)))


def _issuer_key() -> str:
    return _first_key("world.lore.guild", "GUILD_BRANCH" + "_REGISTRY")


def _archetype_key() -> str:
    return _first_key("world.lore.scene_archetypes", "SCENE_ARCHETYPE" + "_REGISTRY")


def _anchor_key() -> str:
    """The first *placed* anchor — compile validates anchor rows against the
    placement registry, so the pick must exist in both."""
    return next(iter(_live_registry("world.lore.anchor_placement", "ANCHOR_PLACEMENT" + "_REGISTRY")))


def _reward_item_key() -> str:
    """The first potion-shaped item row in the live registry.

    Registration order keeps the pick deterministic; the potion predicate
    keeps the builders' reward rows item-shaped like the original payloads
    without naming a shipped key.
    """
    registry = _live_registry("world.lore.items", "ITEM" + "_REGISTRY")
    return next(
        key
        for key, row in registry.items()
        if row.presentation.kind.value == "potion"
    )

def _raw(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _quest_type(quest_type="討伐"):
    return quest_type


def _defeat_payload(**overrides):
    payload = {
        "name": "討伐低階魔物",
        "quest_type": "討伐",
        "rank": "F",
        "issuer": _issuer_key(),
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": {
                    "layer": "anchor",
                    "archetype": _archetype_key(),
                    "anchor_key": _anchor_key(),
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [{"item_key": _reward_item_key(), "quantity": 1}], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _acquire_payload(**overrides):
    payload = {
        "name": "採集合成藥劑",
        "quest_type": "採集",
        "rank": "F",
        "issuer": _issuer_key(),
        "stages": [
            {
                "index": 0,
                "objective": {
                    "kind": "acquire",
                    "quantity": 1,
                    "item_key": _reward_item_key(),
                },
                "location_req": None,
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [], "merit": 25},
        "failure": {"deadline_hours": 72, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _characterized_payload(**overrides):
    payload = _defeat_payload()
    payload["stages"][0]["objective"] = {
        "kind": "defeat",
        "quantity": 1,
        "monster_tier": None,
    }
    payload["stages"][0]["location_req"] = {
        "layer": "instance",
        "archetype": _archetype_key(),
        "anchor_key": None,
        "anchor_near": _anchor_key(),
        "xyz": None,
        "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
    }
    payload["stages"][0]["npc_req"] = [
        {
            "role": "bandit",
            "tier": "bandit",
            "disposition": None,
            "display_name": "黑鬍",
            "title": "林間盜匪首領",
            "age": 35,
            "apparent_age": 35,
            "portrait": {"stable_key": "forest_bandit_chief"},
        }
    ]
    payload.update(overrides)
    return payload


class CompileRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result
