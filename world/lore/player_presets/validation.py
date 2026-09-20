"""Fail-closed load-time validators for the player-preset registry.

Moved verbatim from the single-module history; each rejects a declaration an
activation could never honour. ``__init__`` runs them over the assembled
registry in the exact order the old module did.
"""

from dataclasses import fields
from math import isfinite
from typing import Any

from world.art.fallback_keys import validate_fallback_key
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.player_presets.vocab import (
    _PERSONA_PROSE_FIELDS,
    PlayerPreset,
    PresetAppearance,
    PresetIdentity,
    PresetPersona,
    PresetSexualBaseline,
    StartingCompanion,
)
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    BODY_PARTS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    GENERIC_BODY_PART,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.lore.starting_kits import validate_wearable_loadout
from world.skills.registry import SKILL_REGISTRY, SkillKind


def _validate_preset_fallback_keys(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared fallback key outside the closed vocabulary.

    Runs at registry construction (import) time like every other preset
    sweep, so an authored typo fails loudly at import rather than silently
    resolving to a nonexistent image.
    """
    for preset in registry.values():
        validate_fallback_key(preset.fallback_key, f"preset {preset.key!r}")

def _validate_preset_identities(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose race/subrace pair could never activate.

    Every preset carries a subrace (no "none" presets exist), so a null,
    unregistered, or race-incompatible subrace raises at import the same way an
    unknown skill kit does.
    """
    for preset in registry.values():
        if preset.race not in RACE_REGISTRY:
            raise ValueError(f"preset {preset.key!r} declares unknown race {preset.race!r}")
        subrace = SUBRACE_REGISTRY.get(preset.subrace)
        if subrace is None:
            raise ValueError(f"preset {preset.key!r} declares unknown subrace {preset.subrace!r}")
        if subrace.race_key != preset.race:
            raise ValueError(
                f"preset {preset.key!r} declares subrace {preset.subrace!r} "
                f"belonging to race {subrace.race_key!r}, not {preset.race!r}"
            )


def _validate_preset_skill_kits(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset kit that could never resolve at activation time.

    Mirrors the skill registry's load-time validation style: an unknown key,
    an active/passive kind mismatch, or a divine-arts skill on a race without
    divine affinity raises at import, so an invalid kit can never reach a
    player's activation.
    """
    for preset in registry.values():
        race = RACE_REGISTRY.get(preset.race)
        for kind_name, expected, keys in (
            ("active", SkillKind.ACTIVE, preset.active_skills),
            ("passive", SkillKind.PASSIVE, preset.passive_skills),
        ):
            for key in keys:
                skill = SKILL_REGISTRY.get(key)
                if skill is None:
                    raise ValueError(f"preset {preset.key!r} declares unknown skill {key!r}")
                if skill.kind is not expected:
                    raise ValueError(
                        f"preset {preset.key!r} declares {key!r} as {kind_name}, "
                        f"but the registry classifies it as {skill.kind.value!r}"
                    )
                if skill.requires_divine_arts and (
                    race is None or not race.can_use_divine_arts
                ):
                    raise ValueError(
                        f"preset {preset.key!r} declares divine-arts skill {key!r} "
                        "on a race without divine affinity"
                    )


def _validate_preset_affinity_elements(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose declared affinity set could never resolve.

    Every key must exist in ``ELEMENT_REGISTRY``, must not repeat, and an elf
    preset SHALL declare an empty set -- an elf's affinity is seeded from its
    subrace at activation, never from the preset (element-affinity-progression
    D3).
    """
    for preset in registry.values():
        seen: set[str] = set()
        for element in preset.affinity_elements:
            if element not in ELEMENT_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares unknown affinity element {element!r}"
                )
            if element in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate affinity element {element!r}"
                )
            seen.add(element)
        if preset.race == "elf" and preset.affinity_elements:
            raise ValueError(
                f"elf preset {preset.key!r} must declare an empty affinity set; "
                "its affinity is seeded from the subrace"
            )


def _validate_preset_starting_items(registry: dict[str, PlayerPreset]) -> None:
    """Reject a starting kit an activation could never hand out.

    Mirrors the skill-kit validator's load-time stance: every item key must
    exist in ``ITEM_REGISTRY``, every quantity must be a positive integer, and
    one key may be declared at most once (extra copies repeat through the
    quantity), so an invalid kit raises at import instead of mid-activation.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.starting_items:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed starting-item entry"
                )
            item_key, quantity = entry
            if item_key not in ITEM_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares unknown item {item_key!r}"
                )
            if item_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate item {item_key!r}"
                )
            seen.add(item_key)
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                raise ValueError(
                    f"preset {preset.key!r} declares a non-positive quantity for {item_key!r}"
                )


def _validate_preset_starting_equipment(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared starting loadout the activation could never wear.

    Mirrors the starting-item validator's load-time stance: every declaration
    is an authoring contract whose runtime alternative is silent corruption,
    because ``world/rules/equipment.py::toggle_equipment`` TOGGLES rather than
    equips (a repeated key would equip then unequip), silently replaces a
    singleton occupant, and rejects a sixth accessory at runtime. So the
    subset rule and the wearable-set arithmetic (duplicates, the
    equipment-slot rule, singleton-slot collisions, accessory overflow) all
    raise at import instead of mid-activation. The wearable-set rules are the
    shared helper's (custom-kit-worn-at-activation D3) — the same arithmetic
    ``_validate_starting_kit`` runs on subrace kits once custom activation
    wears them — keeping the five-rule contract this validator declares
    observable through identical stable messages AND per-key error precedence:
    the malformed-entry and subset guards stay here (preset-specific) and run
    as the helper's per-entry guard, so one key's subset error still precedes
    a later key's duplicate error exactly as the original inline loop ordered
    them.
    """
    for preset in registry.values():
        # Defensive shape check: the starting-items validator already rejects
        # a malformed kit at import, but this validator must name the preset
        # rather than crash on tuple unpacking when driven directly.
        carried: set[str] = set()
        for entry in preset.starting_items:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed starting-item entry"
                )
            carried.add(entry[0])

        def check_entry(
            item_key: str, carried: set[str] = carried, key: str = preset.key
        ) -> None:
            if not isinstance(item_key, str) or not item_key:
                raise ValueError(
                    f"preset {key!r} declares a malformed starting-equipment entry"
                )
            if item_key not in carried:
                raise ValueError(
                    f"preset {key!r} declares starting equipment {item_key!r} "
                    "absent from its starting_items"
                )

        validate_wearable_loadout(
            preset.starting_equipment,
            owner=f"preset {preset.key!r}",
            declaration="starting equipment",
            pre_entry=check_entry,
        )


def _validate_preset_sex(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose declared sex is outside the canonical vocabulary.

    Mirrors the identity validator's load-time stance: ``sex`` must be an
    exact ``SEX_VALUES`` member, so a mistyped card raises at import instead
    of shipping a value the sexual-state model, dialogue prompts, and namegen
    would later consume as the character's sex.
    """
    for preset in registry.values():
        if preset.sex not in SEX_VALUES:
            raise ValueError(
                f"preset {preset.key!r} declares unknown sex {preset.sex!r}"
            )


def _validate_preset_personas(registry: dict[str, PlayerPreset]) -> None:
    """Reject a persona that could never persist or render as an import-card record.

    Mirrors the other preset validators' load-time stance: a non-string prose
    value (including the identity layers and appearance sub-keys), a
    non-``PresetIdentity`` identity, a non-``PresetAppearance`` appearance, or
    a ``social_connection`` entry that is not a pair of strings raises at
    import, so a malformed persona can never reach a player's activation.
    Empty values are always legal so a card can be authored incrementally, and
    duplicate ``social_connection`` names are rejected because the stored
    name -> relationship mapping would silently drop the earlier pair. The
    prose length bound is NOT checked here -- ``world/lore/`` must not import
    ``world/rules/``, so ``world/rules/character_creation`` sweeps that bound
    at its own import (field-parity design 3.1).
    """
    for preset in registry.values():
        persona = preset.persona
        if not isinstance(persona, PresetPersona):
            raise ValueError(
                f"preset {preset.key!r} declares a persona that is not a PresetPersona"
            )
        for field in _PERSONA_PROSE_FIELDS:
            if not isinstance(getattr(persona, field), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.{field} that is not text"
                )
        identity = persona.identity
        if not isinstance(identity, PresetIdentity):
            raise ValueError(
                f"preset {preset.key!r} declares persona.identity that is not a "
                "PresetIdentity"
            )
        for layer in ("public", "hidden"):
            if not isinstance(getattr(identity, layer), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.identity.{layer} "
                    "that is not text"
                )
        appearance = persona.appearance
        if not isinstance(appearance, PresetAppearance):
            raise ValueError(
                f"preset {preset.key!r} declares persona.appearance that is not a "
                "PresetAppearance"
            )
        for sub_field in fields(PresetAppearance):
            if not isinstance(getattr(appearance, sub_field.name), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.appearance."
                    f"{sub_field.name} that is not text"
                )
        seen_names: set[str] = set()
        for entry in persona.social_connection:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not all(isinstance(part, str) for part in entry)
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a social_connection entry that "
                    "is not a (name, relationship) pair of strings"
                )
            name, _relationship = entry
            if name in seen_names:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate social_connection "
                    f"name {name!r}"
                )
            seen_names.add(name)


def _validate_preset_skill_proficiency(registry: dict[str, PlayerPreset]) -> None:
    """Reject declared practice XP an activation could never apply.

    Mirrors the other preset validators' load-time stance and the raw-record
    check the import validator performs: every ``skill_proficiency`` key must
    exist in ``SKILL_REGISTRY``, may appear at most once (a repeat would let
    ``dict()`` silently drop the earlier entry), and its value must be a
    finite non-negative number -- a boolean is rejected as non-numeric and a
    NaN/Infinity never reaches the seed arithmetic. An invalid entry raises at
    import naming the preset and the key, so it can never reach activation.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.skill_proficiency:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed skill_proficiency entry"
                )
            skill_key, value = entry
            if skill_key not in SKILL_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares proficiency for unknown "
                    f"skill {skill_key!r}"
                )
            if skill_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate proficiency for "
                    f"{skill_key!r}"
                )
            seen.add(skill_key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a non-numeric or negative "
                    f"proficiency for {skill_key!r}"
                )


def _validate_preset_disguised_stats(registry: dict[str, PlayerPreset]) -> None:
    """Reject a disguise layer an activation could never persist sanely.

    Mirrors the other preset validators' load-time stance: every
    ``disguised_stats`` entry must be a ``(key, value)`` pair with a string
    axis key and an exact ``int`` value (a boolean is rejected as
    non-numeric). There is deliberately NO axis whitelist --
    ``CHARACTER_SCHEMA_V1`` constrains the field only to integer values,
    and the layer is display-only per ``get_display_value``. A duplicate
    key is rejected because ``dict()`` would silently drop the earlier
    entry, the same reason the proficiency validator rejects repeats.

    A non-empty declaration also requires the preset's race to be able to use
    divine arts, mirroring ``_validate_preset_skill_kits``'s stance for
    divine-arts skill ownership: only the bloodline-gated veil verb can place
    a disguise layer, so a non-divine or unresolved race may never carry one.
    """
    for preset in registry.values():
        if preset.disguised_stats:
            race = RACE_REGISTRY.get(preset.race)
            if race is None or not race.can_use_divine_arts:
                raise ValueError(
                    f"preset {preset.key!r} declares disguised_stats "
                    "on a race without divine affinity"
                )
        seen: set[str] = set()
        for entry in preset.disguised_stats:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed disguised_stats entry"
                )
            axis_key, value = entry
            if not isinstance(axis_key, str):
                raise ValueError(
                    f"preset {preset.key!r} declares a disguised_stats key that "
                    "is not text"
                )
            if axis_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate disguised_stats "
                    f"key {axis_key!r}"
                )
            seen.add(axis_key)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"preset {preset.key!r} declares a non-integer disguise "
                    f"value for {axis_key!r}"
                )


def _validate_preset_sexual_baselines(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared sexual baseline the handler could never build from.

    Mirrors the other preset validators' load-time stance: ``None`` (no
    declaration) always passes; otherwise the value must be a
    ``PresetSexualBaseline`` whose ``arousal`` and every optional level are
    members of the matching vocabulary tuple in
    ``world/lore/sexual_vocab.py``, whose ``virgin`` is an exact boolean,
    and whose ``sensitivity`` entries are ``(body_part, level)`` pairs with
    the part in ``BODY_PARTS`` plus ``GENERIC_BODY_PART`` and the level in
    ``SENSITIVITY_LEVELS``. Empty optional levels are legal -- they are
    omitted from ``to_record()`` so the builder floors them -- everything
    else raises at import naming the field, so a card can never reach
    activation with a value the builder's ``OrderedLevelTrait`` would
    reject.
    """
    vocabularies = {
        "arousal": AROUSAL_LEVELS,
        "wetness": WETNESS_LEVELS,
        "shame": SHAME_LEVELS,
        "exposure": EXPOSURE_LEVELS,
        "climax_phase": CLIMAX_PHASE_LEVELS,
    }
    valid_parts = (*BODY_PARTS, GENERIC_BODY_PART)
    for preset in registry.values():
        baseline = preset.sexual_baseline
        if baseline is None:
            continue
        if not isinstance(baseline, PresetSexualBaseline):
            raise ValueError(
                f"preset {preset.key!r} declares a sexual_baseline that is not a "
                "PresetSexualBaseline"
            )
        if not isinstance(baseline.virgin, bool):
            raise ValueError(
                f"preset {preset.key!r} declares a sexual_baseline.virgin that is "
                "not a boolean"
            )
        for field, vocabulary in vocabularies.items():
            level = getattr(baseline, field)
            if not isinstance(level, str):
                raise ValueError(
                    f"preset {preset.key!r} declares sexual_baseline.{field} that "
                    "is not text"
                )
            # Only the four OPTIONAL levels may be empty (to_record() omits
            # them so the builder floors them); required ``arousal`` is
            # always emitted, so an empty arousal would reach the pleasure
            # band lookup and raise there instead of at load.
            empty_allowed = field != "arousal"
            if level not in vocabulary and not (empty_allowed and level == ""):
                raise ValueError(
                    f"preset {preset.key!r} declares sexual_baseline.{field} "
                    f"{level!r} outside its vocabulary"
                )
        seen_parts: set[str] = set()
        for entry in baseline.sensitivity:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not isinstance(entry[1], str)
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a sensitivity entry that is "
                    "not a (body_part, level) pair of strings"
                )
            part, level = entry
            if part not in valid_parts:
                raise ValueError(
                    f"preset {preset.key!r} declares sensitivity for unknown "
                    f"body part {part!r}"
                )
            if part in seen_parts:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate sensitivity for "
                    f"body part {part!r}"
                )
            seen_parts.add(part)
            if level not in SENSITIVITY_LEVELS:
                raise ValueError(
                    f"preset {preset.key!r} declares sensitivity level {level!r} "
                    f"for {part!r} outside its vocabulary"
                )


def _validate_preset_starting_companions(registry: dict[str, PlayerPreset]) -> None:
    """Reject a companion declaration an activation could never resolve.

    Mirrors the starting-item validator's load-time stance: every entry must
    be a ``StartingCompanion``, its ``preset_key`` must name a registered card
    (the companion IS that card), a preset may never name itself, and one
    preset may name a given partner at most once. The numeric bounds that read
    rules constants (``PARTY_MAX_COMPANIONS``, ``NATURAL_CAP``) cannot live
    here because lore must not import rules, so they are swept at
    ``world/rules/starting_companions.py`` import time instead -- the same
    split the persona prose cap established.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.starting_companions:
            if not isinstance(entry, StartingCompanion):
                raise ValueError(
                    f"preset {preset.key!r} declares a starting companion "
                    f"that is not a StartingCompanion"
                )
            if entry.preset_key not in registry:
                raise ValueError(
                    f"preset {preset.key!r} declares companion preset "
                    f"{entry.preset_key!r} that is not registered"
                )
            if entry.preset_key == preset.key:
                raise ValueError(
                    f"preset {preset.key!r} declares itself as its own companion"
                )
            if entry.preset_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares companion "
                    f"{entry.preset_key!r} more than once"
                )
            seen.add(entry.preset_key)
