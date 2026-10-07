"""NPC-owned, append-only operator memory interventions."""

from django.db import transaction
from server.console.errors import ConsoleError
from server.console.validation import integer, resolve_target
from world.narrative import memory
from world.narrative.models import MemoryRecord


def _record(owner, identity):
    integer(identity, minimum=1)
    record = MemoryRecord.objects.filter(pk=identity).first()
    if record is None:
        raise ConsoleError("target_not_found")
    if record.owner_id != str(owner.pk):
        raise ConsoleError("target_kind_mismatch")
    return record


def retract_memory(target, memory_id):
    owner = resolve_target(target, {"npcs"})
    record = _record(owner, memory_id)
    with transaction.atomic():
        memory.revise_memory(record=record, availability="inactive")
    return {"target": target, "memory_id": memory_id}


def supersede_memory(target, memory_id, replacement_id):
    owner = resolve_target(target, {"npcs"})
    old = _record(owner, memory_id)
    new = _record(owner, replacement_id)
    if old.pk == new.pk:
        raise ConsoleError("invalid_argument")
    with transaction.atomic():
        memory.supersede_memory(old_record=old, new_record=new)
    return {"target": target, "memory_id": memory_id, "replacement_id": replacement_id}
