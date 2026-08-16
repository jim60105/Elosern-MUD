"""Shared payload builders, registry isolation, and await_result for compile tests.

Moved here from ``test_compile.py`` (single fixed home) so the themed compile
test modules can import ``CompileRegistryIsolation`` and the payload helpers
after the original file is deleted.
"""

from world.ai.profiles import default_profiles
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_offers import GUILD_OFFER_REGISTRY

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
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {"kind": "defeat", "quantity": 1, "monster_tier": "low"},
                "location_req": {
                    "layer": "anchor",
                    "archetype": "forest_path",
                    "anchor_key": "capital_altoria",
                    "anchor_near": None,
                    "xyz": None,
                    "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
                },
                "npc_req": [],
            }
        ],
        "reward": {"copper": 50, "items": [{"item_key": "healing_potion", "quantity": 1}], "merit": 25},
        "failure": {"deadline_hours": None, "conditions": []},
    }
    payload.update(overrides)
    return payload


def _acquire_payload(**overrides):
    payload = {
        "name": "採集治療藥水",
        "quest_type": "採集",
        "rank": "F",
        "issuer": "guild_branch_altoria",
        "stages": [
            {
                "index": 0,
                "objective": {
                    "kind": "acquire",
                    "quantity": 1,
                    "item_key": "healing_potion",
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
        "archetype": "forest_path",
        "anchor_key": None,
        "anchor_near": "capital_altoria",
        "xyz": None,
        "scene_sentence": "王都近郊的林間小徑，樹影搖曳。",
    }
    payload["stages"][0]["npc_req"] = [
        {
            "role": "bandit",
            "tier": "bandit",
            "disposition": None,
            "display_name": "黑鬍",
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
