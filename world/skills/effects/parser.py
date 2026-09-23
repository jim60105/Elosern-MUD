"""The single dispatch point parsing effect-ID strings into typed dataclasses.

Part of :mod:`world.skills.effects`; ``parse_effect`` is the leaf module
importing every effect family. The damage-school grammar lives exclusively
in :func:`parse_effect` (skill-effect-model spec).
"""

from math import isfinite

from world.lore.elements import ELEMENT_REGISTRY
from world.skills.effects.combat import (
    CleanseEffect,
    DamageEffect,
    DisengageEffect,
    GaugeTransferEffect,
    HealEffect,
    SelfHealEffect,
)
from world.skills.effects.passives import (
    BuffApplyEffect,
    ConferGrowthRateEffect,
    ConferralEffect,
    DisguiseEffect,
    DivineMysteryEffect,
    FlavorEffect,
    GrowthRateEffect,
    MovementEffect,
    RevealDisguiseEffect,
    RevokeGrantsEffect,
    RuleTableEffect,
    SelfBuffApplyEffect,
    SessionStampEffect,
    SexualMasteryEffect,
    StatMultiplyEffect,
    WeaponStyleEffect,
)
from world.skills.effects.sexual import (
    ActorSexualEventEffect,
    ClampShameEffect,
    ClimaxExtensionStageEffect,
    DivinePleasureMaxEffect,
    MarkSubmissionEffect,
    PairEventEffect,
    PleasureEffect,
    PleasurePeakEffect,
    RestorePurityEffect,
    SaturateSensitivityEffect,
    SexualCounterEffect,
    SexualDrainEffect,
    SexualEventEffect,
    StimulusEffect,
    TargetSexualEventEffect,
)

def _parse_stat_like(effect_id: str, prefix: str) -> tuple[str, float]:
    """Parse a ``prefix:<stat>:<multiplier>`` effect into its pair."""
    _, _, rest = effect_id.partition(":")
    stat, _, multiplier_text = rest.partition(":")
    if not stat or not multiplier_text:
        raise ValueError(
            f"{prefix} effect must be {prefix}:<stat>:<multiplier>, got {effect_id!r}"
        )
    try:
        multiplier = float(multiplier_text)
    except ValueError as error:
        raise ValueError(
            f"{prefix} multiplier must be numeric, got {effect_id!r}"
        ) from error
    if not isfinite(multiplier):
        raise ValueError(
            f"{prefix} multiplier must be finite, got {effect_id!r}"
        )
    return stat, multiplier


def _parse_single_arg(effect_id: str, prefix: str) -> str:
    """Parse a ``prefix:<arg>`` effect into its bare argument."""
    arg = effect_id.partition(":")[2]
    if not arg:
        raise ValueError(f"{prefix} effect requires an argument, got {effect_id!r}")
    if ":" in arg:
        raise ValueError(
            f"{prefix} effect takes exactly one argument, got {effect_id!r}"
        )
    return arg


def _parse_bare(effect_id: str, prefix: str) -> None:
    """Reject any payload on a prefix that declares none."""
    if effect_id != prefix:
        raise ValueError(
            f"{prefix} effect takes no argument, got {effect_id!r}"
        )


def parse_effect(effect_id: str) -> object:
    """Parse one effect-ID string into its typed frozen dataclass.

    Raises ``ValueError`` for any unrecognized prefix or malformed payload, so
    ``SkillDef.__post_init__`` fails at registry construction instead of the
    effect silently doing nothing at use time.
    """
    prefix = effect_id.partition(":")[0]
    if prefix == "stat_multiply":
        trait, multiplier = _parse_stat_like(effect_id, prefix)
        return StatMultiplyEffect(trait=trait, multiplier=multiplier)
    if prefix == "growth_rate":
        parts = effect_id.split(":")
        if len(parts) != 4:
            raise ValueError(
                f"growth_rate effect must be growth_rate:<stat>:<multiplier>:<scope>, "
                f"got {effect_id!r}"
            )
        _, stat, multiplier_text, scope = parts
        if stat != "practice":
            raise ValueError(
                f"growth_rate effect stat must be 'practice', got {stat!r} "
                f"in {effect_id!r} (the retired 'magic' key fails closed)"
            )
        try:
            multiplier = float(multiplier_text)
        except ValueError as error:
            raise ValueError(
                f"growth_rate multiplier must be numeric, got {effect_id!r}"
            ) from error
        if not isfinite(multiplier):
            raise ValueError(
                f"growth_rate multiplier must be finite, got {effect_id!r}"
            )
        if multiplier < 0:
            raise ValueError(
                f"growth_rate multiplier must be non-negative, got {effect_id!r}"
            )
        if scope not in ELEMENT_REGISTRY:
            raise ValueError(
                f"growth_rate scope must be an ELEMENT_REGISTRY key, got {scope!r} "
                f"in {effect_id!r}"
            )
        return GrowthRateEffect(stat=stat, multiplier=multiplier, scope=scope)
    if prefix == "sexual_magic_mastery":
        _parse_bare(effect_id, prefix)
        return SexualMasteryEffect()
    if prefix == "passive_buff":
        return RuleTableEffect(rule_key=_parse_single_arg(effect_id, prefix))
    if prefix == "combat_prediction":
        return RuleTableEffect(rule_key=_parse_single_arg(effect_id, prefix))
    if prefix == "passive_trait":
        return FlavorEffect(name=_parse_single_arg(effect_id, prefix))
    if prefix == "movement":
        mode = _parse_single_arg(effect_id, prefix)
        if mode not in ("flight", "flash_step"):
            raise ValueError(
                f"movement effect mode must be flight or flash_step, got {effect_id!r}"
            )
        return MovementEffect(mode=mode)
    if prefix == "weapon_style":
        return WeaponStyleEffect(style=_parse_single_arg(effect_id, prefix))
    if prefix == "divine_mystery":
        return DivineMysteryEffect(name=_parse_single_arg(effect_id, prefix))
    if prefix == "confer_skill_partial":
        _parse_bare(effect_id, prefix)
        return ConferralEffect()
    if prefix == "set_disguise":
        _parse_bare(effect_id, prefix)
        return DisguiseEffect()
    if prefix == "reveal_disguise":
        _parse_bare(effect_id, prefix)
        return RevealDisguiseEffect()
    if prefix == "buff_apply":
        return BuffApplyEffect(buff_key=_parse_single_arg(effect_id, prefix))
    if prefix == "self_buff_apply":
        return SelfBuffApplyEffect(buff_key=_parse_single_arg(effect_id, prefix))
    if prefix == "session_stamp":
        return SessionStampEffect(key=_parse_single_arg(effect_id, prefix))
    if prefix == "confer_growth_rate":
        _parse_bare(effect_id, prefix)
        return ConferGrowthRateEffect()
    if prefix == "revoke_grants":
        _parse_bare(effect_id, prefix)
        return RevokeGrantsEffect()
    if prefix == "sexual_event":
        return SexualEventEffect(event_name=_parse_single_arg(effect_id, prefix))
    if prefix == "sexual_event_actor":
        return ActorSexualEventEffect(event_name=_parse_single_arg(effect_id, prefix))
    if prefix == "sexual_event_target":
        return TargetSexualEventEffect(event_name=_parse_single_arg(effect_id, prefix))
    if prefix == "pleasure":
        return PleasureEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "sexual_counter":
        return SexualCounterEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "act_pair_event":
        return PairEventEffect(act_key=_parse_single_arg(effect_id, prefix))
    if prefix == "divine_pleasure_max":
        _parse_single_arg(effect_id, prefix)
        return DivinePleasureMaxEffect()
    if prefix == "divine_climax_extension_stage":
        try:
            count = int(_parse_single_arg(effect_id, prefix))
        except ValueError as error:
            raise ValueError(
                f"divine_climax_extension_stage count must be an integer, "
                f"got {effect_id!r}"
            ) from error
        if count < 1:
            raise ValueError(
                f"divine_climax_extension_stage count must be positive, "
                f"got {effect_id!r}"
            )
        return ClimaxExtensionStageEffect(count=count)
    if prefix == "divine_drain":
        _parse_single_arg(effect_id, prefix)
        return SexualDrainEffect()
    if prefix == "divine_saturate_sensitivity":
        _parse_single_arg(effect_id, prefix)
        return SaturateSensitivityEffect()
    if prefix == "divine_clamp_shame":
        _parse_single_arg(effect_id, prefix)
        return ClampShameEffect()
    if prefix == "divine_mark_submission":
        _parse_single_arg(effect_id, prefix)
        return MarkSubmissionEffect()
    if prefix == "divine_restore_purity":
        _parse_single_arg(effect_id, prefix)
        return RestorePurityEffect()
    if prefix == "damage":
        _, _, rest = effect_id.partition(":")
        element, _, school = rest.partition(":")
        if not element or not school or ":" in school:
            raise ValueError(
                f"damage effect must be damage:<element>:<school>, got {effect_id!r}"
            )
        if school not in {"physical", "magic"}:
            raise ValueError(
                f"damage school must be 'physical' or 'magic', got {school!r}"
            )
        return DamageEffect(element=None if element == "none" else element, school=school)
    if prefix == "heal":
        shape = _parse_single_arg(effect_id, prefix)
        if shape not in {"single", "area"}:
            raise ValueError(
                f"heal shape must be 'single' or 'area', got {shape!r}"
            )
        return HealEffect(shape=shape)
    if prefix == "self_heal":
        if effect_id == "self_heal":
            return SelfHealEffect()
        parts = effect_id.split(":")
        if len(parts) == 3 and parts[1] == "missing_fraction":
            try:
                frac_val = float(parts[2])
            except ValueError as error:
                raise ValueError(
                    f"self_heal missing_fraction magnitude must be a number, got {parts[2]!r}"
                ) from error
            return SelfHealEffect(basis="missing_fraction", fraction=frac_val)
        raise ValueError(
            f"self_heal effect must be 'self_heal' or 'self_heal:missing_fraction:<fraction>', got {effect_id!r}"
        )
    if prefix == "disengage":
        return DisengageEffect(mode=_parse_single_arg(effect_id, prefix))
    if prefix == "cleanse":
        scope = _parse_single_arg(effect_id, prefix)
        if scope != "status":
            raise ValueError(
                f"cleanse effect must be cleanse:status, got {effect_id!r}"
            )
        return CleanseEffect(scope=scope)
    if prefix == "stimulus":
        recipient = _parse_single_arg(effect_id, prefix)
        if recipient not in ("actor", "target", "both"):
            raise ValueError(
                f"stimulus effect recipient must be 'actor', 'target', or 'both', got {recipient!r}"
            )
        return StimulusEffect(recipient=recipient)
    if prefix == "pleasure_peak":
        _parse_bare(effect_id, prefix)
        return PleasurePeakEffect()
    if prefix == "gauge_transfer":
        parts = effect_id.split(":")
        if len(parts) < 4:
            raise ValueError(
                f"gauge_transfer effect must have at least 4 segments, got {effect_id!r}"
            )
        _, gauge, direction, mode = parts[:4]
        rest = parts[4:]
        if mode == "fixed":
            if len(rest) != 1:
                raise ValueError(
                    f"gauge_transfer fixed mode requires exactly one magnitude argument, got {effect_id!r}"
                )
            try:
                mag_val = int(rest[0])
            except ValueError as error:
                raise ValueError(
                    f"gauge_transfer fixed magnitude must be an integer, got {rest[0]!r}"
                ) from error
            return GaugeTransferEffect(
                gauge=gauge, direction=direction, magnitude_mode=mode, magnitude=mag_val
            )
        elif mode == "fraction":
            if len(rest) != 1:
                raise ValueError(
                    f"gauge_transfer fraction mode requires exactly one magnitude argument, got {effect_id!r}"
                )
            try:
                frac_val = float(rest[0])
            except ValueError as error:
                raise ValueError(
                    f"gauge_transfer fraction magnitude must be a number, got {rest[0]!r}"
                ) from error
            return GaugeTransferEffect(
                gauge=gauge, direction=direction, magnitude_mode=mode, magnitude=frac_val
            )
        elif mode == "all":
            if rest:
                raise ValueError(
                    f"gauge_transfer 'all' mode takes no magnitude argument, got {effect_id!r}"
                )
            return GaugeTransferEffect(
                gauge=gauge, direction=direction, magnitude_mode=mode, magnitude=None
            )
        else:
            raise ValueError(
                f"gauge_transfer magnitude_mode must be 'fixed', 'fraction', or 'all', got {mode!r} in {effect_id!r}"
            )
    raise ValueError(f"unrecognized skill effect prefix {prefix!r} in {effect_id!r}")
