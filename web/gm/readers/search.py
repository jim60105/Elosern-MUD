"""Global runtime search (S3 §3/§6).

An exact ``#dbref`` (or bare dbref) resolves straight to that object, whatever
its kind; any other text matches object keys, then quest ids, then narrative
source ids — in that precedence and never as one merged ranking. The result
carries the link descriptor the SPA navigates with, so a non-curated object
lands on raw inspection and a quest carries the owner identity its record id is
scoped by.
"""

from __future__ import annotations

import re
from typing import Any

from web.gm.readers._entities import label_of, mapping_values, object_kind
from web.gm.readers._sections import link, row

KIND = "search"

#: How many matches one precedence tier may contribute.
MAX_RESULTS_PER_TIER = 20

DBREF_PATTERN = re.compile(r"^#?(\d+)$")


def dbref_result(query: str) -> dict[str, Any] | None:
    """The exact-dbref result, or None when the query is not a dbref."""
    match = DBREF_PATTERN.fullmatch(query)
    if match is None:
        return None
    from evennia.objects.models import ObjectDB

    dbref = int(match.group(1))
    entity = ObjectDB.objects.filter(pk=dbref).first()
    if entity is None:
        return None
    kind = object_kind(entity) or "object"
    return {
        "kind": kind,
        "id": str(dbref),
        "label": label_of(entity),
        "dbref": dbref,
        "matched": "dbref",
        "link": link(kind, dbref, label_of(entity)),
    }


def object_key_results(query: str, *, limit: int = MAX_RESULTS_PER_TIER) -> list[dict[str, Any]]:
    """Objects whose key matches exactly, then those containing the text."""
    from evennia.objects.models import ObjectDB

    found: list[Any] = list(
        ObjectDB.objects.filter(db_key__iexact=query).order_by("id")[:limit]
    )
    if len(found) < limit:
        found.extend(
            entity
            for entity in ObjectDB.objects.filter(db_key__icontains=query)
            .exclude(pk__in=[item.pk for item in found])
            .order_by("id")[: limit - len(found)]
        )
    results = []
    for entity in found:
        kind = object_kind(entity) or "object"
        results.append(
            {
                "kind": kind,
                "id": str(entity.pk),
                "label": label_of(entity),
                "dbref": entity.pk,
                "matched": "object_key",
                "link": link(kind, entity.pk, label_of(entity)),
            }
        )
    return results


def quest_id_results(query: str, *, limit: int = MAX_RESULTS_PER_TIER) -> list[dict[str, Any]]:
    """Runtime quest records whose quest id matches exactly."""
    from typeclasses.characters import PlayerCharacter

    results = []
    for player in PlayerCharacter.objects.all_family().order_by("id"):
        raw_log = getattr(getattr(player, "db", None), "quest_log", None)
        if not raw_log:
            continue
        for entry in raw_log:
            stored_entry = mapping_values(entry)
            if stored_entry is None:
                continue
            if str(stored_entry.get("quest_id")) != query:
                continue
            results.append(
                {
                    "kind": "quests",
                    "id": query,
                    "label": query,
                    "dbref": None,
                    "matched": "quest_id",
                    "link": {"kind": "quests", "id": query, "owner": player.pk, "label": query},
                }
            )
            if len(results) >= limit:
                return results
    return results


def source_id_results(query: str, *, limit: int = MAX_RESULTS_PER_TIER) -> list[dict[str, Any]]:
    """Narrative records whose stable identity matches the text exactly."""
    from world.narrative import models

    results: list[dict[str, Any]] = []

    def add(kind: str, identifier: str, label: str) -> None:
        results.append(
            {
                "kind": "narrative",
                "id": identifier,
                "label": label,
                "dbref": None,
                "matched": "source_id",
                "link": link("narrative", identifier, label),
            }
        )

    for event in models.NarrativeEvent.objects.filter(source_id=query).order_by("id")[:limit]:
        add("event", f"event:{event.source_id}", event.event_type)
    for letter in models.LetterSend.objects.filter(source_id=query).order_by("id")[:limit]:
        add("letter", f"letter:{letter.source_id}", letter.recipient_id)
    for thread in models.StoryThread.objects.filter(thread_id=query).order_by("id")[:limit]:
        add("thread", f"thread:{thread.thread_id}", thread.origin)
    for session in models.DreamSession.objects.filter(session_id=query).order_by("id")[:limit]:
        add("dream", f"dream:{session.session_id}", session.owner_id)
    for draft in models.AuthoringDraft.objects.filter(draft_id=query).order_by("id")[:limit]:
        add("draft", f"draft:{draft.draft_id}", draft.owner_id)
    for request in models.CreativeRequest.objects.filter(submission_key=query).order_by("id")[:limit]:
        add("request", f"request:{request.submission_key}", request.owner_id)
    return results[:limit]


def memory_source_result(query: str, *, limit: int = MAX_RESULTS_PER_TIER) -> list[dict[str, Any]]:
    """Memories whose recorded source identity matches the text."""
    from world.narrative.models import MemoryRecord

    results = []
    for record in MemoryRecord.objects.filter(source_id=query).order_by("id")[:limit]:
        results.append(
            {
                "kind": "memories",
                "id": str(record.pk),
                "label": query,
                "dbref": None,
                "matched": "source_id",
                "link": link("memories", record.pk, record.category),
            }
        )
    return results


def search(query: Any) -> dict[str, Any]:
    """Resolve one query into its ordered results."""
    from web.gm.readers.errors import InvalidQuery

    text = str(query or "").strip()
    if not text:
        raise InvalidQuery("請輸入查詢文字（名稱、#dbref、任務編號或來源識別）。")
    if len(text) > 255:
        text = text[:255]
    exact = dbref_result(text)
    if exact is not None:
        return {"query": text, "results": [exact]}
    results = object_key_results(text)
    results.extend(quest_id_results(text))
    results.extend(source_id_results(text))
    results.extend(memory_source_result(text))
    return {"query": text, "results": results}


__all__ = [
    "KIND",
    "MAX_RESULTS_PER_TIER",
    "dbref_result",
    "object_key_results",
    "quest_id_results",
    "search",
    "source_id_results",
]
