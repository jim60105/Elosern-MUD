"""Declarative phase transition and outcome reactions (light-climax-empowerment D2).

Consumes load_rules and evaluate_condition from world.rules.rulebook.schema
without inventing a new language or event bus. Two dispatchers share the rule
list with disjoint action ownership:

* ``dispatch_phase_reaction`` runs once after a successful canonical
  ``_apply_climax_phase_set`` edge and executes the ``apply_buff`` /
  ``remove_buff`` actions of field-conditioned phase rules.
* ``dispatch_outcome_reaction`` runs on named outcome events (``hp_loss``,
  ``negative_buff_added``) and executes only the ``pleasure_gain`` action of
  event-conditioned rules; buff actions belong to the phase dispatcher.
"""

from pathlib import Path
from collections.abc import Mapping
from fractions import Fraction
import math
from typing import Any

from world.rules.rulebook.schema import Rule, evaluate_condition, load_rules
from world.rules.phase_hooks import register_phase_dispatcher

_RULES_PATH = Path(__file__).parent / "rulebook" / "state_reactions.yaml"

_RECOGNIZED_EVENT_VALUES = frozenset(
    {"hp_loss", "mp_zero", "negative_buff_added", "physical_hit"}
)

_RECOGNIZED_WHEN_KEYS = frozenset(
    {
        "field",
        "equals",
        "gte",
        "event",
        "skill_qualified",
        "skill_owned",
        "buff_active",
        "field_changed",
        "direction",
        "dual_wielding",
        "equipment_worn",
        "event_source_skill",
    }
)


def validate_state_reaction_rules(rules: list[Rule]) -> None:
    """Fail closed at load time on structurally invalid or unsupported rules."""
    from world.rules.buffs import BUFF_DEFINITIONS

    seen_empowerment_markers: set[str] = set()

    for rule in rules:
        if "event" in rule.when:
            event_val = rule.when["event"]
            if (
                isinstance(event_val, bool)
                or not isinstance(event_val, str)
                or event_val not in _RECOGNIZED_EVENT_VALUES
            ):
                raise ValueError(
                    f"state reaction rule {rule.id!r} has unrecognized or invalid event {event_val!r}; "
                    f"must be one of {sorted(_RECOGNIZED_EVENT_VALUES)}"
                )

        if "event_source_skill" in rule.when:
            if "event" not in rule.when:
                raise ValueError(
                    f"state reaction rule {rule.id!r} declares event_source_skill without an event condition"
                )
            expected = rule.when["event_source_skill"]
            if isinstance(expected, bool) or not isinstance(expected, str) or not expected.strip():
                raise ValueError(
                    f"state reaction rule {rule.id!r} event_source_skill must be a non-empty string, got {expected!r}"
                )

        unknown_when = set(rule.when) - _RECOGNIZED_WHEN_KEYS
        if unknown_when:
            raise ValueError(
                f"state reaction rule {rule.id!r} has unrecognized when condition: {sorted(unknown_when)[0]!r}"
            )

        then_keys = set(rule.then)
        if then_keys not in (
            {"apply_buff"},
            {"remove_buff"},
            {"pleasure_gain"},
            {"counter_damage"},
            {"apply_buff_to_source"},
            {"mark_order_op"},
        ):
            raise ValueError(
                f"state reaction rule {rule.id!r} then clause must declare exactly one of "
                f"'apply_buff', 'remove_buff', 'pleasure_gain', 'counter_damage', 'apply_buff_to_source', or 'mark_order_op', "
                f"got {sorted(then_keys)!r}"
            )

        action_key = next(iter(then_keys))
        if action_key in ("apply_buff", "remove_buff"):
            buff_key = rule.then[action_key]
            if isinstance(buff_key, bool) or not isinstance(buff_key, str) or not buff_key.strip():
                raise ValueError(
                    f"state reaction rule {rule.id!r} {action_key} value must be a non-empty string, got {buff_key!r}"
                )

            if buff_key not in BUFF_DEFINITIONS:
                raise ValueError(
                    f"state reaction rule {rule.id!r} references unknown buff definition {buff_key!r}"
                )

            if action_key == "apply_buff":
                if buff_key in seen_empowerment_markers:
                    raise ValueError(
                        f"multiple state reaction rules declare apply_buff for marker {buff_key!r}"
                    )
                seen_empowerment_markers.add(buff_key)
        elif action_key == "counter_damage":
            coeff = rule.then["counter_damage"]
            if (
                isinstance(coeff, bool)
                or not isinstance(coeff, (int, float))
                or not math.isfinite(coeff)
                or coeff <= 0
            ):
                raise ValueError(
                    f"state reaction rule {rule.id!r} counter_damage must be a finite positive number, got {coeff!r}"
                )
        elif action_key == "apply_buff_to_source":
            buff_key = rule.then["apply_buff_to_source"]
            if (
                isinstance(buff_key, bool)
                or not isinstance(buff_key, str)
                or not buff_key.strip()
            ):
                raise ValueError(
                    f"state reaction rule {rule.id!r} apply_buff_to_source value must be a non-empty string, got {buff_key!r}"
                )
            if buff_key not in BUFF_DEFINITIONS:
                raise ValueError(
                    f"state reaction rule {rule.id!r} references unknown buff definition {buff_key!r}"
                )
        elif action_key == "mark_order_op":
            buff_key = rule.then["mark_order_op"]
            if (
                isinstance(buff_key, bool)
                or not isinstance(buff_key, str)
                or not buff_key.strip()
            ):
                raise ValueError(
                    f"state reaction rule {rule.id!r} mark_order_op value must be a non-empty string, got {buff_key!r}"
                )
            if buff_key not in BUFF_DEFINITIONS:
                raise ValueError(
                    f"state reaction rule {rule.id!r} references unknown buff definition {buff_key!r}"
                )
            defn = BUFF_DEFINITIONS[buff_key]
            if not getattr(defn, "round_order", None):
                raise ValueError(
                    f"state reaction rule {rule.id!r} references buff definition {buff_key!r} which does not declare round_order"
                )
        elif action_key == "pleasure_gain":
            gain_val = rule.then["pleasure_gain"]
            if isinstance(gain_val, bool):
                raise ValueError(
                    f"state reaction rule {rule.id!r} pleasure_gain must not be a boolean, got {gain_val!r}"
                )
            if isinstance(gain_val, int):
                if gain_val < 0:
                    raise ValueError(
                        f"state reaction rule {rule.id!r} pleasure_gain integer must be non-negative, got {gain_val}"
                    )
            elif isinstance(gain_val, dict):
                # Loadable gain mappings (light-masochism repricing D1/D3):
                # {"max_hp_coefficient": c} for loss-proportional gains and
                # {"max_hp_coefficient": c, "flat_max_hp_fraction": f} for
                # no-loss negative instances. The retired source-tier-keyed
                # mapping is rejected fail-closed so it cannot be authored
                # back in by accident.
                if not gain_val:
                    raise ValueError(
                        f"state reaction rule {rule.id!r} pleasure_gain mapping must not be empty"
                    )
                unknown = set(gain_val) - {
                    "max_hp_coefficient",
                    "flat_max_hp_fraction",
                }
                if unknown:
                    raise ValueError(
                        f"state reaction rule {rule.id!r} pleasure_gain mapping key {sorted(unknown)[0]!r} is not recognized; "
                        f"the retired source-tier mapping is no longer loadable, use 'max_hp_coefficient' "
                        f"with an optional 'flat_max_hp_fraction'"
                    )
                coeff = gain_val.get("max_hp_coefficient")
                if (
                    isinstance(coeff, bool)
                    or not isinstance(coeff, (int, float))
                    or not math.isfinite(coeff)
                    or coeff <= 0
                ):
                    raise ValueError(
                        f"state reaction rule {rule.id!r} pleasure_gain max_hp_coefficient must be a finite positive number, got {coeff!r}"
                    )
                if "flat_max_hp_fraction" in gain_val:
                    fraction = gain_val["flat_max_hp_fraction"]
                    if (
                        isinstance(fraction, bool)
                        or not isinstance(fraction, (int, float))
                        or not math.isfinite(fraction)
                        or not (0 < fraction < 1)
                    ):
                        raise ValueError(
                            f"state reaction rule {rule.id!r} pleasure_gain flat_max_hp_fraction must be a finite number between 0 and 1, got {fraction!r}"
                        )
            else:
                raise ValueError(
                    f"state reaction rule {rule.id!r} pleasure_gain must be a non-negative integer or a "
                    f"'max_hp_coefficient' mapping, got {type(gain_val).__name__}"
                )


def load_state_reaction_rules(path: Path | None = None) -> list[Rule]:
    """Load and validate declarative state reaction rules from YAML."""
    rule_path = path or _RULES_PATH
    rules = load_rules(rule_path)
    validate_state_reaction_rules(rules)
    return rules


STATE_REACTION_RULES: list[Rule] = load_state_reaction_rules()


def get_marker_qualification(
    marker: str, rules: list[Rule] | None = None
) -> str | None:
    """Return the qualifying skill key declared for this marker, or None."""
    active_rules = rules if rules is not None else STATE_REACTION_RULES
    qualifying_skills: list[str] = []
    for rule in active_rules:
        if rule.then.get("apply_buff") == marker:
            skill = rule.when.get("skill_qualified")
            if isinstance(skill, str):
                qualifying_skills.append(skill)
    if len(qualifying_skills) > 1:
        raise ValueError(
            f"marker {marker!r} is declared with conflicting qualifying skills: {qualifying_skills}"
        )
    return qualifying_skills[0] if qualifying_skills else None


def is_configured_marker(marker: str, rules: list[Rule] | None = None) -> bool:
    """Return whether marker is a known buff or declared state reaction marker."""
    from world.rules.buffs import BUFF_DEFINITIONS

    if marker in BUFF_DEFINITIONS:
        return True
    active_rules = rules if rules is not None else STATE_REACTION_RULES
    return any(rule.then.get("apply_buff") == marker for rule in active_rules)


def is_empowered(actor: Any, marker: str, rules: list[Rule] | None = None) -> bool:
    """Check if actor holds the marker buff and currently satisfies qualification.

    Uses active_buff_keys_from_storage to guarantee preview and preflight reads
    remain side-effect-free (no materializing actor.buffs). If qualification was
    lost mid-cycle, returns False immediately without active writes on reads.
    """
    from world.rules.buffs import active_buff_keys_from_storage

    active_keys = active_buff_keys_from_storage(actor)
    if marker not in active_keys:
        return False

    skill_key = get_marker_qualification(marker, rules)
    if skill_key is not None:
        from world.rules.progression import can_use_skill
        from world.skills.registry import SKILL_REGISTRY

        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            return False

        skills_handler = getattr(actor, "skills", None)
        if skills_handler is None:
            return False

        owned_keys = set(skills_handler.owned_keys())
        if skill.key not in owned_keys or not can_use_skill(actor, skill):
            return False

    return True


def compute_state_magnitude(magnitude: Any, entity: Any, actor: Any | None = None) -> float:
    """Interpret one declared ``StateMagnitude`` against live entity state.

    The runtime-rule half of state-derived magnitude: sampling stored
    arousal/effective-exposure state and consulting empowerment lives here,
    on the rules side. ``world.skills.effects.StateMagnitude`` keeps only the
    declarative fields and pure shape validation, so the definition module
    never reaches into rules or the persistent attribute handler.
    """
    from math import isfinite

    from world.lore.sexual_vocab import AROUSAL_LEVELS, EXPOSURE_LEVELS
    from world.rules.equipment_effects import effective_exposure
    from world.rules.stored_sexual_reads import StoredLevel
    from world.rules.sexual_state import PLEASURE_CONFIG

    empowerment_actor = actor if actor is not None else entity
    if magnitude.marker is not None and is_empowered(empowerment_actor, magnitude.marker):
        if magnitude.maximum is not None:
            if not isfinite(magnitude.maximum) or magnitude.maximum <= 0:
                raise ValueError(
                    f"StateMagnitude maximum must be positive, got {magnitude.maximum}"
                )
            return float(magnitude.maximum)

    field_name = "effective_exposure" if magnitude.field == "exposure" else magnitude.field
    ordinal = 0

    if field_name == "arousal":
        sexual = getattr(entity, "__dict__", {}).get("sexual")
        if sexual is not None:
            ordinal = sexual.arousal.value
        else:
            traits = (
                entity.attributes.get("sexual_traits", default=None, category="traits")
                if hasattr(entity, "attributes")
                else None
            )
            if isinstance(traits, Mapping) and "pleasure" in traits:
                raw = traits["pleasure"]
                base = raw.get("base") if isinstance(raw, Mapping) else None
                if isinstance(base, int) and not isinstance(base, bool):
                    base = min(100, max(0, base))
                    ordinal = PLEASURE_CONFIG.ordinal_for(base)
            else:
                baseline = (
                    entity.attributes.get("sexual", default=None)
                    if hasattr(entity, "attributes")
                    else None
                )
                if isinstance(baseline, Mapping) and "arousal" in baseline:
                    val = baseline["arousal"]
                    if val in AROUSAL_LEVELS:
                        ordinal = AROUSAL_LEVELS.index(val)
    elif field_name == "effective_exposure":
        eff = effective_exposure(entity)
        if isinstance(eff, StoredLevel):
            ordinal = eff.value
        elif isinstance(eff, str) and eff in EXPOSURE_LEVELS:
            ordinal = EXPOSURE_LEVELS.index(eff)

    val = magnitude.base + magnitude.per_ordinal * ordinal
    if magnitude.maximum is not None:
        val = min(val, magnitude.maximum)
    if (
        not isfinite(val)
        or val < 0
        or (magnitude.base > 0 and val <= 0)
    ):
        raise ValueError(
            f"StateMagnitude computed non-positive or non-finite value: {val}"
        )
    return float(val)


def validate_skill_markers(registry: dict[str, Any] | None = None) -> None:
    """Fail closed when a shipped skill declares an unconfigured marker.

    The configured-marker vocabulary is owned here (buff definitions plus
    declared reaction rules), so the check runs on the rules side at load:
    ``world.skills`` validates marker *shape* only, and the authority that
    knows which markers exist rejects unresolved ones — never from the
    definition module, which would force a skills→rules import.
    """
    if registry is None:
        from world.skills.registry import SKILL_REGISTRY

        registry = SKILL_REGISTRY
    for skill_key, skill in registry.items():
        for policy in skill.effect_policies:
            for mag in (policy.magnitude, policy.stimulus_bonus):
                if mag is not None and mag.marker is not None:
                    if not is_configured_marker(mag.marker):
                        raise ValueError(
                            f"skill {skill_key!r} declares unresolved configured "
                            f"marker {mag.marker!r}"
                        )


validate_skill_markers()


def dispatch_phase_reaction(
    entity: Any,
    from_phase: str,
    to_phase: str,
    rules: list[Rule] | None = None,
) -> None:
    """Dispatch phase transition reactions once after canonical climax phase changes.

    Callers must execute inside a buffs-snapshotting transaction to preserve
    all-or-nothing settlement when a reaction applies or removes a marker.
    Context provides: entity, field (climax_phase), from_phase, to_phase,
    climax_phase (to_phase), and active_buffs.
    """
    if not hasattr(entity, "attributes"):
        return

    from world.rules.buffs import active_buff_keys_from_storage

    active_rules = rules if rules is not None else STATE_REACTION_RULES
    context = {
        "entity": entity,
        "field": "climax_phase",
        "climax_phase": to_phase,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "active_buffs": active_buff_keys_from_storage(entity),
    }

    for rule in active_rules:
        if evaluate_condition(rule.when, context):
            from world.rules.buffs import apply_buff, remove_by_selector

            if "apply_buff" in rule.then:
                apply_buff(entity, rule.then["apply_buff"])
            elif "remove_buff" in rule.then:
                remove_by_selector(entity, rule.then["remove_buff"])


def _read_max_hp(entity: Any) -> Fraction | None:
    """Read the recipient's maximum HP through the damage pipeline accessor.

    Returns ``None`` — never raises — when the maximum is unreadable, zero or
    negative, so a state reaction on a malformed entity is a silent no-op
    instead of an exception aborting a damage settlement mid-transaction
    (design D4).
    """
    try:
        from world.rules.combat import _max_hp

        max_hp = _max_hp(entity)
    except (AttributeError, KeyError, TypeError):
        return None
    if not (isinstance(max_hp, (int, float)) and max_hp > 0):
        return None
    return Fraction(max_hp)


def _resolve_pleasure_gain(
    entity: Any, rule: Rule, hp_loss_amount: int | None
) -> int:
    """Resolve one authored ``pleasure_gain`` into a whole number of pleasure.

    Three loadable shapes:
    - a plain non-negative integer: a flat gain used verbatim;
    - ``{"max_hp_coefficient": c}``: ``floor(c * hp_loss_amount / max_hp)``,
      the loss-proportional shape (design D1);
    - ``{"max_hp_coefficient": c, "flat_max_hp_fraction": f}``:
      ``floor(c * f)``, the no-loss negative-instance shape (design D3).

    Every indeterminate case — a loss-fraction shape with no loss amount, an
    unreadable or non-positive maximum HP, or any other mapping — yields ``0``
    rather than a guessed number: the same fail-closed posture the dispatcher
    already keeps for a missing handler on a malformed entity (design D2/D4).
    The derivation runs on exact rational arithmetic so ``floor`` can never
    undershoot an exact integer through float rounding.
    """
    gain_spec = rule.then["pleasure_gain"]
    if isinstance(gain_spec, int):
        return gain_spec
    if not isinstance(gain_spec, dict):
        return 0
    coefficient = gain_spec.get("max_hp_coefficient")
    if isinstance(coefficient, bool) or not isinstance(coefficient, (int, float)):
        return 0
    if "flat_max_hp_fraction" in gain_spec:
        flat = gain_spec["flat_max_hp_fraction"]
        if isinstance(flat, bool) or not isinstance(flat, (int, float)):
            return 0
        fraction = Fraction(flat)
    else:
        if hp_loss_amount is None or hp_loss_amount <= 0:
            return 0
        max_hp = _read_max_hp(entity)
        if max_hp is None:
            return 0
        fraction = Fraction(hp_loss_amount) / max_hp
    gain = Fraction(coefficient) * fraction
    if gain <= 0:
        return 0
    return gain.numerator // gain.denominator


def dispatch_outcome_reaction(
    entity: Any,
    event: str,
    source_tier: str | None = None,
    rules: list[Rule] | None = None,
    source_skill: str | None = None,
    *,
    source: Any = None,
    nonlethal: bool = False,
    nonlethal_keys: frozenset[str] = frozenset(),
    battlefield: Any = None,
    is_counter: bool = False,
    hp_loss_amount: int | None = None,
) -> None:
    """Dispatch outcome reactions (hp_loss, mp_zero, negative_buff_added, physical_hit).

    Context provides: entity, event, active_buffs, sexual fields (climax_phase, arousal),
    source_skill, source (for source-targeted reactions), and hp_loss_amount
    (the event's positive actual HP loss, when the caller knows it — it also
    rides the context, so future when-conditions may author against it).
    A pleasure_gain action resolves the gain from the rule's authored shape —
    a flat integer, or the loss fraction of maximum HP for ``hp_loss`` — and
    calls the canonical apply_pleasure_gain; the gain never reads the source's
    tier, school or spell-or-not nature.

    Only event-conditioned rules are considered: the buff actions of
    field-conditioned phase rules belong to ``dispatch_phase_reaction`` and
    must never fire from an outcome dispatch.
    """
    if not hasattr(entity, "attributes"):
        return

    from world.rules.buffs import active_buff_keys_from_storage

    active_rules = rules if rules is not None else STATE_REACTION_RULES
    skill_key = getattr(source_skill, "key", source_skill)
    context: dict[str, Any] = {
        "entity": entity,
        "event": event,
        "active_buffs": active_buff_keys_from_storage(entity),
        "source_skill": skill_key,
        "source": source,
        "hp_loss_amount": hp_loss_amount,
    }

    sexual = getattr(entity, "sexual", None)
    if sexual is not None:
        context["climax_phase"] = getattr(sexual.climax_phase, "level", str(sexual.climax_phase))
        context["arousal"] = getattr(sexual.arousal, "level", str(sexual.arousal))
    else:
        from world.rules.stored_sexual_reads import stored_sexual_level

        cp = stored_sexual_level(entity, "climax_phase")
        if cp is not None:
            context["climax_phase"] = getattr(cp, "level", str(cp))
        ar = stored_sexual_level(entity, "arousal")
        if ar is not None:
            context["arousal"] = getattr(ar, "level", str(ar))

    for rule in active_rules:
        if "event" not in rule.when:
            continue
        if evaluate_condition(rule.when, context):
            if "apply_buff" in rule.then:
                from world.rules.buffs import apply_buff

                kwargs: dict[str, Any] = {}
                if skill_key is not None:
                    kwargs["source_skill"] = skill_key
                if source_tier is not None:
                    kwargs["source_tier"] = source_tier
                apply_buff(entity, rule.then["apply_buff"], **kwargs)
            elif "remove_buff" in rule.then:
                from world.rules.buffs import remove_by_selector

                remove_by_selector(entity, rule.then["remove_buff"])
            elif "pleasure_gain" in rule.then:
                from world.rules.pleasure import apply_pleasure_gain

                gain = _resolve_pleasure_gain(entity, rule, hp_loss_amount)
                if gain > 0:
                    apply_pleasure_gain(entity, gain)
            elif "counter_damage" in rule.then:
                # Preconditions:
                # - is_counter guard: counter legs never trigger counter damage (non-recursion).
                # - living source: dead or unresolvable source produces silent no-write.
                # Rollback invariant: counter HP writes and battlefield.knocked_out markings
                # are restorable because the action pipeline unconditionally snapshots the
                # actor (via the practice effect) and touches the battlefield when nonlethal_keys exist.
                if is_counter:
                    continue
                if source is None:
                    continue
                if not hasattr(source, "traits") or not hasattr(source.traits, "hp"):
                    continue
                from world.rules.action import _stored_trait_value
                from world.rules.combat import (
                    COMBAT_YAML,
                    _adjusted_attack,
                    _adjusted_defense,
                    _apply_hp_delta,
                    _apply_hp_delta_nonlethal,
                )

                source_hp_before = _stored_trait_value(source.traits.hp)
                if source_hp_before <= 0:
                    continue

                coeff = float(rule.then["counter_damage"])
                if hasattr(entity, "skills"):
                    atk_phys = _adjusted_attack(entity, "atk_phys")
                else:
                    atk_phys = 0.0
                source_def = (
                    _adjusted_defense(source) if hasattr(source, "skills") else 0.0
                )
                floor = int(COMBAT_YAML["damage"]["floor"])
                raw_amount = round(atk_phys * coeff) - source_def
                counter_amount = int(max(raw_amount, floor))

                src_key = str(getattr(source, "key", ""))
                is_protected = nonlethal or src_key in nonlethal_keys
                if not is_protected:
                    _apply_hp_delta(source, -counter_amount)
                else:
                    _apply_hp_delta_nonlethal(source, -counter_amount)
                    if (
                        source_hp_before > 0
                        and source_hp_before - counter_amount <= 0
                        and src_key in nonlethal_keys
                    ):
                        if battlefield is not None and hasattr(
                            battlefield, "knocked_out"
                        ):
                            battlefield.knocked_out.add(src_key)

                source_hp_after = _stored_trait_value(source.traits.hp)
                source_actual_loss = max(
                    0, int(source_hp_before - max(0.0, source_hp_after))
                )
                if source_actual_loss > 0:
                    dispatch_outcome_reaction(
                        source,
                        "hp_loss",
                        source_tier=source_tier,
                        rules=rules,
                        source_skill=source_skill,
                        is_counter=True,
                        hp_loss_amount=source_actual_loss,
                    )
            elif "apply_buff_to_source" in rule.then:
                # Preconditions:
                # - source must exist and have buffs handler
                # - dead source produces silent no-write
                if source is None:
                    continue
                if not hasattr(source, "buffs"):
                    continue
                if hasattr(source, "traits") and hasattr(source.traits, "hp"):
                    from world.rules.action import _stored_trait_value

                    if _stored_trait_value(source.traits.hp) <= 0:
                        continue

                from world.rules.buffs import BUFF_DEFINITIONS, apply_buff

                buff_key = rule.then["apply_buff_to_source"]
                definition = BUFF_DEFINITIONS.get(buff_key)
                if definition is None:
                    continue

                holder_key = str(getattr(entity, "key", ""))
                instance_key: str | None = None
                if definition.stacking == "unique_per_source":
                    instance_key = f"{buff_key}:{holder_key}"

                buff_kwargs: dict[str, Any] = {
                    "source_key": holder_key,
                    "source_tier": source_tier or "學徒",
                }
                if skill_key is not None:
                    buff_kwargs["source_skill"] = skill_key
                apply_buff(source, buff_key, instance_key=instance_key, **buff_kwargs)
            elif "mark_order_op" in rule.then:
                # Preconditions:
                # - source must exist and have buffs handler
                # - dead source produces silent no-write
                if source is None:
                    continue
                if not hasattr(source, "buffs"):
                    continue
                if hasattr(source, "traits") and hasattr(source.traits, "hp"):
                    from world.rules.action import _stored_trait_value

                    if _stored_trait_value(source.traits.hp) <= 0:
                        continue

                from world.rules.buffs import BUFF_DEFINITIONS, apply_buff

                buff_key = rule.then["mark_order_op"]
                definition = BUFF_DEFINITIONS.get(buff_key)
                if definition is None or not getattr(definition, "round_order", None):
                    continue

                holder_key = str(getattr(entity, "key", ""))
                instance_key: str | None = None
                if definition.stacking == "unique_per_source":
                    instance_key = f"{buff_key}:{holder_key}"

                buff_kwargs: dict[str, Any] = {
                    "source_key": holder_key,
                    "source_tier": source_tier or "學徒",
                }
                if skill_key is not None:
                    buff_kwargs["source_skill"] = skill_key
                apply_buff(source, buff_key, instance_key=instance_key, **buff_kwargs)


# Publish the phase dispatcher into the dependency leaf so the canonical
# phase setter reaches it without importing this module (F9'): the import is
# the registration, and the production bootstrap path force-imports this
# module at server start, making the edge explicit rather than lazy.
register_phase_dispatcher(dispatch_phase_reaction)
