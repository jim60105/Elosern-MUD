"""Closed owner dispatch; neither names nor imports come from the client."""

from importlib import import_module

from server.console.errors import ConsoleError

# Exact transport fields are deliberately independent of Python reflection.
VERBS = {
    "give_item": ("world.rules.gm", ("target", "key", "quantity")),
    "take_item": ("world.rules.gm", ("target", "key", "quantity")),
    "set_wallet": ("world.rules.gm", ("target", "copper")),
    "set_trait_base": ("world.rules.gm", ("target", "trait", "value")),
    "set_gauge": ("world.rules.gm", ("target", "gauge", "value")),
    "advance_clock": ("world.rules.gm", ("seconds",)),
    "teleport": ("world.maps.gm", ("target", "room")),
    "spawn_monster": ("world.maps.gm", ("species", "variant", "room")),
    "delete_entity": ("world.maps.gm", ("target",)),
    "set_quest_state": ("world.quests.gm", ("target", "quest_id", "state")),
    "set_quest_stage": ("world.quests.gm", ("target", "quest_id", "stage")),
    "issue_quest": ("world.quests.gm", ("target", "definition_key", "issuer_key")),
    "retract_memory": ("world.narrative.gm", ("target", "memory_id")),
    "supersede_memory": ("world.narrative.gm", ("target", "memory_id", "replacement_id")),
}


def validate_arguments(verb: str, arguments: dict):
    if verb not in VERBS:
        raise ConsoleError("unknown_verb")
    if not isinstance(arguments, dict) or set(arguments) != set(VERBS[verb][1]):
        raise ConsoleError("invalid_argument")


def dispatch(verb: str, arguments: dict):
    validate_arguments(verb, arguments)
    module, _ = VERBS[verb]
    return getattr(import_module(module), verb)(**arguments)


def argument_summary(arguments: dict) -> str:
    """Describe shape, never raw strings, credentials or Attribute contents."""
    return ", ".join(
        f"{key}={value}" if type(value) is int else f"{key}: {type(value).__name__}"
        for key, value in arguments.items()
    )[:200]
