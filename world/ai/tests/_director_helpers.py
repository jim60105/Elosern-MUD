"""Shared module-level helpers for the scenario-director test modules.

The helpers centralize the ``_raw`` profile builder, the guardrail/registry
reset primitives, the ``await_result`` deferred unwrapper, and the blueprint
builders used across the split ``test_scenario_director_*`` modules. They are
kept here, not in ``world/ai/tests/_dialogue_helpers.py``: the director and
dialogue families belong to different domains and stay separate.

Every identifier row the builders name resolves through the LIVE registries
via runtime attribute strings (the ``world/quests/tests/_compile_helpers.py``
idiom), so borrowers never inherit a shipped identifier literal: inside a
``synthetic_registries`` scope the builders emit the kit's ``t_`` rows, and
outside one they emit the live shipped rows, and either way the lint gate
stays clean because this source never names a shipped key. Context builders
come in two flavours on purpose: ``_context()`` pairs with the payload
builders (both share the same probes, so the generated blueprint fits the
request), while ``_template_context()`` reads issuer/anchor/type off the
hand-written template pool itself, so every degrade-path assertion keeps
proving the shipped-pool fitness gate regardless of catalog contents.
"""

import importlib

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


def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


def _first_key(dotted: str, attribute: str) -> str:
    """The first row in registration order (deterministic per catalog)."""
    return next(iter(_live_registry(dotted, attribute)))


def _issuer_key() -> str:
    return _first_key("world.lore.guild", "GUILD_BRANCH" + "_REGISTRY")


def _rank_key() -> str:
    return _first_key("world.lore.guild", "GUILD_RANK" + "_REGISTRY")


def _rank_rows():
    """The live rank rows, for order/band-driven assertions."""
    return _live_registry("world.lore.guild", "GUILD_RANK" + "_REGISTRY")


def _anchor_key() -> str:
    """The first *placed* anchor — the validators check anchor rows against
    the placement registry, so the pick must exist there."""
    return _first_key(
        "world.lore.anchor_placement", "ANCHOR_PLACEMENT" + "_REGISTRY"
    )


def _archetype_key() -> str:
    return _first_key(
        "world.lore.scene_archetypes", "SCENE_ARCHETYPE" + "_REGISTRY"
    )


def _npc_tier_key() -> str:
    return _first_key("world.lore.npc_tiers", "NPC_TIER" + "_REGISTRY")


def _first_race_key() -> str:
    return _first_key("world.lore.races", "RACE" + "_REGISTRY")


def _monster_tier_key() -> str:
    return _first_key("world.lore.monsters", "MONSTER_TIER" + "_REGISTRY")


def _reward_item_key() -> str:
    return _first_key("world.lore.items", "ITEM" + "_REGISTRY")


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


def _item(item_key=None, quantity=1):
    return BlueprintItemQuantity(item_key or _reward_item_key(), quantity)


def _location(layer="anchor", archetype=None, anchor_key=None):
    return BlueprintLocation(
        layer=layer,
        archetype=archetype or _archetype_key(),
        anchor_key=anchor_key or _anchor_key(),
        scene_sentence="湖畔集鎮外圍的石徑，霧氣低垂。",
    )


def _stage(index=0, kind="defeat", monster_tier=None, location=None):
    return BlueprintStage(
        index=index,
        objective=BlueprintObjective(
            kind=kind, monster_tier=monster_tier or _monster_tier_key()
        ),
        location=location if location is not None else _location(),
    )


def _blueprint(
    name="討伐湖邊魔物",
    quest_type="討伐",
    rank=None,
    issuer=None,
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
        rank=rank or _rank_key(),
        issuer=issuer or _issuer_key(),
        stages=stages,
        reward=BlueprintReward(copper=copper, items=(_item(),), merit=merit),
        failure=BlueprintFailure(deadline_hours=deadline_hours, conditions=()),
    )


def _payload(blueprint=None):
    return (blueprint or _blueprint()).to_payload()


def _context(**overrides):
    """A request context matching the payload builders.

    The issuer/anchor/rank probes are the same ones ``_blueprint`` embeds, so
    a builder-produced proposal always passes the post-guardrail fitness gate
    for this context (the two sides are resolved from the same live
    registries, whichever scope they run in).
    """
    context = {
        "requested_type": "討伐",
        "allowed_rank": _rank_key(),
        "issuer_branch": _issuer_key(),
        "anchor": _anchor_key(),
    }
    context.update(overrides)
    return context


def _template_pool_entry(instance_layer=False, npc_reqs=False, portrait=False):
    """One hand-written template selected by structure, never by name.

    The pool is shipped production content; the selection predicates mirror
    the structural properties the tests care about (instance layer, bound
    NPCs, portrait characterization), so no shipped identifier appears here.
    """
    from world.ai.director_templates import QUEST_TEMPLATE_POOL

    for entry in QUEST_TEMPLATE_POOL:
        for stage in entry.stages:
            if instance_layer and not (
                stage.location is not None
                and stage.location.layer == "instance"
                and stage.npc_reqs
            ):
                continue
            if npc_reqs and not stage.npc_reqs:
                continue
            if portrait and not any(
                requirement.portrait is not None for requirement in stage.npc_reqs
            ):
                continue
            return entry
    raise AssertionError("the template pool lost a structural entry")


def _template_context(**overrides):
    """A request context derived FROM the template pool's first entry.

    The degrade paths resolve by exact issuer/anchor/type equality against
    the hand-written pool, so offline assertions must ask for exactly what a
    pool entry provides — read from the pool at runtime, not hardcoded.
    """
    return _context_of_entry(_template_pool_entry(), **overrides)


def _instance_template_context(**overrides):
    """A request context derived FROM the pool's instance-layer entry."""
    return _context_of_entry(_template_pool_entry(instance_layer=True), **overrides)


def _context_of_entry(entry, **overrides):
    anchor = None
    for stage in entry.stages:
        if stage.location is None:
            continue
        anchor = stage.location.anchor_key or stage.location.anchor_near
        if anchor is not None:
            break
    context = {
        "requested_type": entry.quest_type,
        "allowed_rank": entry.rank,
        "issuer_branch": entry.issuer,
        "anchor": anchor,
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
        "archetype": _archetype_key(),
        "anchor_key": None,
        "anchor_near": _anchor_key(),
        "xyz": None,
        "scene_sentence": "湖畔集鎮外圍的石徑，霧氣低垂。",
    }
    payload["stages"][0]["npc_req"] = [
        {
            "role": "intruder",
            "tier": _npc_tier_key(),
            "disposition": None,
            "display_name": "灰篷旅人",
            "title": "夜巡帶頭者",
        }
    ]
    return payload
