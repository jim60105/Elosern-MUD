"""Durable mirror of every registered generated quest (design D1).

One ``GeneratedQuestStore`` Evennia Script (key ``generated_quest_store``)
holds a JSON-safe list of serialized payloads, one per issuance identity
``(definition key, issuer key)`` -- two commissioners of one definition
coexist as two entries:
``{"definition": {...}, "issuance": {"issuer_key", "settlement", "reward"},
"requirements": [...]}``. The Script survives server restarts and is the
single write point ``register_generated_quest`` appends to before touching
the process-local registries.

This module deliberately imports nothing from ``world.quests``: the payloads
are raw JSON-safe dicts here, and serialization plus reconstruction live in
``world.quests.compile``, which imports this module. Importing ``compile``
here would create an import cycle.
"""

from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

STORE_KEY = "generated_quest_store"


class StorePayloadConflictError(ValueError):
    """A payload already stored under the key differs from the new payload."""


class GeneratedQuestStore(DefaultScript):
    """Persistent, non-ticking Script holding serialized generated-quest payloads."""


def get_store() -> GeneratedQuestStore:
    """Return the one store Script, creating it only when absent.

    The Evennia server is a single game process, so store access is never
    concurrent; exactly one script must exist. A duplicate is a split-brain
    hazard (reads and writes could land on different rows), so it fails loudly
    instead of silently picking ``matches[0]``.
    """
    matches = search_script(STORE_KEY)
    if len(matches) > 1:
        raise RuntimeError(
            f"{len(matches)} generated-quest store scripts found under "
            f"{STORE_KEY!r}; delete all but one to repair"
        )
    if matches:
        return matches[0]
    return create_script(GeneratedQuestStore, key=STORE_KEY, persistent=True)


def _payload_identity(payload: dict) -> tuple[str, str]:
    """Return the ``(definition key, issuer key)`` identity a payload mirrors.

    One definition can be issued by several carriers (two commissioners of
    identical stages share the definition key and differ by issuance), so the
    durable mirror holds one payload per issuance, not per definition.
    """
    return payload["definition"]["key"], payload["issuance"]["issuer_key"]


def list_payloads() -> list[dict]:
    """Return a copy of every stored payload in registration order."""
    return list(get_store().db.payloads or [])


def append_payload(payload: dict) -> bool:
    """Append one payload unless its issuance identity is already stored.

    Idempotent by ``(definition key, issuer key)`` with content verification:
    a payload whose identity already exists is compared field by field -- an
    equal payload leaves the store untouched and returns ``False``; a
    different payload raises ``StorePayloadConflictError`` so a mid-crash
    divergence (store holding an older issuance for the same identity) can
    never silently regress the issuance or reward after a restart. Payloads
    with the same definition key but different issuer keys coexist as
    separate entries. Returns ``True`` when the payload was appended.
    """
    store = get_store()
    payloads = list(store.db.payloads or [])
    for existing in payloads:
        if _payload_identity(existing) == _payload_identity(payload):
            if existing == payload:
                return False
            raise StorePayloadConflictError(
                f"generated-quest store already holds a different payload for "
                f"definition {_payload_identity(payload)[0]!r} under issuer "
                f"{_payload_identity(payload)[1]!r}"
            )
    payloads.append(payload)
    store.db.payloads = payloads
    return True


def remove_payload(definition_key: str, issuer_key: str) -> None:
    """Remove one payload by issuance identity; a missing identity is a no-op."""
    store = get_store()
    payloads = list(store.db.payloads or [])
    for index, existing in enumerate(payloads):
        if _payload_identity(existing) == (definition_key, issuer_key):
            del payloads[index]
            store.db.payloads = payloads
            break


def clear() -> None:
    """Drop every stored payload."""
    store = get_store()
    store.db.payloads = []
