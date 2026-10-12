"""The single read/write boundary over the persistent scene-package records.

Every write to ``world.quests.models`` goes through this module, exactly as the
compile boundary is the sole writer of the scene requirement registry and the
generated-quest store is the sole writer of its Script. Immutable published
definitions are written once by :func:`publish_package`; mutable runtime state
(role binding, encounter, dialogue revision, commission grant) is written by the
narrow helpers below, each of which relies on the database uniqueness constraint
rather than an in-memory scan to keep one exact identity per role, scene/player
and commission.

The module is deterministic and imports no generative or transport module.
"""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from .models import (
    SceneEncounterRuntime,
    ScenePackage,
    StoryCommissionGrant,
    StoryRoleBinding,
    StoryRoleDialogueRuntime,
)

PACKAGE_STATUS_PUBLISHED = "published"
PACKAGE_STATUS_CANCELLED = "cancelled"

ENCOUNTER_PENDING = "pending"
ENCOUNTER_ACTIVATED = "activated"
ENCOUNTER_CANCELLED = "cancelled"
ENCOUNTER_UNAVAILABLE = "unavailable"

AVAILABILITY_BOUND = "bound"


class ScenePackageConflictError(ValueError):
    """A published identity already exists with different content."""


class SceneStoreError(ValueError):
    """A runtime record write violates the store contract."""


def publish_package(
    *,
    package_id: str,
    source_id: str | None,
    owner_id: str,
    payload: dict[str, Any],
    version: int = 1,
    tick: int = 0,
) -> tuple[ScenePackage, bool]:
    """Persist one immutable package, returning ``(package, created)``.

    Replaying an identical package identity returns the stored row unchanged.
    A differing payload under the same ``package_id``, or a differing package
    for an already-used ``source_id``, raises
    :class:`ScenePackageConflictError` without touching stored content, so a
    revised plan can never overwrite a materialized character's identity,
    history, or baseline persona (design §4).
    """
    if not isinstance(package_id, str) or not package_id:
        raise SceneStoreError("package_id must be a non-empty string")
    existing = ScenePackage.objects.filter(package_id=package_id).first()
    if existing is not None:
        if existing.payload != payload or existing.version != version:
            raise ScenePackageConflictError(
                f"package {package_id!r} is already published with different content"
            )
        return existing, False
    if source_id is not None:
        by_source = ScenePackage.objects.filter(source_id=source_id).first()
        if by_source is not None:
            raise ScenePackageConflictError(
                f"source {source_id!r} is already published as package "
                f"{by_source.package_id!r}"
            )
    try:
        with transaction.atomic():
            row = ScenePackage.objects.create(
                package_id=package_id,
                source_id=source_id,
                owner_id=owner_id,
                version=version,
                status=PACKAGE_STATUS_PUBLISHED,
                payload=payload,
                created_tick=tick,
            )
    except IntegrityError as error:
        raise ScenePackageConflictError(
            f"package {package_id!r} was published concurrently"
        ) from error
    return row, True


def read_package(package_id: str) -> ScenePackage | None:
    """Return the stored package row, or ``None``."""
    return ScenePackage.objects.filter(package_id=package_id).first()


def package_by_source(source_id: str) -> ScenePackage | None:
    """Return the package published for one durable source identity, or ``None``."""
    return ScenePackage.objects.filter(source_id=source_id).first()


def list_packages() -> list[ScenePackage]:
    """Return every stored package in creation order."""
    return list(ScenePackage.objects.order_by("id"))


def package_for_definition(definition_key: str) -> ScenePackage | None:
    """Return the published package whose compiled definition key matches, or ``None``.

    Read-only: the accepted-stage consumer uses it to tell a validated
    package-owned scene from a hand-written one. The payload is validated
    through the shared cache, so the scan does not recompile on every call.
    """
    from .scene_package import validated_package

    for row in list_packages():
        if row.status != PACKAGE_STATUS_PUBLISHED:
            continue
        definition = validated_package(row.package_id, row.payload)
        if definition is not None and definition.quest.definition.key == definition_key:
            return row
    return None


def cancel_package(package_id: str) -> bool:
    """Mark one unactivated package cancelled (definitions stay for replay).

    Cancelled definitions are discarded according to source lifecycle; no actor
    exists for them (design §7). The immutable payload itself is never rewritten.
    """
    row = ScenePackage.objects.filter(package_id=package_id).first()
    if row is None:
        return False
    if row.status == PACKAGE_STATUS_CANCELLED:
        return False
    # ``status`` is the one mutable field on the otherwise immutable row; the
    # store-owned transition applies only that field and still refuses a payload
    # rewrite through the manager's normal update/delete guards.
    ScenePackage.objects.transition_status(package_id, PACKAGE_STATUS_CANCELLED)
    return True


def get_role_binding(package_id: str, role_id: str) -> StoryRoleBinding | None:
    """Return the exact role binding for one package role, or ``None``."""
    return StoryRoleBinding.objects.filter(
        package__package_id=package_id, role_id=role_id
    ).first()


def list_role_bindings(package_id: str) -> list[StoryRoleBinding]:
    return list(
        StoryRoleBinding.objects.filter(package__package_id=package_id).order_by("role_id")
    )


def get_role_binding_for_npc(npc_id: int) -> StoryRoleBinding | None:
    """Return any binding naming one live actor id (retention lookup), or ``None``.

    Read-only: a retained actor may be referenced by exactly one binding, which
    is the ownership rule the retention transfer relies on.
    """
    return StoryRoleBinding.objects.filter(npc_id=npc_id).first()


def bind_role(
    package: ScenePackage,
    role_id: str,
    npc_id: int,
    *,
    provenance: dict[str, Any] | None = None,
    availability: str = AVAILABILITY_BOUND,
    tick: int = 0,
) -> StoryRoleBinding:
    """Record one exact role binding, refusing a different actor for the role.

    The database uniqueness constraint on ``(package, role_id)`` is the
    authority: a concurrent or repeated write either returns the committed row
    or raises, and never creates a second actor for one role (design §5.2).
    """
    if not isinstance(npc_id, int) or isinstance(npc_id, bool) or npc_id <= 0:
        raise SceneStoreError("npc_id must be a positive integer")
    existing = get_role_binding(package.package_id, role_id)
    if existing is not None:
        if existing.npc_id != npc_id:
            raise ScenePackageConflictError(
                f"role {role_id!r} of package {package.package_id!r} is already "
                f"bound to actor {existing.npc_id}"
            )
        return existing
    try:
        return StoryRoleBinding.objects.create(
            package=package,
            role_id=role_id,
            npc_id=int(npc_id),
            provenance=dict(provenance or {}),
            availability=availability,
            updated_tick=tick,
        )
    except IntegrityError as error:
        raise ScenePackageConflictError(
            f"role {role_id!r} of package {package.package_id!r} was bound concurrently"
        ) from error


def set_role_availability(
    package_id: str, role_id: str, availability: str, *, tick: int = 0
) -> bool:
    """Update a binding's availability without ever rebinding the actor."""
    return bool(
        StoryRoleBinding.objects.filter(
            package__package_id=package_id, role_id=role_id
        ).update(availability=availability, updated_tick=tick)
    )


def get_encounter(
    package_id: str, scene_id: str, player_id: int
) -> SceneEncounterRuntime | None:
    return SceneEncounterRuntime.objects.filter(
        package__package_id=package_id, scene_id=scene_id, player_id=player_id
    ).first()


def reserved_encounter(
    package: ScenePackage, scene_id: str, player_id: int, *, tick: int = 0
) -> tuple[SceneEncounterRuntime, bool]:
    """Reserve the unique activation identity before any materialization.

    The ``(package, scene_id, player_id)`` row is created first, so a competing
    activation loses on the database constraint instead of racing a read of an
    absent row (design §5.2; SQLite has no row-level lock).
    """
    try:
        with transaction.atomic():
            row = SceneEncounterRuntime.objects.create(
                package=package,
                scene_id=scene_id,
                player_id=player_id,
                state=ENCOUNTER_PENDING,
                updated_tick=tick,
            )
    except IntegrityError:
        existing = get_encounter(package.package_id, scene_id, player_id)
        if existing is None:  # pragma: no cover - defensive
            raise
        return existing, False
    return row, True


def set_encounter_state(
    package: ScenePackage,
    scene_id: str,
    player_id: int,
    state: str,
    *,
    activation_tick: int | None = None,
    reason: str = "",
    tick: int = 0,
) -> bool:
    """Write one encounter lifecycle state, returning whether a row changed."""
    return bool(
        SceneEncounterRuntime.objects.filter(
            package=package, scene_id=scene_id, player_id=player_id
        ).update(
            state=state,
            activation_tick=activation_tick,
            reason=reason,
            updated_tick=tick,
        )
    )


def mark_encounter_activated(
    package: ScenePackage,
    scene_id: str,
    player_id: int,
    *,
    activation_tick: int,
    tick: int = 0,
) -> bool:
    return set_encounter_state(
        package,
        scene_id,
        player_id,
        ENCOUNTER_ACTIVATED,
        activation_tick=activation_tick,
        reason="",
        tick=tick,
    )


def set_encounter_room(
    package: ScenePackage,
    scene_id: str,
    player_id: int,
    room_id: int,
    *,
    tick: int = 0,
) -> bool:
    """Record the one room an instance-layer encounter materialized.

    Written inside the activation transaction, so a repeat activation reuses the
    committed room and a rolled-back attempt leaves no room identity behind.
    """
    return bool(
        SceneEncounterRuntime.objects.filter(
            package=package, scene_id=scene_id, player_id=player_id
        ).update(room_id=int(room_id), updated_tick=tick)
    )



def get_dialogue_phase(package_id: str, role_id: str) -> StoryRoleDialogueRuntime | None:
    return StoryRoleDialogueRuntime.objects.filter(
        package__package_id=package_id, role_id=role_id
    ).first()


def set_dialogue_phase(
    package: ScenePackage,
    role_id: str,
    phase_id: str,
    *,
    tick: int = 0,
) -> StoryRoleDialogueRuntime:
    """Initialize one role's dialogue phase at revision zero.

    Used once per role when the encounter commits. A later phase change goes
    through :func:`advance_dialogue_phase`, which enforces monotonic revision.
    """
    existing = get_dialogue_phase(package.package_id, role_id)
    if existing is not None:
        return existing
    try:
        return StoryRoleDialogueRuntime.objects.create(
            package=package,
            role_id=role_id,
            selected_phase=phase_id,
            revision=0,
            updated_tick=tick,
        )
    except IntegrityError as error:
        raise ScenePackageConflictError(
            f"role {role_id!r} phase was initialized concurrently"
        ) from error


def advance_dialogue_phase(
    package: ScenePackage,
    role_id: str,
    phase_id: str,
    *,
    expected_revision: int,
    tick: int = 0,
) -> StoryRoleDialogueRuntime | None:
    """Advance one role's phase with a monotonic revision, or ``None``.

    ``expected_revision`` is the revision the deterministic caller resolved its
    decision against -- not one this helper reads for itself. The conditional
    ``UPDATE`` matches that exact revision, so a caller acting on a stale
    revision is refused (``None``) instead of silently overwriting a newer
    selected phase, and the revision increments by exactly one (design §5.2/§6).
    """
    updated = StoryRoleDialogueRuntime.objects.filter(
        package=package, role_id=role_id, revision=expected_revision
    ).update(
        selected_phase=phase_id,
        revision=expected_revision + 1,
        updated_tick=tick,
    )
    if not updated:
        return None
    return get_dialogue_phase(package.package_id, role_id)


def get_commission_grant(
    package_id: str, role_id: str, definition_key: str
) -> StoryCommissionGrant | None:
    return StoryCommissionGrant.objects.filter(
        package__package_id=package_id,
        role_id=role_id,
        definition_key=definition_key,
    ).first()


def list_commission_grants(package_id: str | None = None) -> list[StoryCommissionGrant]:
    query = StoryCommissionGrant.objects.all()
    if package_id is not None:
        query = query.filter(package__package_id=package_id)
    return list(query.order_by("id"))


def ensure_commission_grant(
    package: ScenePackage,
    role_id: str,
    definition_key: str,
    *,
    issuer_key: str,
    tick: int = 0,
) -> StoryCommissionGrant:
    """Record one planned commission grant, without an actor or registration.

    Publication writes the grant shape (durable record that this role is
    authorized for exactly this commission) while ``npc_id`` stays the ``0``
    sentinel and ``registered`` stays false. It becomes real authority only in
    :func:`assign_grant_actor` plus the rules-owned registration.
    """
    existing = get_commission_grant(package.package_id, role_id, definition_key)
    if existing is not None:
        if existing.issuer_key != issuer_key:
            raise ScenePackageConflictError(
                f"commission {definition_key!r} of role {role_id!r} is already "
                "granted under a different issuer key"
            )
        return existing
    try:
        return StoryCommissionGrant.objects.create(
            package=package,
            role_id=role_id,
            npc_id=0,
            definition_key=definition_key,
            issuer_key=issuer_key,
            registered=False,
            updated_tick=tick,
        )
    except IntegrityError as error:
        raise ScenePackageConflictError(
            f"commission {definition_key!r} of role {role_id!r} was granted concurrently"
        ) from error


def assign_grant_actor(
    package: ScenePackage,
    role_id: str,
    definition_key: str,
    npc_id: int,
    *,
    tick: int = 0,
) -> StoryCommissionGrant | None:
    """Bind one planned grant to the exact actor materialized for its role.

    Refuses a different actor for an already-assigned grant, so activation can
    never redirect an authorized commission to another entity, and requires the
    actor to be the exact actor the role binding names, so a grant can never
    authorize an actor no package role owns.
    """
    if not isinstance(npc_id, int) or isinstance(npc_id, bool) or npc_id <= 0:
        raise SceneStoreError("npc_id must be a positive integer")
    binding = get_role_binding(package.package_id, role_id)
    if binding is None or binding.npc_id != npc_id:
        raise SceneStoreError(
            f"role {role_id!r} is not bound to actor {npc_id}; a grant cannot "
            "authorize an unbound actor"
        )
    existing = get_commission_grant(package.package_id, role_id, definition_key)
    if existing is None:
        return None
    if existing.npc_id not in (0, npc_id):
        raise ScenePackageConflictError(
            f"commission {definition_key!r} of role {role_id!r} is already "
            f"assigned to actor {existing.npc_id}"
        )
    if existing.npc_id == 0:
        StoryCommissionGrant.objects.filter(pk=existing.pk).update(
            npc_id=int(npc_id), updated_tick=tick
        )
    return get_commission_grant(package.package_id, role_id, definition_key)


def set_grant_registered(
    package: ScenePackage,
    role_id: str,
    definition_key: str,
    registered: bool,
    *,
    tick: int = 0,
) -> bool:
    """Record whether the grant's issuance is currently registered.

    A grant is registered authority only once its exact actor is assigned: a
    ``registered=True`` write on an unassigned (``npc_id`` zero) grant is
    refused, so the planned-versus-activated boundary cannot be crossed by a
    flag write alone.
    """
    if registered:
        current = get_commission_grant(package.package_id, role_id, definition_key)
        if current is None or current.npc_id <= 0:
            raise SceneStoreError(
                f"commission {definition_key!r} of role {role_id!r} cannot be "
                "registered before its actor is assigned"
            )
    return bool(
        StoryCommissionGrant.objects.filter(
            package=package, role_id=role_id, definition_key=definition_key
        ).update(registered=registered, updated_tick=tick)
    )


