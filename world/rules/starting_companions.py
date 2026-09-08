"""Deterministic builder turning one preset companion declaration into a live NPC.

``build_starting_companion`` resolves a ``StartingCompanion`` declaration and
one owning player into a fully-configured ``LLMNPC`` carrying the attribute set
``world/imports/loader.py::_instantiate_validated_character`` writes and the
values preset-mode ``activate_player_character`` computes, so the companion is
mechanically identical to the player version of the same card. The module's
boundary is exact: it builds NPCs and writes NO player, party, or affinity
state -- seeding the relationship and binding the party are the activation
binding's responsibility, not the builder's.

The module also owns the rules-side import-time sweep over the preset
registry's companion bounds (companion count against ``PARTY_MAX_COMPANIONS``,
affinity against ``NATURAL_CAP``) because ``world/lore/`` must not import
``world/rules/`` and the lore-side validator cannot see those constants -- the
same split the persona prose cap established. Activation lazy-imports this
module inside the bind step, and ``at_server_start`` runs an explicit
``starting_companion_validation`` boot step that imports it, so the sweep is a
server-boot gate, not a test-only side effect.

The builder deliberately owns no transaction of its own, following
``world/rules/guild_exams.py::_spawn_opponent``'s delete-compensation idiom:
a mid-build failure removes the partially built NPC and re-raises. When a
caller (the later activation binding) wraps the call in its own transaction,
the failure degrades to that transaction's rollback instead.
"""

from typing import Any

from django.db import transaction

from evennia.utils.create import create_object

from world.lore.player_presets import PLAYER_PRESET_REGISTRY, PlayerPreset, StartingCompanion
from world.lore.races import SUBRACE_REGISTRY
from world.observability import log_info, log_warn
from world.rules.affinity import NATURAL_CAP, seed_affinity
# The lineage state and portrait finalization are consumed from their sole
# player-activation owners rather than recomposed here, so companion and
# player builds can never drift. ``_preset_lineage_state`` is an intentional
# private-symbol coupling: character_creation is the design's high-churn
# serialization point, and importing its composition beats duplicating it.
from world.rules.character_creation import (
    MAX_PERSONA_FIELD_LENGTH,
    CharacterCreationError,
    _preset_lineage_state,
    finalize_player_portrait,
    resolve_preset_values,
    validate_affinity_seed,
)
from world.rules.equipment import toggle_equipment
from world.rules.party import PARTY_MAX_COMPANIONS, join_party
from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
from world.rules.traits import trait_config_for_values
from typeclasses.npcs import LLMNPC, ensure_npc_canonical_age


class StartingCompanionError(ValueError):
    """A companion build violates the deterministic builder contract."""


def _validate_preset_companion_bounds(registry: dict[str, PlayerPreset]) -> None:
    """Sweep every preset's companion declarations against the rules constants.

    The two bounds read rules-owned numbers -- the party cap and the affinity
    natural ceiling -- so they run here at ``world/rules/`` import time while
    the lore-side validator only sees registry-shape facts. A preset declaring
    more companions than the party can ever hold, or an affinity outside the
    ``1..NATURAL_CAP`` seeding range (booleans excluded, mirroring
    ``seed_affinity``'s discipline), raises naming the offending preset.
    A relationship label longer than the persona prose cap it would be
    injected into (``PersonaStore`` renders connection values as prose) is
    refused the same way.
    """
    for preset in registry.values():
        if len(preset.starting_companions) > PARTY_MAX_COMPANIONS:
            raise StartingCompanionError(
                f"preset {preset.key!r} declares {len(preset.starting_companions)} "
                f"starting companions, more than the party cap {PARTY_MAX_COMPANIONS}"
            )
        for entry in preset.starting_companions:
            if (
                isinstance(entry.affinity, bool)
                or not isinstance(entry.affinity, int)
                or not 1 <= entry.affinity <= NATURAL_CAP
            ):
                raise StartingCompanionError(
                    f"preset {preset.key!r} declares companion affinity "
                    f"{entry.affinity!r} outside 1..{NATURAL_CAP} for "
                    f"{entry.preset_key!r}"
                )
            if len(entry.relationship) > MAX_PERSONA_FIELD_LENGTH:
                raise StartingCompanionError(
                    f"preset {preset.key!r} declares a companion relationship "
                    f"exceeding the {MAX_PERSONA_FIELD_LENGTH}-character persona "
                    f"length cap for {entry.preset_key!r}"
                )


def _key_taken_by_other(entity: Any) -> bool:
    """True when any other persisted entity already carries this display key."""
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(db_key=entity.key).exclude(pk=entity.pk).exists()


def _resolve_affinity_elements(preset: PlayerPreset) -> list[str]:
    """Resolve the companion's affinity set with the player-side elf rule.

    An elf's set is seeded from its subrace -- never from the preset, matching
    the loader's and activation's single-source rule -- while every other race
    persists its own declared set verbatim.
    """
    if preset.race == "elf":
        subrace = SUBRACE_REGISTRY[preset.subrace]
        return list(validate_affinity_seed(subrace.affinity_elements))
    return list(preset.affinity_elements)


def _build_persona_record(preset: PlayerPreset, player: Any, declaration: StartingCompanion) -> dict[str, Any]:
    """The partner preset's own persona record plus the owning-player link.

    The record is ``PresetPersona.to_record()`` exactly as the player version
    of the card would persist it, with one added ``social_connection`` entry
    keyed by the owning player's name holding the declaration's relationship
    label, so the companion knows on arrival whose twin it is.
    """
    record = preset.persona.to_record()
    record["social_connection"][player.key] = declaration.relationship
    return record


def build_starting_companion(player: Any, declaration: StartingCompanion) -> LLMNPC:
    """Build one declared companion as a live ``LLMNPC`` beside ``player``.

    The companion's card is ``PLAYER_PRESET_REGISTRY[declaration.preset_key]``
    -- the same card a player could have chosen -- and every mechanical value
    comes from the shared resolvers the player path uses
    (``resolve_preset_values``, ``_preset_lineage_state``,
    ``toggle_equipment``), so a companion and a player built from one card
    cannot drift. The entity is an ``LLMNPC``, not a plain ``NPC``, because
    ``commands/invite.py`` accepts only an ``LLMNPC`` and a dismissed
    companion must stay re-invitable.

    The NPC's key is the partner preset's display name; when another persisted
    entity already holds it, the key takes the ``-{pk}`` suffix following
    ``guild_exams``'s disambiguation, while the named portrait policy keeps the
    portrait subject pinned to the pk either way. On any failure the partially
    built NPC is deleted and the error re-raised, so a rejected build never
    leaves a persisted half-companion behind.
    """
    preset = PLAYER_PRESET_REGISTRY.get(declaration.preset_key)
    if preset is None:
        # Second, fail-closed gate: the lore-side validator already rejects an
        # unregistered partner at import, so reaching here is a genuine bug.
        raise StartingCompanionError(
            f"companion declaration names unregistered preset "
            f"{declaration.preset_key!r}"
        )
    if player.location is None:
        # Deterministic rejection before any object exists: a companion has no
        # meaningful spawn place without its owner's location.
        raise StartingCompanionError(
            f"player {player.key!r} has no location to spawn a companion at"
        )
    npc = create_object(LLMNPC, key=preset.display_name)
    try:
        npc.race = preset.race
        npc.subrace = preset.subrace
        npc.sex = preset.sex
        npc._apply_trait_config(
            trait_config_for_values(resolve_preset_values(preset))
        )
        npc.db.age = preset.age
        npc.db.apparent_age = preset.apparent_age
        # The disguise layer and sexual baseline mirror the preset-only writes
        # of player activation and the import loader: an empty declaration
        # normalizes to None, an undeclared baseline writes nothing so
        # SexualState keeps its lazy generic default.
        npc.db.disguised_stats = dict(preset.disguised_stats) or None
        if preset.sexual_baseline is not None:
            npc.db.sexual = preset.sexual_baseline.to_record()
        skills_value, proficiency_value = _preset_lineage_state(preset)
        npc.db.skills = skills_value
        npc.db.skill_proficiency = proficiency_value
        npc.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        npc.db.inventory = preset.inventory_list()
        npc.db.affinity_elements = _resolve_affinity_elements(preset)
        npc.db.persona = _build_persona_record(preset, player, declaration)
        # Declared starting equipment is applied through the sole equipment
        # writer, after the inventory write (the toggle preflight requires
        # canonical inventory ownership), exactly like activation. A rejected
        # toggle is a hard failure: the registry validators make one a genuine
        # bug, and skipping it would ship a companion contradicting its card.
        for equipment_key in preset.starting_equipment:
            toggle_result = toggle_equipment(npc, equipment_key)
            if toggle_result.outcome == "rejected":
                raise StartingCompanionError(
                    f"companion starting equipment {equipment_key!r} was "
                    f"rejected: {toggle_result.reason}"
                )
        npc.location = player.location
        # Occupancy check against the whole persisted namespace: display-name
        # uniqueness is not enforced at player activation, so a same-named
        # character is a real possibility and the suffix is the only guard.
        if _key_taken_by_other(npc):
            npc.key = f"{preset.display_name}-{npc.pk}"
        # Canonical age is a no-op here (both values were written from the
        # card) but every existing NPC spawn site calls it, and it keeps the
        # builder honest if a future card ever declares an absent age.
        ensure_npc_canonical_age(npc)
        npc.save()
        # Portrait finalization runs LAST, after the save: with no outer
        # transaction of our own, ``schedule_portrait_ensure``'s on-commit
        # callback would otherwise fire inline mid-build, and a later failure
        # would orphan an already-enqueued portrait. The stable key is the pk,
        # so the ``-{pk}`` suffix above never changes the portrait subject.
        finalize_player_portrait(npc)
        log_info(
            "starting_companion_built",
            context={
                "owner": player.key,
                "preset": preset.key,
                "char": npc.key,
            },
        )
    except Exception:
        try:
            npc.delete()
        except Exception as error:
            log_warn(
                "starting_companion_delete_failed",
                exc=error,
                context={"stage": "build_companion", "obj": str(npc)},
            )
        raise
    return npc


def _discard_built_companions(built: list[LLMNPC]) -> None:
    """Delete every companion built during a failed bind, best-effort.

    The caller's transaction rollback removes the persisted rows; this pass
    clears the in-process objects so no idmapper entry or room contents-cache
    pk outlives the failed activation: ``create_object`` cached each NPC on
    ``post_save`` and Django rollback never flushes the idmapper. Runs both
    inside bind's own except (still in the doomed transaction, where the
    deletes are pure cache eviction) and from activation's except after the
    rollback, when a failure lands AFTER a completed bind (portrait
    finalization, the write observer): without this pass a phantom companion
    with a stale ``party_member`` backref keeps surfacing in ``room.contents``
    until process restart. A companion may already be gone (``join_party``
    restores both surfaces on its own write failure, and the builder deletes
    a half-build), so a failing delete is logged, never raised -- raising
    here would replace the original activation failure. If the delete itself
    dies before Evennia's cache pop (on Postgres an aborted transaction makes
    ``at_object_delete``'s purge raise first; SQLite is unaffected), evict the
    instance directly so the rollback cannot strand it in the idmapper.
    """
    for npc in built:
        try:
            npc.delete()
        except Exception as error:
            try:
                npc.flush_from_cache(force=True)
            except Exception:  # observability: ignore R2: last-ditch eviction of an object that may already be flushed; the original failure is already surfaced
                pass
            log_warn(
                "starting_companion_delete_failed",
                exc=error,
                context={"stage": "bind_companion", "obj": str(npc)},
            )


def bind_starting_companions(player: Any, preset: PlayerPreset) -> list[LLMNPC]:
    """Build, seed, and bind every companion one preset declares (design 10.2).

    Runs inside the caller's ``transaction.atomic()`` (preset activation).
    For each declaration, in registry order: build the NPC, seed its affinity
    toward ``player`` through the sole seed writer at the declared value, and
    bind it through the sole membership writer ``join_party`` -- never by
    touching ``player.db.party`` or ``npc.db.party_member`` directly. The
    ``starting_companion_joined`` event is deferred with ``on_commit`` so a
    rolled-back activation never announces a companion.

    Any failure deletes every NPC built during this call and surfaces as
    ``CharacterCreationError`` (domain errors wrapped with ``from``), so
    activation's own except branch restores the player's snapshotted
    surfaces -- including ``party``, which joined the creation snapshot for
    this window -- and the whole activation rolls back. A companion is never
    best-effort: silently arriving without the twin the card declares would
    contradict the card the player chose.

    Returns the built companions so the caller's rollback path can run
    ``_discard_built_companions`` itself when a LATER activation step fails
    after this binding committed in-transaction.
    """
    party_before = attribute_snapshot(player, "party")
    built: list[LLMNPC] = []
    try:
        for declaration in preset.starting_companions:
            npc = build_starting_companion(player, declaration)
            built.append(npc)
            seed_affinity(npc, player, declaration.affinity)
            join_party(npc, player)
            transaction.on_commit(
                lambda npc=npc, declaration=declaration: log_info(
                    "starting_companion_joined",
                    context={
                        "owner": player.key,
                        "preset": declaration.preset_key,
                        "char": npc.key,
                        "value": declaration.affinity,
                    },
                )
            )
    except Exception as error:
        _discard_built_companions(built)
        restore_attribute_best_effort(player, "party", party_before)
        if isinstance(error, CharacterCreationError):
            raise
        raise CharacterCreationError(
            f"preset {preset.key!r} starting companion binding failed: {error}"
        ) from error
    return built


_validate_preset_companion_bounds(PLAYER_PRESET_REGISTRY)
