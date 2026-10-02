"""Deterministic NPC persona persistence and versioning service (D3/D4).

This module provides the deterministic persistence writer and reader for NPC
character cards and metadata. It enforces compare-and-set updates serialized
across processes via database row locking, bypasses in-process attribute caches
to avoid stale version checks, restores attribute caches upon rollback, and
emits commit-bound observability events carrying IDs and versions without prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from django.db import OperationalError, transaction
from django.db.models import F

from evennia.objects.models import ObjectDB
from typeclasses.npcs import NPC
from world.lore.npc_card import (
    NPC_CARD_FORMAT,
    NPC_PERSONA_CONTENT_GENERATION,
    NpcCard,
    NpcCardError,
    normalize_card,
    normalize_offline_greeting,
    validate_provenance,
)
from world.observability import log_info, log_warn
from world.rules.surfaces import attribute_snapshot, restore_attributes


class NpcPersonaStorageError(RuntimeError):
    """Raised when an all-or-nothing initialization fails due to storage unavailability."""


@dataclass(frozen=True)
class NpcPersonaSnapshot:
    """Snapshot of an NPC's effective character card and metadata."""

    card: NpcCard
    version: int
    generation: int
    provenance: dict[str, Any]


@dataclass(frozen=True)
class NpcPersonaUnavailable:
    """Represents an unavailable NPC persona with a stable reason."""

    reason: str


@dataclass(frozen=True)
class UpdateOutcome:
    """Outcome of an update_npc_persona call."""

    status: str  # "updated", "unchanged", "version_conflict", "invalid", "unavailable", "storage_unavailable"
    version: int | None = None
    reason: str | None = None
    error: NpcCardError | None = None


def _raw_meta_value(npc: Any) -> Any:
    """Read the raw persisted npc_persona_meta from the database, bypassing idmapper.

    Uses the sanctioned idmapper-free through join on ObjectDB.db_attributes,
    filtering on db_key.
    """
    return _raw_attribute_value(npc, "npc_persona_meta")


def _raw_attribute_value(npc: Any, key: str) -> Any:
    """Read raw persisted Attribute from database bypassing idmapper.

    Note: PickledObjectField automatically decodes the stored value.
    """
    qs = npc.db_attributes.through.objects.filter(
        objectdb_id=npc.pk, attribute__db_key=key
    ).values_list("attribute__db_value", flat=True)
    return qs.first()


def _lock_npc_row(npc: Any) -> None:
    """Take a database write lock on the NPC's ObjectDB row via guarded UPDATE.

    D4 mandates this guarded UPDATE as the first statement inside transaction.atomic()
    to serialize across processes and prevent SQLite deferred transaction upgrade deadlocks.
    """
    ObjectDB.objects.filter(id=npc.id).update(db_date_created=F("db_date_created"))


def read_npc_persona(npc: Any) -> NpcPersonaSnapshot | NpcPersonaUnavailable:
    """Read an NPC's persona without ever writing or repairing.

    Returns:
        NpcPersonaSnapshot if valid, or NpcPersonaUnavailable with a stable reason:
        'not_npc', 'missing_card', 'missing_meta', 'corrupt_card', 'corrupt_meta'.
    """
    if not isinstance(npc, NPC):
        log_warn("npc_persona_unavailable", context={"npc": str(getattr(npc, "pk", npc)), "reason": "not_npc"})
        return NpcPersonaUnavailable("not_npc")

    if not npc.attributes.has("persona"):
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "missing_card"})
        return NpcPersonaUnavailable("missing_card")

    if not npc.attributes.has("npc_persona_meta"):
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "missing_meta"})
        return NpcPersonaUnavailable("missing_meta")

    raw_card = npc.db.persona
    try:
        card = normalize_card(raw_card)
    except NpcCardError:
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "corrupt_card"})
        return NpcPersonaUnavailable("corrupt_card")

    raw_meta = npc.db.npc_persona_meta
    if not isinstance(raw_meta, Mapping) or isinstance(raw_meta, (str, bytes)):
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "corrupt_meta"})
        return NpcPersonaUnavailable("corrupt_meta")

    version = raw_meta.get("persona_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "corrupt_meta"})
        return NpcPersonaUnavailable("corrupt_meta")

    generation = raw_meta.get("generation")
    card_fmt = raw_meta.get("format")
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or not isinstance(card_fmt, int)
        or isinstance(card_fmt, bool)
    ):
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "corrupt_meta"})
        return NpcPersonaUnavailable("corrupt_meta")

    try:
        provenance = validate_provenance(raw_meta.get("provenance"))
    except NpcCardError:
        log_warn("npc_persona_unavailable", context={"npc": str(npc.pk), "reason": "corrupt_meta"})
        return NpcPersonaUnavailable("corrupt_meta")

    return NpcPersonaSnapshot(
        card=card,
        version=version,
        generation=generation,
        provenance=provenance,
    )


def current_persona_version(npc: Any) -> int | None:
    """Read an NPC's current persona_version without writing or repairing.

    Returns:
        The integer persona_version (>= 1), or None if the entity is not an NPC,
        the attribute is missing, or the metadata is malformed. Never writes.
    """
    if not isinstance(npc, NPC):
        return None

    try:
        if not getattr(npc, "attributes", None) or not npc.attributes.has("npc_persona_meta"):
            return None
        raw_meta = getattr(getattr(npc, "db", None), "npc_persona_meta", None)
    except Exception:  # observability: ignore R2: deleted or inaccessible entities yield None
        return None

    if not isinstance(raw_meta, Mapping) or isinstance(raw_meta, (str, bytes)):
        return None

    version = raw_meta.get("persona_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return None

    return version


def provenance_profile_key(npc: Any) -> str | None:
    """Read an NPC's provenance profile key without writing or repairing (design D2).

    Returns:
        The string profile key iff the entity is an NPC with valid metadata whose
        provenance kind is 'profile'. For absent, non-NPC, malformed metadata, or
        any other provenance kind (such as 'companion', whose voice lines live on the
        instance field), returns None. Never writes or repairs.
    """
    if not isinstance(npc, NPC):
        return None
    try:
        if not getattr(npc, "attributes", None) or not npc.attributes.has("npc_persona_meta"):
            return None
        raw_meta = getattr(getattr(npc, "db", None), "npc_persona_meta", None)
    except Exception:  # observability: ignore R2: deleted or inaccessible entities yield None
        return None

    if not isinstance(raw_meta, Mapping) or isinstance(raw_meta, (str, bytes)):
        return None

    prov = raw_meta.get("provenance")
    if not isinstance(prov, Mapping) or isinstance(prov, (str, bytes)):
        return None
    if prov.get("kind") != "profile":
        return None
    key = prov.get("profile")
    if not isinstance(key, str) or isinstance(key, bool) or not key:
        return None
    return key


OFFLINE_GREETING_KEY = "npc_offline_greeting"


def read_offline_greeting(npc: Any) -> str:
    """Return an NPC's stored offline-greeting field verbatim, ``""`` when unset.

    Never writes, normalizes, or repairs: a stored value is returned exactly as
    persisted (the editor validates it like any draft), and an absent or
    non-text attribute reads as ``""``.
    """
    try:
        value = getattr(getattr(npc, "db", None), OFFLINE_GREETING_KEY, None)
    except Exception:  # observability: ignore R2: deleted or inaccessible entities read as no override
        return ""
    return value if isinstance(value, str) else ""


def is_card_available(npc: Any) -> bool:
    """Silent, read-only predicate checking whether an NPC's card is available and valid (D5).

    Unlike ``read_npc_persona``, this does NOT emit the ``npc_persona_unavailable``
    observability warning: exploration snapshot calculation runs frequently and
    must stay silent for uninitialized or non-NPC targets.
    """
    if not isinstance(npc, NPC):
        return False
    if not npc.attributes.has("persona") or not npc.attributes.has("npc_persona_meta"):
        return False
    try:
        normalize_card(npc.db.persona)
    except Exception:  # observability: ignore R2: silent read-only presentation predicate deliberately suppresses card parse errors
        return False
    raw_meta = npc.db.npc_persona_meta
    if not isinstance(raw_meta, Mapping) or isinstance(raw_meta, (str, bytes)):
        return False
    version = raw_meta.get("persona_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return False
    generation = raw_meta.get("generation")
    card_fmt = raw_meta.get("format")
    if (
        not isinstance(generation, int)
        or isinstance(generation, bool)
        or not isinstance(card_fmt, int)
        or isinstance(card_fmt, bool)
    ):
        return False
    try:
        validate_provenance(raw_meta.get("provenance"))
    except Exception:  # observability: ignore R2: silent read-only presentation predicate deliberately suppresses provenance parse errors
        return False
    return True


def initialize_npc_persona(
    npc: Any,
    card_raw: Any,
    provenance: Any,
) -> NpcPersonaSnapshot:
    """Initialize an NPC persona and metadata atomically.

    If the NPC already carries metadata with the current generation, it returns the
    existing snapshot unchanged without overwriting.

    Raises:
        NpcCardError: If card or provenance validation fails.
        NpcPersonaStorageError: If a database operational error occurs.
    """
    if not isinstance(npc, NPC):
        raise NpcCardError("not_npc", "npc")

    card = normalize_card(card_raw)
    valid_prov = validate_provenance(provenance)

    # Snapshot attributes before entering transaction.atomic() to avoid cache-miss reads
    # triggering SQLite SELECTs before the guarded UPDATE (Blocking issue 3 / D4).
    snapshots = {
        "persona": attribute_snapshot(npc, "persona"),
        "npc_persona_meta": attribute_snapshot(npc, "npc_persona_meta"),
    }

    try:
        with transaction.atomic():
            # First statement inside atomic: take the database write lock
            _lock_npc_row(npc)

            # Check existing meta directly from database to avoid stale idmapper cache
            raw_meta = _raw_meta_value(npc)
            if (
                isinstance(raw_meta, Mapping)
                and raw_meta.get("generation") == NPC_PERSONA_CONTENT_GENERATION
                and isinstance(raw_meta.get("persona_version"), int)
                and not isinstance(raw_meta.get("persona_version"), bool)
            ):
                # Already initialized with current generation; return existing snapshot without overwrite
                raw_card = _raw_attribute_value(npc, "persona")
                existing_card = normalize_card(raw_card)
                return NpcPersonaSnapshot(
                    card=existing_card,
                    version=raw_meta["persona_version"],
                    generation=raw_meta["generation"],
                    provenance=raw_meta["provenance"],
                )

            # Write card and meta
            meta = {
                "format": NPC_CARD_FORMAT,
                "generation": NPC_PERSONA_CONTENT_GENERATION,
                "persona_version": 1,
                "provenance": valid_prov,
            }
            npc.db.persona = card.to_record()
            npc.db.npc_persona_meta = meta

            # Hook commit-bound event
            event_context = {
                "npc": str(npc.pk),
                "source": valid_prov.get("kind"),
                "version": 1,
            }
            if "profile" in valid_prov:
                event_context["profile"] = valid_prov["profile"]

            transaction.on_commit(
                lambda: log_info("npc_persona_initialized", context=event_context)
            )

            return NpcPersonaSnapshot(
                card=card,
                version=1,
                generation=NPC_PERSONA_CONTENT_GENERATION,
                provenance=valid_prov,
            )
    except OperationalError as exc:
        restore_attributes(npc, snapshots)
        raise NpcPersonaStorageError("storage_unavailable") from exc
    except Exception:
        restore_attributes(npc, snapshots)
        raise


def update_npc_persona(
    npc: Any,
    card_raw: Any,
    expected_version: Any,
    *,
    offline_greeting: Any = "",
    actor: Any = None,
) -> UpdateOutcome:
    """Update an NPC persona card and offline greeting using compare-and-set on persona_version.

    The card and the per-instance offline greeting (``db.npc_offline_greeting``)
    are ONE submission: any changed component advances ``persona_version``
    exactly once, an identical submission succeeds unchanged, and a stale
    expected version writes nothing. An empty greeting clears the override
    (the attribute is removed), restoring the authored default.

    Serializes across processes via a guarded row UPDATE inside transaction.atomic(),
    reads the persisted version, card, and greeting directly from the database
    bypassing idmapper caches, and restores attribute caches on rollback.
    """
    actor_id = str(getattr(actor, "pk", actor)) if actor is not None else None

    # Version validation: boolean or non-integer is rejected
    if isinstance(expected_version, bool) or not isinstance(expected_version, int):
        log_info(
            "npc_persona_update_rejected",
            context={"npc": str(getattr(npc, "pk", npc)), "char": actor_id, "reason": "invalid_version"},
        )
        return UpdateOutcome(status="invalid", version=None, reason="invalid_version", error=None)

    if not isinstance(npc, NPC):
        log_info(
            "npc_persona_update_rejected",
            context={"npc": str(getattr(npc, "pk", npc)), "char": actor_id, "reason": "not_npc"},
        )
        return UpdateOutcome(status="unavailable", version=None, reason="not_npc", error=None)

    # Validate card before starting write transaction
    try:
        new_card = normalize_card(card_raw)
    except NpcCardError as card_err:
        log_info(
            "npc_persona_update_rejected",
            context={"npc": str(npc.pk), "char": actor_id, "reason": f"invalid_card:{card_err.code}"},
        )
        return UpdateOutcome(status="invalid", version=None, reason=card_err.code, error=card_err)

    try:
        new_greeting = normalize_offline_greeting(offline_greeting)
    except NpcCardError as greeting_err:
        log_info(
            "npc_persona_update_rejected",
            context={"npc": str(npc.pk), "char": actor_id, "reason": "invalid_greeting"},
        )
        return UpdateOutcome(status="invalid", version=None, reason=greeting_err.code, error=greeting_err)

    # Snapshot attributes before transaction.atomic() (D4)
    snapshots = {
        "persona": attribute_snapshot(npc, "persona"),
        "npc_persona_meta": attribute_snapshot(npc, "npc_persona_meta"),
        OFFLINE_GREETING_KEY: attribute_snapshot(npc, OFFLINE_GREETING_KEY),
    }

    try:
        with transaction.atomic():
            # 1. Take guarded row lock first
            _lock_npc_row(npc)

            # 2. Read persisted meta bypassing idmapper
            raw_meta = _raw_meta_value(npc)
            if not isinstance(raw_meta, Mapping) or isinstance(raw_meta, (str, bytes)):
                log_info(
                    "npc_persona_update_rejected",
                    context={"npc": str(npc.pk), "char": actor_id, "reason": "missing_meta"},
                )
                return UpdateOutcome(status="unavailable", version=None, reason="missing_meta")

            current_version = raw_meta.get("persona_version")
            if not isinstance(current_version, int) or isinstance(current_version, bool):
                log_info(
                    "npc_persona_update_rejected",
                    context={"npc": str(npc.pk), "char": actor_id, "reason": "corrupt_meta"},
                )
                return UpdateOutcome(status="unavailable", version=None, reason="corrupt_meta")

            # 3. Check version conflict
            if current_version != expected_version:
                log_info(
                    "npc_persona_update_rejected",
                    context={
                        "npc": str(npc.pk),
                        "char": actor_id,
                        "reason": "version_conflict",
                        "expected_version": expected_version,
                        "current_version": current_version,
                    },
                )
                return UpdateOutcome(status="version_conflict", version=current_version, reason="version_conflict")

            # 4. Check card equality against current normalized card
            current_card_record = _raw_attribute_value(npc, "persona")
            if current_card_record is None:
                current_card_record = npc.db.persona
            try:
                current_card = normalize_card(current_card_record)
            except NpcCardError:
                log_info(
                    "npc_persona_update_rejected",
                    context={"npc": str(npc.pk), "char": actor_id, "reason": "corrupt_card"},
                )
                return UpdateOutcome(status="unavailable", version=None, reason="corrupt_card")

            raw_greeting = _raw_attribute_value(npc, OFFLINE_GREETING_KEY)
            current_greeting = normalize_offline_greeting(raw_greeting) if isinstance(raw_greeting, str) else ""
            card_changed = current_card != new_card
            greeting_changed = current_greeting != new_greeting

            if not card_changed and not greeting_changed:
                # No-op success: card and greeting identical, version does not advance
                return UpdateOutcome(status="unchanged", version=current_version)

            # 5. A component changed; advance version by exactly 1
            new_version = current_version + 1
            new_meta = dict(raw_meta)
            new_meta["persona_version"] = new_version

            if card_changed:
                npc.db.persona = new_card.to_record()
            if greeting_changed:
                if new_greeting:
                    npc.attributes.add(OFFLINE_GREETING_KEY, new_greeting)
                else:
                    npc.attributes.remove(OFFLINE_GREETING_KEY)
            npc.db.npc_persona_meta = new_meta

            # Hook commit-bound event (identifiers and flags only, never prose)
            event_context = {
                "npc": str(npc.pk),
                "char": actor_id,
                "version_from": current_version,
                "version_to": new_version,
                "card_changed": card_changed,
                "greeting_changed": greeting_changed,
            }
            transaction.on_commit(
                lambda: log_info("npc_persona_updated", context=event_context)
            )

            return UpdateOutcome(status="updated", version=new_version)

    except OperationalError:
        # observability: ignore R2: storage contention surfaces as a stable UpdateOutcome status without raising
        restore_attributes(npc, snapshots)
        return UpdateOutcome(status="storage_unavailable", version=None, reason="storage_unavailable")
    except Exception:
        restore_attributes(npc, snapshots)
        raise
