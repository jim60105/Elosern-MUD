"""Scene-package publication and read boundaries (design §4/§5).

The public operation contract this change publishes for the two downstream
designs:

``publish_scene_package``
    Validate one bounded package payload and persist it immutably, together with
    its compiled definition and spawn requirements. No actor is created, no
    quest is accepted, and a role-issued commission stays a validated symbolic
    declaration that is *not* registered as runtime authority.

``lookup_story_role``
    A read-only view of one package role's definition plus its exact binding
    status.

``activate_scene_encounter`` / ``transition_story_dialogue`` live in
:mod:`world.quests.encounter_activation` and
:mod:`world.quests.story_dialogue`; they share this module's store boundary.

Everything here is deterministic: no generative or transport dependency, and no
state change outside the quest-owned writers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.observability import log_info

from . import scene_store
from .compile import (
    IssuanceDescriptor,
    _publish_registration,
    publish_definition_views,
)
from .compile.registration import publication_scope
from .scene_package import ScenePackageDefinition, validate_scene_package
from world.rules.quest_issuance import (
    IssuerKeyError,
    Settlement,
    guild_issuer_key,
    npc_issuer_key,
)


def guild_descriptor(branch_key: str) -> IssuanceDescriptor:
    """The concrete counter-settled descriptor of a guild-branch package."""
    return IssuanceDescriptor(
        issuer_key=guild_issuer_key(branch_key), settlement=Settlement.COUNTER
    )


def symbolic_issuer_key(content_key: Any) -> str | None:
    """Validate one symbolic commission content key into its ``npc:<key>`` form."""
    if not isinstance(content_key, str) or not content_key:
        return None
    try:
        return npc_issuer_key(content_key)
    except IssuerKeyError:  # observability: ignore R2: a malformed stored symbolic key is reported as an absent lookup value, never fabricated into an issuer key
        return None


class ScenePackageNotFound(LookupError):
    """The referenced package is not published."""


class SceneRoleNotFound(LookupError):
    """The referenced package role is not defined by the package."""


@dataclass(frozen=True)
class PublishedPackage:
    """The committed result of one publication."""

    package_id: str
    definition_key: str
    created: bool
    definition: ScenePackageDefinition


@dataclass(frozen=True)
class StoryRoleLookup:
    """One read-only role lookup result."""

    package_id: str
    role_id: str
    definition: dict[str, Any]
    bound: bool
    npc_id: int | None
    availability: str
    provenance: dict[str, Any]
    commission_issuer_key: str | None


def publish_scene_package(
    payload: Any,
    *,
    owner: str,
    source_id: str | None = None,
    tick: int = 0,
) -> PublishedPackage:
    """Validate and persist one immutable scene package.

    The whole package is validated before any write. Publication registers the
    compiled definition and per-stage spawn requirements so an accepted stage
    can later resolve them through the existing runtime views, and a
    guild-branch package registers its ordinary guild offer. A role-issued
    commission is recorded as an unregistered symbolic grant: it becomes real
    authority only when its role is materialized and provisioned at activation.

    Reprocessing an identical payload returns the stored package unchanged; a
    differing payload for the same package or source identity raises
    ``ScenePackageConflictError`` without overwriting materialized persona or
    history (design §4).
    """
    if not isinstance(owner, str) or not owner:
        raise ValueError("owner must be a non-empty string")
    definition = validate_scene_package(payload)
    resolved_source = source_id if source_id is not None else definition.source_id
    # One transaction for the immutable row, its commission grant, and the
    # process-local definition/requirement/offer views. A failure anywhere rolls
    # the database back and ``publication_scope`` restores the registries, so a
    # failed publication leaves neither a durable package without its views nor
    # registered views without their package (design §5.1).
    with publication_scope():
        with transaction.atomic():
            row, created = scene_store.publish_package(
                package_id=definition.package_id,
                source_id=resolved_source,
                owner_id=owner,
                payload=payload,
                tick=tick,
            )
            _publish_definition_views_for(row, definition)
    if created:
        log_info(
            "scene_package_published",
            context={
                "package": definition.package_id,
                "owner": owner,
                "source": resolved_source or "",
                "definition": definition.quest.definition.key,
                "roles": str(len(definition.roles)),
                "scenes": str(len(definition.encounters)),
            },
        )
    return PublishedPackage(
        package_id=row.package_id,
        definition_key=definition.quest.definition.key,
        created=created,
        definition=definition,
    )


def _publish_definition_views_for(
    row: scene_store.ScenePackage, definition: ScenePackageDefinition
) -> None:
    """Register one package's definition, requirements, and commission shape."""
    core = definition.quest
    if definition.guild_branch is not None:
        _publish_registration(
            core.definition,
            guild_descriptor(definition.guild_branch),
            core.reward,
            core.stage_requirements,
        )
        return
    publish_definition_views(core.definition, core.stage_requirements)
    assert definition.commission is not None
    scene_store.ensure_commission_grant(
        row,
        definition.commission.role_id,
        definition.commission.definition_key,
        issuer_key=definition.commission.issuer_key,
        tick=0,
    )


def lookup_story_role(package_id: str, role_id: str) -> StoryRoleLookup:
    """Return one package role's definition and exact binding status (read-only).

    An unknown package or role is a named lookup failure. A missing, dead,
    deleted, or departed actor is reported through ``availability`` without
    repair (design §5.2).
    """
    row = scene_store.read_package(package_id)
    if row is None:
        raise ScenePackageNotFound(f"package {package_id!r} is not published")
    roles = row.payload.get("roles") or []
    role_definition = next(
        (entry for entry in roles if isinstance(entry, dict) and entry.get("role_id") == role_id),
        None,
    )
    if role_definition is None:
        raise SceneRoleNotFound(f"role {role_id!r} is not defined by package {package_id!r}")
    binding = scene_store.get_role_binding(package_id, role_id)
    commission = row.payload.get("commission")
    issuer_key = None
    if isinstance(commission, dict) and commission.get("role_id") == role_id:
        issuer_key = symbolic_issuer_key(commission.get("issuer_content_key"))
    return StoryRoleLookup(
        package_id=package_id,
        role_id=role_id,
        definition=dict(role_definition),
        bound=binding is not None,
        npc_id=binding.npc_id if binding is not None else None,
        availability=binding.availability if binding is not None else "unmaterialized",
        provenance=dict(binding.provenance) if binding is not None else {},
        commission_issuer_key=issuer_key,
    )


__all__ = [
    "PublishedPackage",
    "ScenePackageNotFound",
    "SceneRoleNotFound",
    "StoryRoleLookup",
    "lookup_story_role",
    "publish_scene_package",
]
