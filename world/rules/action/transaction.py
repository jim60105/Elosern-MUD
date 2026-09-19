"""The single commit point: surface snapshots, restore, and the commit.

``_commit`` is the pipeline's only state-writing step: it snapshots every
declared surface of every touched object, applies the pending effects inside
one atomic transaction, and restores the snapshots best-effort on failure.
"""

import time
from copy import deepcopy
from typing import Any

from django.db import transaction

from world.observability import log_info, log_warn

from world.rules.action.contracts import (
    SNAPSHOTTED_SURFACES,
    CommitFailed,
    PendingEffect,
    RejectReason,
)


def _attribute_snapshot(
    entity: Any,
    key: str,
    category: str | None = None,
) -> tuple[bool, Any]:
    exists = entity.attributes.has(key, category=category)
    value = (
        deepcopy(entity.attributes.get(key, category=category))
        if exists
        else None
    )
    return exists, value


def _snapshot_entity_state(entity: Any) -> dict[str, Any]:
    return {
        "traits": _attribute_snapshot(entity, "traits", "traits"),
        "disguised_stats": _attribute_snapshot(entity, "disguised_stats"),
        "disguise_provenance": _attribute_snapshot(entity, "disguise_provenance"),
        "sexual_traits": _attribute_snapshot(
            entity,
            "sexual_traits",
            "traits",
        ),
        "virgin": _attribute_snapshot(entity, "virgin", "sexual_state"),
        "experience_types": _attribute_snapshot(
            entity,
            "experience_types",
            "sexual_state",
        ),
        "climax_turns": _attribute_snapshot(entity, "climax_turns", "sexual_state"),
        "pending_climax_extension": _attribute_snapshot(
            entity,
            "pending_climax_extension",
            "sexual_state",
        ),
        "submission_marks": _attribute_snapshot(
            entity,
            "submission_marks",
            "sexual_state",
        ),
        "buffs": _attribute_snapshot(entity, "buffs"),
        "skill_grants": _attribute_snapshot(entity, "skill_grants"),
        # Cross-lineage unlocks write db.skills inside the practice award's
        # commit; the rollback face must restore it so a failed action undoes
        # the grant that its award triggered (design: the grant shares the
        # award's commit boundary, forward and backward).
        "skills": _attribute_snapshot(entity, "skills"),
        "skill_proficiency": _attribute_snapshot(entity, "skill_proficiency"),
        "skill_practice_day": _attribute_snapshot(entity, "skill_practice_day"),
        "title_collection": _attribute_snapshot(entity, "title_collection"),
        "title_equipped": _attribute_snapshot(entity, "title_equipped"),
        "pending_title_ballot": _attribute_snapshot(entity, "pending_title_ballot"),
        "title_nomination_declines": _attribute_snapshot(
            entity,
            "title_nomination_declines",
        ),
        "title_epithet_removals": _attribute_snapshot(
            entity,
            "title_epithet_removals",
        ),
    }


def _restore_attribute(
    entity: Any,
    key: str,
    snapshot: tuple[bool, Any],
    category: str | None = None,
) -> None:
    existed, value = snapshot
    if existed:
        entity.attributes.add(key, deepcopy(value), category=category)
    else:
        entity.attributes.remove(key, category=category)


def _restore_entity_state(entity: Any, snapshot: dict[str, Any]) -> None:
    _restore_attribute(entity, "traits", snapshot["traits"], "traits")
    _restore_attribute(entity, "disguised_stats", snapshot["disguised_stats"])
    _restore_attribute(entity, "disguise_provenance", snapshot["disguise_provenance"])
    _restore_attribute(
        entity,
        "sexual_traits",
        snapshot["sexual_traits"],
        "traits",
    )
    _restore_attribute(entity, "virgin", snapshot["virgin"], "sexual_state")
    _restore_attribute(
        entity,
        "experience_types",
        snapshot["experience_types"],
        "sexual_state",
    )
    _restore_attribute(
        entity,
        "climax_turns",
        snapshot["climax_turns"],
        "sexual_state",
    )
    _restore_attribute(
        entity,
        "pending_climax_extension",
        snapshot["pending_climax_extension"],
        "sexual_state",
    )
    _restore_attribute(
        entity,
        "submission_marks",
        snapshot["submission_marks"],
        "sexual_state",
    )
    _restore_attribute(entity, "buffs", snapshot["buffs"])
    _restore_attribute(entity, "skill_grants", snapshot["skill_grants"])
    _restore_attribute(entity, "skills", snapshot["skills"])
    _restore_attribute(entity, "skill_proficiency", snapshot["skill_proficiency"])
    _restore_attribute(entity, "skill_practice_day", snapshot["skill_practice_day"])
    _restore_attribute(entity, "title_collection", snapshot["title_collection"])
    _restore_attribute(entity, "title_equipped", snapshot["title_equipped"])
    _restore_attribute(
        entity,
        "pending_title_ballot",
        snapshot["pending_title_ballot"],
    )
    _restore_attribute(
        entity,
        "title_nomination_declines",
        snapshot["title_nomination_declines"],
    )
    _restore_attribute(
        entity,
        "title_epithet_removals",
        snapshot["title_epithet_removals"],
    )
    entity.traits.trait_data = entity.attributes.get(
        "traits",
        default={},
        category="traits",
    )
    entity.traits._cache.clear()
    entity.__dict__.pop("sexual", None)


def _is_battlefield_like(obj: Any) -> bool:
    """Return whether an object exposes the encounter state this resolver owns."""
    return hasattr(obj, "fled") and hasattr(obj, "roster")


_ENTITY_SURFACES = frozenset(
    {"traits", "sexual", "buffs", "skill_grants", "progression", "titles"}
)


def _snapshot_touched(obj: Any, surfaces: frozenset[str]) -> dict[str, Any]:
    """Snapshot the aggregated declared surfaces of one touched object."""
    if _is_battlefield_like(obj):
        return {
            "battlefield": (
                frozenset(obj.fled),
                frozenset(getattr(obj, "knocked_out", ())),
            )
        }
    snapshot: dict[str, Any] = {}
    if surfaces & _ENTITY_SURFACES:
        snapshot["entity"] = _snapshot_entity_state(obj)
    if "quest_log" in surfaces:
        snapshot["quest_log"] = _attribute_snapshot(obj, "quest_log")
    if "instance_pin" in surfaces:
        snapshot["instance_pin"] = _attribute_snapshot(obj, "pin_reasons")
    if "wallet" in surfaces:
        snapshot["wallet"] = _attribute_snapshot(obj, "wallet")
    if "inventory" in surfaces:
        snapshot["inventory"] = _attribute_snapshot(obj, "inventory")
    if "reward_claims" in surfaces:
        snapshot["reward_claims"] = _attribute_snapshot(obj, "guild_reward_claims")
    if "action_evidence" in surfaces:
        snapshot["action_evidence"] = _attribute_snapshot(obj, "action_evidence")
    return snapshot


def _restore_touched(
    obj: Any,
    snapshot: dict[str, Any],
    surfaces: frozenset[str],
) -> None:
    """Restore an object's aggregated declared surfaces by shape."""
    if _is_battlefield_like(obj):
        fled, knocked_out = snapshot.get(
            "battlefield",
            (
                frozenset(obj.fled),
                frozenset(getattr(obj, "knocked_out", ())),
            ),
        )
        obj.fled = set(fled)
        if hasattr(obj, "knocked_out"):
            obj.knocked_out = set(knocked_out)
        return
    if "entity" in snapshot:
        _restore_entity_state(obj, snapshot["entity"])
    if "quest_log" in surfaces and "quest_log" in snapshot:
        _restore_attribute(obj, "quest_log", snapshot["quest_log"])
    if "instance_pin" in surfaces and "instance_pin" in snapshot:
        _restore_attribute(obj, "pin_reasons", snapshot["instance_pin"])
    if "wallet" in surfaces and "wallet" in snapshot:
        _restore_attribute(obj, "wallet", snapshot["wallet"])
    if "inventory" in surfaces and "inventory" in snapshot:
        _restore_attribute(obj, "inventory", snapshot["inventory"])
    if "reward_claims" in surfaces and "reward_claims" in snapshot:
        _restore_attribute(obj, "guild_reward_claims", snapshot["reward_claims"])
    if "action_evidence" in surfaces and "action_evidence" in snapshot:
        _restore_attribute(obj, "action_evidence", snapshot["action_evidence"])


def _restore_touched_best_effort(
    obj: Any,
    snapshot: dict[str, Any],
    surfaces: frozenset[str],
) -> None:
    """Restore one touched object without letting a second failure escape.

    After a commit failure the database is rolled back; if restoring the
    pre-operation value also raises, invalidating Evennia's attribute cache
    leaves the next read consistent with persistence instead of serving a
    stale value.
    """
    try:
        _restore_touched(obj, snapshot, surfaces)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:  # observability: ignore R2: cache invalidation is best-effort; the restore failure itself is logged below
            pass
        log_warn(
            "rollback_restore_failed",
            exc=error,
            context={"stage": "action_commit", "obj": str(obj), "key": "touched"},
        )


def _commit(pending: list[PendingEffect], *, char: str, action: str) -> None:
    for effect in pending:
        unsupported = effect.surfaces - SNAPSHOTTED_SURFACES
        if unsupported:
            raise CommitFailed(
                RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                f"{effect.description}: {sorted(unsupported)}",
            )
    touched: list[Any] = []
    touched_ids: set[int] = set()
    surfaces_of: dict[int, frozenset[str]] = {}
    for effect in pending:
        identity = id(effect.entity)
        surfaces_of[identity] = surfaces_of.get(identity, frozenset()) | frozenset(
            effect.surfaces
        )
        if identity not in touched_ids:
            touched.append(effect.entity)
            touched_ids.add(identity)
    snapshots = {
        id(entity): _snapshot_touched(entity, surfaces_of[id(entity)])
        for entity in touched
    }
    try:
        started = time.monotonic()
        with transaction.atomic():
            for effect in pending:
                effect.apply()
            # Boundary event fires only on the OUTERMOST durable commit: the
            # resolver's atomic block is routinely a savepoint inside a
            # combat/item transaction, and a rolled-back outer unit must not
            # leave an action_commit line behind (on_commit discards it).
            effects = len(pending)
            elapsed_ms = int((time.monotonic() - started) * 1000)
            transaction.on_commit(
                lambda: log_info(
                    "action_commit",
                    context={"char": char, "action": action, "ms": elapsed_ms, "effects": effects},
                )
            )
    except Exception as error:
        for entity in touched:
            _restore_touched_best_effort(entity, snapshots[id(entity)], surfaces_of[id(entity)])
        raise CommitFailed(RejectReason.COMMIT_FAILED, str(error)) from error
