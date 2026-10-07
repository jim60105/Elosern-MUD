"""Read-only ownership and predicate attribution for one captured status read."""

from world.rules.equipment_effects import attached_buff_instances, declared_attachment

from .models import ConditionProvenance, EquipmentSource


def provenance(kind, item_keys, labels):
    value = ConditionProvenance(
        kind, tuple(EquipmentSource(key, labels[key]) for key in sorted(item_keys))
    )
    value.validate()
    return value


def buff_provenances(entries, equipment, labels):
    required = attached_buff_instances(equipment)
    result = {}
    for instance, cache in entries:
        declared = declared_attachment(instance)
        ownership = (cache["definition_key"], cache.get("source_key"))
        if instance in required and ownership == required[instance]:
            result[instance] = provenance("equipment", {ownership[1]}, labels)
        elif declared is not None:
            result[instance] = provenance("unknown", (), labels)
        else:
            result[instance] = provenance("non_equipment", (), labels)
    return result


def rule_provenances(matches, independent_ids, predicates, actual, comparison,
                     entries, buffs, equipment, labels, biases):
    """Compare each exact matched rule ID, never aggregate distinct conditions."""
    result = {}
    for rule_id, _ in matches:
        when = predicates.get(rule_id, {})
        sources = set()
        incomplete = False
        if when.get("field") == "exposure" and (
            actual.get("exposure") != comparison.get("exposure")
        ):
            sources.update(biases)
        if "buff_active" in when:
            for instance, cache in entries:
                if cache["definition_key"] == when["buff_active"]:
                    sources.update(source.item_key for source in buffs[instance].equipment_sources)
        item = when.get("equipment_worn")
        if item in actual["worn_item_keys"]:
            sources.add(item)
        if when.get("dual_wielding") is True and actual["dual_wielding"]:
            pair = (equipment["weapon_main"], equipment["weapon_off"])
            if all(item in labels for item in pair):
                sources.update(pair)
            else:
                incomplete = True
        if incomplete:
            kind = "unknown"
            sources.clear()
        elif rule_id in independent_ids:
            kind = "mixed" if sources else "non_equipment"
        else:
            kind = "equipment" if sources else "unknown"
        result[rule_id] = provenance(kind, sources, labels)
    return result
