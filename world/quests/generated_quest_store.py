"""Durable mirror of every registered generated quest (design D1).

One ``GeneratedQuestStore`` Evennia Script (key ``generated_quest_store``)
holds a JSON-safe list of serialized payloads, one per generated quest key:
``{"definition": {...}, "offer": {...}, "requirements": [...]}``. The Script
survives server restarts and is the single write point
``register_generated_quest`` appends to before touching the three
process-local registries.

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


def _definition_key(payload: dict) -> str:
    """Return the definition key a payload mirrors."""
    return payload["definition"]["key"]


def _index_of(store: GeneratedQuestStore, definition_key: str) -> int | None:
    """Return the position of one definition key in the store, or ``None``."""
    for position, payload in enumerate(store.db.payloads or []):
        if _definition_key(payload) == definition_key:
            return position
    return None


def list_payloads() -> list[dict]:
    """Return a copy of every stored payload in registration order."""
    return list(get_store().db.payloads or [])


def append_payload(payload: dict) -> bool:
    """Append one payload unless its definition key is already stored.

    Idempotent by definition key with content verification: a payload whose
    ``definition.key`` already exists is compared field by field -- an equal
    payload leaves the store untouched and returns ``False``; a different
    payload raises ``StorePayloadConflictError`` so a mid-crash divergence
    (store holding an older offer for the same key) can never silently regress
    the offer or reward after a restart. Returns ``True`` when the payload was
    appended.
    """
    store = get_store()
    payloads = list(store.db.payloads or [])
    for existing in payloads:
        if _definition_key(existing) == _definition_key(payload):
            if existing == payload:
                return False
            raise StorePayloadConflictError(
                f"generated-quest store already holds a different payload for "
                f"definition {_definition_key(payload)!r}"
            )
    payloads.append(payload)
    store.db.payloads = payloads
    return True


def remove_payload(definition_key: str) -> None:
    """Remove one payload by definition key; a missing key is a no-op."""
    store = get_store()
    payloads = list(store.db.payloads or [])
    index = _index_of(store, definition_key)
    if index is None:
        return
    del payloads[index]
    store.db.payloads = payloads


def clear() -> None:
    """Drop every stored payload."""
    store = get_store()
    store.db.payloads = []
