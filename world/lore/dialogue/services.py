"""Explicit dialogue-service associations: the mechanical row parser and policy.

A dialogue source advertises a service only through an explicit association row
(``{key, topic_id, label}``); prose, names, roles and titles never imply one.
This module owns the one mechanical parser every source shares and the closed
set of native deterministic entries an authored static source may advertise.

The native set is deliberately tiny and exact. The guild counter's ``回報``
topic is the single deterministic action keyword the runtime already executes
outside the scene engine (``commands/talk.py`` routes it to the guild report
service on a ``GuildStaff`` host), so it is the only static topic a source may
name, and advertising it also requires that host capability. Everything else
must be an authorized generated ``offer_commission`` effect topic, decided by
the package validator that owns those effects.

This is a pure data leaf: it imports only the dialogue shape, so the lore
package stays importable without an Evennia/Django environment.
"""

from __future__ import annotations

from typing import Any, Iterable

from world.lore.dialogue.shape import (
    MAX_SERVICE_ASSOCIATIONS,
    MAX_SERVICE_KEY_CHARS,
    MAX_SERVICE_LABEL_CODE_POINTS,
    MAX_SERVICE_TOPIC_ID_CHARS,
    AuthoredDialogue,
    DialogueService,
)

#: The guild counter's authored dialogue key and the deterministic report
#: keyword its host answers. ``world.rules.dialogue`` re-exports both names.
GUILD_STAFF_DIALOGUE_KEY = "guild_staff"
GUILD_STAFF_TURNIN_KEYWORD = "回報"

#: The closed native deterministic associations an authored static source may
#: advertise: ``(dialogue_key, full topic id, keyword)``. Pinning all three
#: keeps a same-keyword topic elsewhere from becoming a service by accident.
NATIVE_SERVICE_ASSOCIATIONS: frozenset[tuple[str, str, str]] = frozenset(
    {
        (
            GUILD_STAFF_DIALOGUE_KEY,
            f"{GUILD_STAFF_DIALOGUE_KEY}.topic_04",
            GUILD_STAFF_TURNIN_KEYWORD,
        )
    }
)

#: The host capability each native association's existing deterministic entry
#: requires. A source may advertise the association only on a host that also
#: carries it, because that is what executes the entry.
NATIVE_ASSOCIATION_CAPABILITIES: dict[tuple[str, str], str] = {
    (dialogue_key, topic_id): "guild_staff"
    for dialogue_key, topic_id, _keyword in NATIVE_SERVICE_ASSOCIATIONS
}

#: The one generated effect verb whose topic an association may advertise.
OFFER_COMMISSION_VERB = "offer_commission"

SERVICE_FIELDS = frozenset({"key", "topic_id", "label"})


class DialogueServiceError(ValueError):
    """One or more dialogue service associations are unusable."""


def parse_service_rows(payload: Any) -> tuple[DialogueService, ...]:
    """Parse one source's raw ``services`` array into frozen associations.

    Mechanical only: exact fields, bounded values, no duplicate key or topic,
    and at most :data:`MAX_SERVICE_ASSOCIATIONS` rows. Whether the referenced
    topic is a supported deterministic entry of this same source/phase is the
    caller's policy decision, made after the topics exist. ``None`` (an absent
    field) is the empty default.
    """
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise DialogueServiceError("services must be an array")
    if len(payload) > MAX_SERVICE_ASSOCIATIONS:
        raise DialogueServiceError(
            f"services cannot exceed {MAX_SERVICE_ASSOCIATIONS} rows, got {len(payload)}"
        )
    parsed: list[DialogueService] = []
    seen_keys: set[str] = set()
    seen_topics: set[str] = set()
    for position, row in enumerate(payload):
        where = f"services[{position}]"
        if not isinstance(row, dict):
            raise DialogueServiceError(f"{where} must be an object")
        unknown = set(row) - SERVICE_FIELDS
        missing = SERVICE_FIELDS - set(row)
        if unknown or missing:
            raise DialogueServiceError(
                f"{where} must declare exactly key, topic_id and label "
                f"(unknown {sorted(unknown)}, missing {sorted(missing)})"
            )
        key = row["key"]
        topic_id = row["topic_id"]
        label = row["label"]
        if not isinstance(key, str) or not key:
            raise DialogueServiceError(f"{where}.key must be a non-empty string")
        if len(key) > MAX_SERVICE_KEY_CHARS:
            raise DialogueServiceError(
                f"{where}.key exceeds {MAX_SERVICE_KEY_CHARS} characters"
            )
        if not isinstance(topic_id, str) or not topic_id:
            raise DialogueServiceError(f"{where}.topic_id must be a non-empty string")
        if len(topic_id) > MAX_SERVICE_TOPIC_ID_CHARS:
            raise DialogueServiceError(
                f"{where}.topic_id exceeds {MAX_SERVICE_TOPIC_ID_CHARS} characters"
            )
        if not isinstance(label, str) or not (
            1 <= len(label) <= MAX_SERVICE_LABEL_CODE_POINTS
        ):
            raise DialogueServiceError(
                f"{where}.label must be a string of 1..{MAX_SERVICE_LABEL_CODE_POINTS} code points"
            )
        try:
            service = DialogueService(key=key, topic_id=topic_id, label=label)
        except (TypeError, ValueError) as error:
            raise DialogueServiceError(f"{where}: {error}") from error
        if service.key in seen_keys:
            raise DialogueServiceError(f"{where} repeats service key {key!r}")
        if service.topic_id in seen_topics:
            raise DialogueServiceError(f"{where} repeats service topic {topic_id!r}")
        seen_keys.add(service.key)
        seen_topics.add(service.topic_id)
        parsed.append(service)
    return tuple(parsed)


def native_supported_topic_ids(
    dialogue_key: str, dialogue: AuthoredDialogue
) -> frozenset[str]:
    """The full topic ids of one static source's native supported entries."""
    return frozenset(
        topic.topic_id
        for topic in dialogue.topics
        if (dialogue_key, topic.topic_id, topic.keyword) in NATIVE_SERVICE_ASSOCIATIONS
    )


def supported_service_topic_ids(
    dialogue_key: str,
    dialogue: AuthoredDialogue,
    *,
    effect_topic_ids: Iterable[str] = (),
) -> frozenset[str]:
    """Every topic id of ``dialogue`` that may be advertised as a service.

    Static sources answer from the closed native set; generated phases answer
    with the topics the package bound an ``offer_commission`` effect to. A
    narrative-only source therefore supports nothing.
    """
    return native_supported_topic_ids(dialogue_key, dialogue) | frozenset(
        effect_topic_ids
    )


def validate_service_associations(
    dialogue: AuthoredDialogue,
    *,
    dialogue_key: str,
    supported_topic_ids: Iterable[str],
) -> None:
    """Reject any association that is not a supported deterministic entry.

    Duplicate, dangling and cross-phase references are already structural (the
    carrier rejects them); this adds the policy leg: the referenced topic must
    be one of this source's own supported entries. Rejection is atomic — the
    caller discards the complete source or package.
    """
    supported = frozenset(supported_topic_ids)
    for service in dialogue.services:
        if service.topic_id not in supported:
            raise DialogueServiceError(
                f"service {service.key!r} names topic {service.topic_id!r}, which is "
                f"not a supported deterministic entry of source {dialogue_key!r}"
            )


def required_capability_types(dialogue_key: str) -> frozenset[str]:
    """The host capabilities a source's native associations require."""
    return frozenset(
        capability
        for (key, _topic_id), capability in NATIVE_ASSOCIATION_CAPABILITIES.items()
        if key == dialogue_key
    )


__all__ = [
    "DialogueServiceError",
    "GUILD_STAFF_DIALOGUE_KEY",
    "GUILD_STAFF_TURNIN_KEYWORD",
    "MAX_SERVICE_ASSOCIATIONS",
    "NATIVE_ASSOCIATION_CAPABILITIES",
    "NATIVE_SERVICE_ASSOCIATIONS",
    "OFFER_COMMISSION_VERB",
    "native_supported_topic_ids",
    "parse_service_rows",
    "required_capability_types",
    "supported_service_topic_ids",
    "validate_service_associations",
]
