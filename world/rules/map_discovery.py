"""Traversal-only district discovery, derived from unchanged visited knowledge."""
from django.db import transaction

from world.observability import log_info, log_warn
from world.rules.map_knowledge import KNOWLEDGE_ATTR, KnowledgeError, _derive_node_id, parse_knowledge


def persisted_visits(actor):
    """Parse persisted knowledge and reconcile Evennia's Attribute cache.

    Attribute.value sets the cached db_value before save(). A swallowed save
    failure can therefore leave a visit in memory that never reached storage.
    A values query bypasses the framework's identity-mapped model instances.
    Assigning db_value here repairs only that in-memory object, without save().
    """
    attribute = actor.attributes.get(KNOWLEDGE_ATTR, return_obj=True)
    if attribute is None:
        return ()
    try:
        stored = type(attribute).objects.filter(pk=attribute.pk).values_list("db_value", flat=True)
        attribute.db_value = stored.get()
    except Exception as error:
        log_warn("map_discovery_knowledge_refresh_failed", exc=error,
                 context={"char": actor.pk, "key": KNOWLEDGE_ATTR})
        raise KnowledgeError("persisted map knowledge is unavailable") from error
    return parse_knowledge(actor)


def traversal_node_id(actor, location):
    """A broken location cannot make an exception-isolated arrival fail."""
    try:
        return _derive_node_id(location)
    except Exception as error:
        log_warn("map_discovery_location_unreadable", exc=error,
                 context={"char": actor.pk, "room": getattr(location, "pk", None)})
        return None


def visited_before_traversal(actor):
    """None means unreadable; an empty set is a legitimate fresh explorer."""
    from typeclasses.characters import PlayerCharacter
    if not isinstance(actor, PlayerCharacter):
        return None
    try:
        return {visit.node_id for visit in persisted_visits(actor)}
    except KnowledgeError as error:
        log_warn("map_discovery_knowledge_unreadable", exc=error, context={"char": actor.pk})
        return None


def publish_traversal_narrative(actor, before):
    """Schedule one immutable message after the final settlement outcome.

    The caller is an explicit exit traversal, never a direct move/teleport.
    Re-read after record_arrival: its exception isolation must not create a
    discovery when persistence failed. Outer transaction rollbacks discard the
    callback. Message delivery cannot compensate an already committed move.
    """
    from typeclasses.characters import PlayerCharacter
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY

    if not isinstance(actor, PlayerCharacter) and not getattr(actor.db, "possessed_by", None):
        return
    destination=traversal_node_id(actor, actor.location)
    discovery=None
    after = set()
    if isinstance(actor, PlayerCharacter):
        try:
            after={visit.node_id for visit in persisted_visits(actor)}
        except KnowledgeError as error:
            log_warn("map_discovery_knowledge_unreadable", exc=error, context={"char": actor.pk})
    if before is not None and destination not in before and destination in after:
        discovery=next((district for district in MAP_DISTRICT_REGISTRY.values()
                        if district.landmark_node == destination),None)
    message=f"你移動到了{actor.location.key}。"
    if discovery is not None:
        message += f"\n已探明：{discovery.district_name_zh}"
    def deliver():
        try:
            actor.msg(message)
            if discovery is not None:
                log_info("map_district_discovered", context={"char": actor.pk, "district": discovery.key})
        except Exception as error:
            log_warn("map_discovery_delivery_failed", exc=error, context={"char": actor.pk})
    transaction.on_commit(deliver)
