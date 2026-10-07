"""Frozen-record console repairs through quest lifecycle settlement."""

from dataclasses import replace
from django.db import transaction

from server.console.errors import ConsoleError
from server.console.validation import integer, resolve_target, text
from world.quests import runtime, transitions
from world.rules.surfaces import snapshot_attributes, restore_attributes
from world.rules.clock import _flush_rolled_back_instances


def _resolve_definition(key, issuer=None):
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY
    from world.quests.generated_quest_store import read_payloads
    from world.quests.compile.payload import payload_to_registrations
    from world.quests.compile.registration import register_restored_quest

    definition = QUEST_DEFINITION_REGISTRY.get(key)
    for payload in read_payloads():
        if payload["definition"]["key"] == key and (issuer is None or payload["issuance"]["issuer_key"] == issuer):
            compiled = payload_to_registrations(payload)
            register_restored_quest(compiled)
            definition = compiled.definition
            break
    if definition is None:
        raise ConsoleError("registry_key_not_found")
    return definition


def _repair(target, quest_id, *, state=None, stage=None):
    actor = resolve_target(target, {"characters"})
    text(quest_id)
    # Read the frozen log only after resolving any durable generated aggregate.
    entries = list(actor.db.quest_log or [])
    entry = next((entry for entry in entries if entry.get("quest_id") == quest_id), None)
    if entry is None:
        raise ConsoleError("target_not_found")
    definition = _resolve_definition(entry["definition_key"], entry["issuer_key"])
    records = runtime.read_records(actor)
    record = runtime.find_record(records, quest_id)
    if state is not None:
        if not isinstance(state, str) or state not in {item.value for item in runtime.QuestState}:
            raise ConsoleError("invalid_argument")
        desired = runtime.QuestState(state)
        index = record.stage_index
    else:
        integer(stage, maximum=len(definition.stages) - 1)
        desired = runtime.QuestState.IN_PROGRESS
        index = stage
    replacement = replace(
        record, state=desired, stage_index=index,
        stage_progress=definition.stages[index].objective.quantity if desired is runtime.QuestState.COMPLETED else 0,
        stage_room_id=None, objective_target_ids=(), protected_entity_ids=(),
        counted_defeat_ids=(), failure_reason="gm_repair" if desired is runtime.QuestState.FAILED else None,
    )
    runtime.validate_record_runtime(replacement)
    pins = transitions.release_stage_binding(actor, record)
    attrs = snapshot_attributes(actor, ("quest_log", "wallet", "inventory", "guild_reward_claims"))
    from world.quests.settlement import plan_auto_settlement_chain
    revised = [replacement if item.quest_id == quest_id else item for item in records]
    settlement = plan_auto_settlement_chain(actor, entries, revised)
    rooms = [(room, transitions.snapshot_pin_reasons(room)) for room in dict.fromkeys(room for room, _, _ in (*pins, *settlement.chain_pins))]
    try:
        with transaction.atomic():
            transitions.apply_quest_log_replacement(actor, revised, pins)
            if desired is runtime.QuestState.IN_PROGRESS:
                from world.quests.compile.compiler import scene_requirements_for
                from world.quests.scene_builder import materialize_stage

                if any(requirement.index == index for requirement in scene_requirements_for(record.definition_key)):
                    materialize_stage(actor, quest_id, origin_room=actor.location)
    except Exception:
        restore_attributes(actor, attrs)
        for room, before in rooms:
            transitions.restore_pin_reasons(room, before)
        _flush_rolled_back_instances()
        if actor.location is not None:
            actor.location.contents_cache.init()
        raise
    return {"target": target, "quest_id": quest_id}


def set_quest_state(target, quest_id, state):
    return _repair(target, quest_id, state=state)


def set_quest_stage(target, quest_id, stage):
    return _repair(target, quest_id, stage=stage)


def issue_quest(target, definition_key, issuer_key):
    actor = resolve_target(target, {"characters"})
    text(definition_key)
    text(issuer_key)
    _resolve_definition(definition_key, issuer_key)
    try:
        record = runtime.accept_quest(actor, definition_key, issuer_key)
    except (ValueError, KeyError) as error:
        raise ConsoleError("invalid_argument") from error
    return {"target": target, "quest_id": record.quest_id}
