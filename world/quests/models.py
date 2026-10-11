"""Normalized persistent scene-package store (design §4, quest-scene-encounters).

The deterministic quest package owns its own durable records directly, exactly
as the sibling packages own theirs (AGENTS.md single-writer boundary). Immutable
published definitions live in :class:`ScenePackage`; mutable role, encounter,
commission and dialogue runtime state lives in the separate `*Runtime` rows so
a restart can never duplicate a binding and a phase revision can never rewrite
a published definition.

Database-enforced uniqueness is the reason these records are Django models
rather than another ``db`` list on the generated-quest Script:

* ``ScenePackage.package_id`` / ``source_id`` -- package and source identity;
* ``StoryRoleBinding`` ``(package, role_id)`` -- one exact actor per role;
* ``SceneEncounterRuntime`` ``(package, scene_id, player_id)`` -- one activation
  identity per scene and player;
* ``StoryRoleDialogueRuntime`` ``(package, role_id)`` -- one selected phase per
  role;
* ``StoryCommissionGrant`` ``(package, role_id, definition_key)`` -- one exact
  authorized commission per role.

No deployed-data migration or backward-compatibility transform is added: this
app's initial migration only declares the fresh schema (design §4).
"""

from django.db import models


class ImmutableScenePackageQuerySet(models.QuerySet):
    """Block rewriting a published package through bulk ORM operations.

    A published package is immutable (design §4): replayed source returns its
    existing version and conflicting content is rejected instead of overwriting
    a materialized persona or history. The store API is the only writer, so the
    aggregate operations that would silently rewrite published definitions are
    refused at the manager, exactly as ``world.narrative.models`` does for its
    immutable accepted records.
    """

    def update(self, *args, **kwargs):
        raise ValueError("Published scene packages are immutable.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Published scene packages are immutable.")

    def delete(self, *args, **kwargs):
        raise ValueError("Published scene packages are immutable.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Published scene packages are immutable.")
        return super().bulk_create(objs, **kwargs)

    def transition_status(self, package_id: str, status: str) -> int:
        """Apply the one documented lifecycle transition: publication status only.

        The published payload, identity and version stay immutable; this narrow,
        store-owned escape hatch exists so ``cancel_package`` can retire an
        unactivated definition without overwriting what was published. The base
        ``update`` is invoked explicitly, so this never re-enters the overridden
        ``update`` above.
        """
        queryset = self.filter(package_id=package_id)
        return models.QuerySet.update(queryset, status=status)


class ScenePackage(models.Model):
    """One immutable published scene package (design §4).

    ``package_id`` is the stable content identity of the package: equal content
    always yields an equal id and different content never collides, so
    reprocessing an identical payload returns the same package. ``source_id`` is
    the optional durable source/decision identity supplied by the publication
    caller; it is database-unique when present, so a later differing payload for
    the same source is rejected instead of overwriting the materialized
    character. ``payload`` holds the validated normalized definitions (roles,
    relationships, initial knowledge, encounters, dialogue phases, and the
    compiled quest definition plus its spawn requirements); ``status`` is the
    publication lifecycle (``published`` or ``cancelled``).
    """

    objects = ImmutableScenePackageQuerySet.as_manager()

    package_id = models.CharField(max_length=128, unique=True)
    source_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    owner_id = models.CharField(max_length=255)
    version = models.BigIntegerField(default=1)
    status = models.CharField(max_length=16, default="published")
    payload = models.JSONField()
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "quests"

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise ValueError("Published scene packages are immutable.")
        return super().save(*args, **kwargs)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"ScenePackage({self.package_id})"


class StoryRoleBinding(models.Model):
    """One package role bound to one exact actual actor (design §4).

    ``(package, role_id)`` is database-unique, so a restart or repeat activation
    can never create a second actor for a role. ``npc_id`` is a database
    identity re-resolved per read -- the row never holds a live object
    reference. ``provenance`` records the materialization decision and
    ``availability`` records the current availability (``bound`` or a named
    unavailable reason) without repairing a departed, dead, or deleted actor.
    """

    package = models.ForeignKey(
        ScenePackage, on_delete=models.CASCADE, related_name="role_bindings"
    )
    role_id = models.CharField(max_length=128)
    npc_id = models.BigIntegerField()
    provenance = models.JSONField(default=dict)
    availability = models.CharField(max_length=32, default="bound")
    updated_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["package", "role_id"], name="quests_unique_role_binding"
            )
        ]


class SceneEncounterRuntime(models.Model):
    """One encounter's activation identity for one player (design §4/§5.2).

    ``(package, scene_id, player_id)`` is database-unique, so repeat activation,
    reconnect, restart and re-entry read the committed state instead of
    creating a duplicate. ``state`` is the closed lifecycle
    (``pending``/``activated``/``cancelled``/``unavailable``); ``reason`` names
    the exact unavailable cause.
    """

    package = models.ForeignKey(
        ScenePackage, on_delete=models.CASCADE, related_name="encounter_runtime"
    )
    scene_id = models.CharField(max_length=128)
    player_id = models.BigIntegerField()
    state = models.CharField(max_length=16, default="pending")
    activation_tick = models.BigIntegerField(null=True, blank=True)
    #: The actual room an instance-layer encounter materialized, so a repeat or
    #: failed-and-retried activation reuses the one room instead of spawning a
    #: second one. ``NULL`` for a permanent anchor/grid encounter.
    room_id = models.BigIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    updated_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["package", "scene_id", "player_id"],
                name="quests_unique_encounter_identity",
            )
        ]


class StoryRoleDialogueRuntime(models.Model):
    """One role's selected dialogue phase and monotonic revision (design §4).

    ``(package, role_id)`` is database-unique. The row is separate from the
    immutable persona and from historical dialogue turns, so a phase change
    never rewrites the character or erases old conversation frames.
    """

    package = models.ForeignKey(
        ScenePackage, on_delete=models.CASCADE, related_name="dialogue_runtime"
    )
    role_id = models.CharField(max_length=128)
    selected_phase = models.CharField(max_length=128)
    revision = models.BigIntegerField(default=0)
    updated_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["package", "role_id"],
                name="quests_unique_role_phase",
            )
        ]


class StoryCommissionGrant(models.Model):
    """One exact authorized commission registered for a provisioned issuer role.

    The grant is the durable bridge between a published symbolic commission
    declaration and an actual runtime registration (design §5.1/§5.2): it keys
    the validated package role, the exact bound actor, and the one definition
    the actor was authorized to offer, so a restart re-registers exactly the
    activated issuance and never fabricates authority for a merely planned
    declaration. ``(package, role_id, definition_key)`` is database-unique.
    """

    package = models.ForeignKey(
        ScenePackage, on_delete=models.CASCADE, related_name="commission_grants"
    )
    role_id = models.CharField(max_length=128)
    npc_id = models.BigIntegerField()
    definition_key = models.CharField(max_length=128)
    issuer_key = models.CharField(max_length=64)
    registered = models.BooleanField(default=False)
    updated_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["package", "role_id", "definition_key"],
                name="quests_unique_commission_grant",
            )
        ]


class ExclusiveOutcomeGroup(models.Model):
    """One owner/package/group's durable exclusive-result state (escort §7).

    A group is identified by ``(owner_id, package_id, group_id)`` and is
    database-unique, so one owner can never hold two competing resolution rows
    for the same declared group and a restart re-reads exactly the committed
    state instead of inventing a second one. Acceptance sequences are allocated
    from ``next_sequence`` under the same serialized write discipline, because
    world tick alone cannot order two acceptances in one tick.
    """

    owner_id = models.BigIntegerField()
    package_id = models.CharField(max_length=128)
    group_id = models.CharField(max_length=128)
    resolved = models.BooleanField(default=False)
    resolution_source = models.CharField(max_length=200, blank=True, default="")
    winner_quest_id = models.CharField(max_length=128, blank=True, default="")
    no_commission = models.BooleanField(default=False)
    next_sequence = models.PositiveIntegerField(default=1)
    updated_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["owner_id", "package_id", "group_id"],
                name="quests_unique_outcome_group",
            )
        ]

    @property
    def unresolved(self) -> bool:
        """Whether this group still admits acceptances and arbitration."""
        return not self.resolved


class EscortEventTransition(models.Model):
    """One consumed ``(owner, record, source)`` escort event identity.

    The one-transition-per-event rule (escort design §6.2/§7): the boundary that
    owns a movement/activation/binding/living-state change builds one stable
    durable source identity and the evaluator inserts a row for it *only when a
    stage advanced or a resolution was attributed*. ``(owner_id, record_id,
    source_key)`` is database-unique, so a pre-follow receive and a post-follow
    recheck cannot advance two stages, and replaying the same settled movement
    after a committed reload advances nothing.
    """

    owner_id = models.BigIntegerField()
    record_id = models.CharField(max_length=128)
    source_key = models.CharField(max_length=200)
    consumed_tick = models.BigIntegerField(default=0)

    class Meta:
        app_label = "quests"
        constraints = [
            models.UniqueConstraint(
                fields=["owner_id", "record_id", "source_key"],
                name="quests_unique_escort_transition",
            )
        ]
