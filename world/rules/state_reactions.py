"""Declarative phase transition reactions (light-climax-empowerment D2).

Consumes load_rules and evaluate_condition from world.rules.rulebook.schema
without inventing a new language or event bus. Dispatches once after a
successful canonical _apply_climax_phase_set edge, executing declared
apply_buff / remove_buff actions.
"""

from pathlib import Path
from typing import Any

from world.rules.rulebook.schema import Rule, evaluate_condition, load_rules

_RULES_PATH = Path(__file__).parent / "rulebook" / "state_reactions.yaml"

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
    }
)


def validate_state_reaction_rules(rules: list[Rule]) -> None:
    """Fail closed at load time on structurally invalid or unsupported rules."""
    from world.rules.buffs import BUFF_DEFINITIONS

    seen_empowerment_markers: set[str] = set()

    for rule in rules:
        unknown_when = set(rule.when) - _RECOGNIZED_WHEN_KEYS
        if unknown_when:
            raise ValueError(
                f"state reaction rule {rule.id!r} has unrecognized when condition: {sorted(unknown_when)[0]!r}"
            )

        then_keys = set(rule.then)
        if then_keys not in ({"apply_buff"}, {"remove_buff"}, {"pleasure_gain"}):
            raise ValueError(
                f"state reaction rule {rule.id!r} then clause must declare exactly one of "
                f"'apply_buff', 'remove_buff', or 'pleasure_gain', got {sorted(then_keys)!r}"
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
                if not gain_val:
                    raise ValueError(
                        f"state reaction rule {rule.id!r} pleasure_gain mapping must not be empty"
                    )
                from world.skills.cost_tiers import MP_COST_TIERS

                valid_tiers = set(MP_COST_TIERS.keys())
                for tier_name, tier_amount in gain_val.items():
                    if not isinstance(tier_name, str) or tier_name not in valid_tiers:
                        raise ValueError(
                            f"state reaction rule {rule.id!r} pleasure_gain invalid tier {tier_name!r}; "
                            f"must be one of {sorted(valid_tiers)}"
                        )
                    if (
                        isinstance(tier_amount, bool)
                        or not isinstance(tier_amount, int)
                        or tier_amount < 0
                    ):
                        raise ValueError(
                            f"state reaction rule {rule.id!r} pleasure_gain for tier {tier_name!r} "
                            f"must be a non-negative integer, got {tier_amount!r}"
                        )
            else:
                raise ValueError(
                    f"state reaction rule {rule.id!r} pleasure_gain must be an integer or mapping of tiers to integers, got {type(gain_val).__name__}"
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


def dispatch_outcome_reaction(
    entity: Any,
    event: str,
    source_tier: str | None = None,
    rules: list[Rule] | None = None,
) -> None:
    """Dispatch outcome reactions (hp_loss, negative_buff_added) to matching rules.

    Context provides: entity, event, active_buffs, and sexual fields (climax_phase, arousal).
    A pleasure_gain action calculates the gain using the source_tier (falling back to '學徒'
    for non-spell or unspecified sources) and calls canonical apply_pleasure_gain.
    """
    if not hasattr(entity, "attributes"):
        return

    from world.rules.buffs import active_buff_keys_from_storage

    active_rules = rules if rules is not None else STATE_REACTION_RULES
    context: dict[str, Any] = {
        "entity": entity,
        "event": event,
        "active_buffs": active_buff_keys_from_storage(entity),
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
        if evaluate_condition(rule.when, context):
            if "pleasure_gain" in rule.then:
                from world.rules.pleasure import apply_pleasure_gain

                gain_spec = rule.then["pleasure_gain"]
                if isinstance(gain_spec, dict):
                    chosen_tier = (
                        source_tier
                        if (source_tier and source_tier in gain_spec)
                        else "學徒"
                    )
                    gain = gain_spec.get(chosen_tier, gain_spec.get("學徒", 0))
                elif isinstance(gain_spec, int):
                    gain = gain_spec
                else:
                    gain = 0

                if gain > 0:
                    apply_pleasure_gain(entity, gain)
            elif "apply_buff" in rule.then:
                from world.rules.buffs import apply_buff

                apply_buff(entity, rule.then["apply_buff"])
            elif "remove_buff" in rule.then:
                from world.rules.buffs import remove_by_selector

                remove_by_selector(entity, rule.then["remove_buff"])
