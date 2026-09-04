"""Shared module-level helpers for the scenario-director test modules.

The helpers centralize the ``_raw`` profile builder, the guardrail/registry
reset primitives, the ``await_result`` deferred unwrapper, and the blueprint
builders used across the split ``test_scenario_director_*`` modules. They are
kept here, not in ``world/ai/tests/_dialogue_helpers.py``: the director and
dialogue families belong to different domains and stay separate.
"""

from world.ai import guardrail
from world.ai.profiles import default_profiles
from world.ai.scenario_director import (
    BlueprintFailure,
    BlueprintItemQuantity,
    BlueprintLocation,
    BlueprintObjective,
    BlueprintReward,
    BlueprintStage,
    QuestBlueprint,
)
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


def _item(item_key="healing_potion", quantity=1):
    return BlueprintItemQuantity(item_key, quantity)


def _location(layer="anchor", archetype="forest_path", anchor_key="capital_altoria"):
    return BlueprintLocation(
        layer=layer,
        archetype=archetype,
        anchor_key=anchor_key,
        scene_sentence="王都近郊的林間小徑，樹影搖曳。",
    )


def _stage(index=0, kind="defeat", monster_tier="low", location=None):
    return BlueprintStage(
        index=index,
        objective=BlueprintObjective(kind=kind, monster_tier=monster_tier),
        location=location if location is not None else _location(),
    )


def _blueprint(
    name="討伐低階魔物",
    quest_type="討伐",
    rank="F",
    issuer="guild_branch_altoria",
    stages=None,
    copper=50,
    merit=25,
    deadline_hours=None,
):
    if stages is None:
        stages = (_stage(),)
    return QuestBlueprint(
        name=name,
        quest_type=quest_type,
        rank=rank,
        issuer=issuer,
        stages=stages,
        reward=BlueprintReward(copper=copper, items=(_item(),), merit=merit),
        failure=BlueprintFailure(deadline_hours=deadline_hours, conditions=()),
    )


def _payload(blueprint=None):
    return (blueprint or _blueprint()).to_payload()


def _context(**overrides):
    context = {
        "requested_type": "討伐",
        "allowed_rank": "F",
        "issuer_branch": "guild_branch_altoria",
        "anchor": "capital_altoria",
    }
    context.update(overrides)
    return context


def _instance_payload():
    """A valid instance-bound payload (registers scene requirements)."""
    payload = _payload()
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
            "title": "林間盜匪首領",
        }
    ]
    return payload
