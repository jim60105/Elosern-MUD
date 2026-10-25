"""Durable per-owner authored-dialogue reading state (Shared contract v2).

The owning player carries one persisted Attribute,
:data:`READING_ATTRIBUTE`, whose exact shape is::

    {
      "schema_version": 1,
      "revision": int,
      "hosts": {
        "<stable host_key>": {
          "initialized": bool,
          "topics": {
            "<stable topic_id>": {
              "completed": bool,
              "ever_open": bool,
              "announced": bool,
            },
          },
          "pending_batch": None | {"batch_id", "topic_ids", "created_revision"},
        },
      },
    }

Reading is keyed by the owning player, the stable logical ``host_key``
(``s:<profile_key>`` or ``g:<encoded package/role>``) and the stable
source-aware ``topic_id``. A physical host dbid is never a key, so possession,
save/reload, a rematerialized generated binding and a returning phase all share
one logical record.

Ownership boundary: ``world/narrative/`` owns persistent narrative state
directly (AGENTS single-writer boundary). This module writes exactly one
Attribute and reads nothing else persistently; it never touches a dialogue
session, a scene, eligibility or any game effect.

Concurrency: SQLite has no usable ``SELECT ... FOR UPDATE``. ``record_completion``
therefore opens ``transaction.atomic()`` and makes a guarded owner-row UPDATE
(``db_date_created = db_date_created``) its FIRST statement, then reads the raw
persisted Attribute through the ``db_attributes`` join so the merge never trusts
the idmapper cache. Every read inside that block happens after the lock. The
completion entry points (action adapter, text command) own no outer
transaction, so this block is the transaction that serializes writers; a caller
that nests it inside a longer transaction owns the first-write ordering of that
outer transaction. On any failure the pre-write Attribute cache is restored
best-effort, and a successful write resets the cache so the next read
re-derives the committed row.

Observation is NOT owned here: ``ever_open`` and ``announced`` stay ``False``
and ``pending_batch`` stays ``None`` (initialized on the first host write) until
``authored-dialogue-unread-notices`` adds ``observe_availability`` /
``claim_unlock_batch``. ``reading_for`` never creates or repairs storage.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from django.db import transaction
from django.db.models import F

from evennia.objects.models import ObjectDB

from world.observability import log_info, log_warn
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort

#: The owning player's Attribute holding every host's reading record.
READING_ATTRIBUTE = "dialogue_reading"

READING_SCHEMA_VERSION = 1

#: Shared contract bounds (ASCII stable IDs).
MAX_HOST_KEY_CHARS = 768
MAX_TOPIC_ID_CHARS = 2048
MAX_BATCH_ID_CHARS = 64
MAX_PENDING_BATCH_TOPICS = 16

#: Completion statuses returned to the caller.
STATUS_SAVED = "saved"
STATUS_ALREADY_SAVED = "already_saved"

READING_COMPLETED_EVENT = "dialogue_reading_completed"
READING_INTEGRITY_EVENT = "dialogue_reading_integrity"


@dataclass(frozen=True)
class TopicReading:
    """One stable topic's persisted reading row."""

    completed: bool
    ever_open: bool
    announced: bool


@dataclass(frozen=True)
class HostReading:
    """One host's persisted reading record under its owner."""

    host_key: str
    initialized: bool
    topics: Mapping[str, TopicReading]
    pending_batch: Mapping[str, Any] | None

    def is_completed(self, topic_id: str) -> bool:
        """Whether ``topic_id`` was formally completed by this owner."""
        row = self.topics.get(topic_id)
        return bool(row is not None and row.completed)

    def completed_topic_ids(self) -> tuple[str, ...]:
        """Every completed topic ID in persisted declaration order."""
        return tuple(
            topic_id for topic_id, row in self.topics.items() if row.completed
        )


@dataclass(frozen=True)
class ReadingRecord:
    """One owner's whole reading record: the monotonic revision and its hosts."""

    revision: int
    hosts: Mapping[str, HostReading]


@dataclass(frozen=True)
class CompletionRecord:
    """The outcome of one formal completion: status and owner revision."""

    status: str
    reading_revision: int


_EMPTY_RECORD = ReadingRecord(revision=0, hosts=MappingProxyType({}))


def _integrity(reason: str, *, owner: Any = None, host_key: str | None = None) -> None:
    """Emit one bounded integrity event for corrupt or out-of-contract storage."""
    log_warn(
        READING_INTEGRITY_EVENT,
        context={
            "char": str(getattr(owner, "pk", "?")),
            "host": host_key or "?",
            "reason": reason,
        },
    )


def _parse_topic_row(raw: Any) -> TopicReading | None:
    """Parse one topic row, or ``None`` when it violates the exact schema."""
    if not isinstance(raw, Mapping):
        return None
    flags = []
    for key in ("completed", "ever_open", "announced"):
        value = raw.get(key, False)
        if not isinstance(value, bool):
            return None
        flags.append(value)
    return TopicReading(completed=flags[0], ever_open=flags[1], announced=flags[2])


def _parse_pending_batch(raw: Any) -> Mapping[str, Any] | None:
    """Parse one deferred announcement batch, or ``None`` when absent/corrupt."""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ValueError("pending_batch")
    batch_id = raw.get("batch_id")
    created_revision = raw.get("created_revision")
    topic_ids = raw.get("topic_ids")
    if (
        not isinstance(batch_id, str)
        or not batch_id
        or len(batch_id) > MAX_BATCH_ID_CHARS
        or isinstance(created_revision, bool)
        or not isinstance(created_revision, int)
        or created_revision < 0
        # Evennia persists lists as ``_SaverList`` (a MutableSequence, not a
        # list subclass), so classify by the sequence protocol.
        or isinstance(topic_ids, (str, bytes))
        or not isinstance(topic_ids, Sequence)
        or not 1 <= len(topic_ids) <= MAX_PENDING_BATCH_TOPICS
    ):
        raise ValueError("pending_batch")
    bounded: list[str] = []
    for topic_id in topic_ids:
        if (
            not isinstance(topic_id, str)
            or not topic_id
            or len(topic_id) > MAX_TOPIC_ID_CHARS
            or topic_id in bounded
        ):
            raise ValueError("pending_batch")
        bounded.append(topic_id)
    return MappingProxyType(
        {
            "batch_id": batch_id,
            "topic_ids": tuple(bounded),
            "created_revision": created_revision,
        }
    )


def _parse_host(raw: Any, host_key: str) -> HostReading | None:
    """Parse one host record, or ``None`` when it violates the exact schema."""
    if not isinstance(raw, Mapping):
        return None
    initialized = raw.get("initialized", False)
    if not isinstance(initialized, bool):
        return None
    raw_topics = raw.get("topics", {})
    if not isinstance(raw_topics, Mapping):
        return None
    topics: dict[str, TopicReading] = {}
    for topic_id, row in raw_topics.items():
        if (
            not isinstance(topic_id, str)
            or not topic_id
            or len(topic_id) > MAX_TOPIC_ID_CHARS
        ):
            return None
        parsed = _parse_topic_row(row)
        if parsed is None:
            return None
        topics[topic_id] = parsed
    try:
        pending_batch = _parse_pending_batch(raw.get("pending_batch"))
    except ValueError:  # observability: ignore R2: an out-of-contract batch makes the host record read as absent; the caller degrades to no reading
        return None
    return HostReading(
        host_key=host_key,
        initialized=initialized,
        topics=MappingProxyType(topics),
        pending_batch=pending_batch,
    )


def _parse_record(raw: Any, *, owner: Any = None) -> ReadingRecord:
    """Parse the stored Attribute, degrading corruption to "no reading".

    An absent value is the normal empty record and stays silent; a present but
    out-of-contract value emits one bounded integrity event and reads as empty,
    so a damaged row never raises into a presenter, selection or completion.
    """
    if raw is None:
        return _EMPTY_RECORD
    if not isinstance(raw, Mapping):
        _integrity("not_a_mapping", owner=owner)
        return _EMPTY_RECORD
    if raw.get("schema_version") != READING_SCHEMA_VERSION:
        _integrity("schema_version", owner=owner)
        return _EMPTY_RECORD
    revision = raw.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
        _integrity("revision", owner=owner)
        return _EMPTY_RECORD
    raw_hosts = raw.get("hosts")
    if not isinstance(raw_hosts, Mapping):
        _integrity("hosts", owner=owner)
        return _EMPTY_RECORD
    hosts: dict[str, HostReading] = {}
    for host_key, host_raw in raw_hosts.items():
        if (
            not isinstance(host_key, str)
            or not host_key
            or len(host_key) > MAX_HOST_KEY_CHARS
        ):
            _integrity("host_key", owner=owner)
            return _EMPTY_RECORD
        parsed = _parse_host(host_raw, host_key)
        if parsed is None:
            _integrity("host_record", owner=owner, host_key=host_key)
            return _EMPTY_RECORD
        hosts[host_key] = parsed
    return ReadingRecord(revision=revision, hosts=MappingProxyType(hosts))


def _serialize(record: ReadingRecord) -> dict[str, Any]:
    """Serialize one record into fresh JSON-safe containers."""
    hosts: dict[str, Any] = {}
    for host_key, host in record.hosts.items():
        topics = {
            topic_id: {
                "completed": row.completed,
                "ever_open": row.ever_open,
                "announced": row.announced,
            }
            for topic_id, row in host.topics.items()
        }
        pending = None
        if host.pending_batch is not None:
            pending = {
                "batch_id": host.pending_batch["batch_id"],
                "topic_ids": list(host.pending_batch["topic_ids"]),
                "created_revision": host.pending_batch["created_revision"],
            }
        hosts[host_key] = {
            "initialized": host.initialized,
            "topics": topics,
            "pending_batch": pending,
        }
    return {
        "schema_version": READING_SCHEMA_VERSION,
        "revision": record.revision,
        "hosts": hosts,
    }


def _raw_attribute_value(owner: Any) -> Any:
    """Read the persisted Attribute value from the database, bypassing idmapper.

    Uses the sanctioned idmapper-free through join on ``ObjectDB.db_attributes``;
    the pickled field decodes the stored value on read.
    """
    return (
        owner.db_attributes.through.objects.filter(
            objectdb_id=owner.pk, attribute__db_key=READING_ATTRIBUTE
        )
        .values_list("attribute__db_value", flat=True)
        .first()
    )


def _lock_owner_row(owner: Any) -> None:
    """Take the SQLite write lock on the owner's row via a guarded UPDATE."""
    ObjectDB.objects.filter(id=owner.pk).update(db_date_created=F("db_date_created"))


def _require_bounded_str(value: Any, maximum: int, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field} must be a non-empty string <= {maximum} characters")
    return value


def _owner_pk(owner: Any) -> int:
    pk = getattr(owner, "pk", None)
    if isinstance(pk, bool) or not isinstance(pk, int) or pk <= 0:
        raise ValueError("reading is owned by a saved persistent player")
    return pk


def read_reading(owner: Any) -> ReadingRecord:
    """The owner's whole reading record. Pure: never creates or repairs."""
    try:
        pk = _owner_pk(owner)
    except ValueError:  # observability: ignore R2: an unsaved owner has no reading state; callers degrade to the empty record
        return _EMPTY_RECORD
    try:
        raw = owner.attributes.get(READING_ATTRIBUTE)
    except Exception as error:  # observability: ignore R2: an unreadable Attribute reads as no reading and is reported once
        log_warn(
            READING_INTEGRITY_EVENT,
            context={"char": str(pk), "host": "?", "reason": "unreadable"},
            exc=error,
        )
        return _EMPTY_RECORD
    return _parse_record(raw, owner=owner)


def reading_for(owner: Any, host_key: str) -> HostReading | None:
    """One host's reading under ``owner``, or ``None``. Pure: never creates."""
    if not isinstance(host_key, str) or not host_key:
        return None
    return read_reading(owner).hosts.get(host_key)


def reading_revision(owner: Any) -> int:
    """The owner's monotonic reading revision (0 before any saved completion)."""
    return read_reading(owner).revision


def completed_topic_ids(owner: Any, host_key: str) -> tuple[str, ...]:
    """Every completed topic ID under one owner and stable host key."""
    host = reading_for(owner, host_key)
    return () if host is None else host.completed_topic_ids()


def record_completion(
    owner: Any, *, host_key: str, topic_id: str
) -> CompletionRecord:
    """Persist one formal topic completion under the owner's reading lock.

    Returns ``saved`` when this call advanced the record and ``already_saved``
    (with the unchanged revision) when the topic was already completed, so a
    duplicate acknowledgement from another connection stays idempotent and the
    revision only increments on a real change. Only the named host/topic pair is
    merged; every other host and topic row is carried forward in fresh
    containers, so a concurrently cached snapshot can never observe a mutation
    in place.
    """
    pk = _owner_pk(owner)
    _require_bounded_str(host_key, MAX_HOST_KEY_CHARS, "host_key")
    _require_bounded_str(topic_id, MAX_TOPIC_ID_CHARS, "topic_id")

    # Snapshot BEFORE the atomic block: a cache-miss SELECT here must never
    # become the first statement of the transaction that takes the write lock.
    snapshot = attribute_snapshot(owner, READING_ATTRIBUTE)
    try:
        with transaction.atomic():
            # First statement inside the atomic: serialize SQLite writers.
            _lock_owner_row(owner)
            record = _parse_record(_raw_attribute_value(owner), owner=owner)
            current = record.hosts.get(host_key)
            if current is not None and current.is_completed(topic_id):
                return CompletionRecord(
                    status=STATUS_ALREADY_SAVED, reading_revision=record.revision
                )
            revision = record.revision + 1
            hosts = dict(record.hosts)
            hosts[host_key] = _merged_host(current, host_key, topic_id)
            value = _serialize(
                ReadingRecord(revision=revision, hosts=MappingProxyType(hosts))
            )
            owner.attributes.add(READING_ATTRIBUTE, value)
    except Exception:
        restore_attribute_best_effort(owner, READING_ATTRIBUTE, snapshot)
        raise

    # Drop the in-process cache so the next read re-derives the committed row
    # instead of serving a value a later outer rollback could invalidate.
    try:
        owner.attributes.reset_cache()
    except Exception as error:  # observability: ignore R2: a cache reset failure leaves a correct committed row; the next read still resolves it
        log_warn(
            READING_INTEGRITY_EVENT,
            context={"char": str(pk), "host": host_key, "reason": "cache_reset"},
            exc=error,
        )

    log_info(
        READING_COMPLETED_EVENT,
        context={
            "char": str(pk),
            "host": host_key,
            "topic": topic_id,
            "revision": revision,
            "status": STATUS_SAVED,
        },
    )
    return CompletionRecord(status=STATUS_SAVED, reading_revision=revision)


def _merged_host(
    current: HostReading | None, host_key: str, topic_id: str
) -> HostReading:
    """One host record with ``topic_id`` completed and every sibling retained."""
    topics = {} if current is None else dict(current.topics)
    existing = topics.get(topic_id)
    topics[topic_id] = TopicReading(
        completed=True,
        ever_open=bool(existing.ever_open) if existing is not None else False,
        announced=bool(existing.announced) if existing is not None else False,
    )
    return HostReading(
        host_key=host_key,
        # Observation owns ``initialized``; a reading-only write leaves the host
        # unobserved so the notification slice can still run its first scan.
        initialized=bool(current.initialized) if current is not None else False,
        topics=MappingProxyType(topics),
        pending_batch=current.pending_batch if current is not None else None,
    )


__all__ = [
    "MAX_BATCH_ID_CHARS",
    "MAX_HOST_KEY_CHARS",
    "MAX_TOPIC_ID_CHARS",
    "READING_ATTRIBUTE",
    "READING_COMPLETED_EVENT",
    "READING_INTEGRITY_EVENT",
    "READING_SCHEMA_VERSION",
    "STATUS_ALREADY_SAVED",
    "STATUS_SAVED",
    "CompletionRecord",
    "HostReading",
    "ReadingRecord",
    "TopicReading",
    "completed_topic_ids",
    "read_reading",
    "reading_for",
    "reading_revision",
    "record_completion",
]
