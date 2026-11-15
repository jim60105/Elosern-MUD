"""Traversal movement narrative and the persisted-visit read it shares with the world map."""
from django.db import transaction

from world.observability import log_warn
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
    """None means unreadable; an empty set is a legitimate fresh explorer.

    The narrative no longer reads the result (a movement announces no
    discovery). The read is kept because it reconciles a dirty in-memory
    knowledge cache through :func:`persisted_visits` before each explicit
    traversal.
    """
    from typeclasses.characters import PlayerCharacter
    if not isinstance(actor, PlayerCharacter):
        return None
    try:
        return {visit.node_id for visit in persisted_visits(actor)}
    except KnowledgeError as error:
        log_warn("map_discovery_knowledge_unreadable", exc=error, context={"char": actor.pk})
        return None


def publish_traversal_narrative(actor, before):
    """Schedule the one immutable movement message after the final settlement.

    The caller is an explicit exit traversal, never a direct move/teleport. A
    movement announces no district discovery: a district lights only when its
    rite completes (map-district-discovery). ``before`` (the pre-traversal
    visited set) is no longer read and is kept for signature stability. Outer
    transaction rollbacks discard the callback. Message delivery cannot
    compensate an already committed move.
    """
    from typeclasses.characters import PlayerCharacter

    if not isinstance(actor, PlayerCharacter) and not getattr(actor.db, "possessed_by", None):
        return
    message=f"你移動到了{actor.location.key}。"
    def deliver():
        try:
            actor.msg(message)
        except Exception as error:
            log_warn("map_discovery_delivery_failed", exc=error, context={"char": actor.pk})
    transaction.on_commit(deliver)
