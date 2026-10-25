"""Read-only condition evaluation and canonical hints for authored dialogue.

``evaluate_condition`` is the single runtime truth of a :class:`Condition`
declaration; ``condition_hint`` renders the same declaration as the bounded
player-facing requirement text a locked topic shows. Both are pure reads over
an immutable :class:`world.rules.dialogue_context.DialogueContext`: they never
materialize the world clock or a sexual handler, never consume inventory,
never write skill practice and never grant an effect.

Ownership rules the evaluator enforces:

- race, social identity, carried items, skills and exposure read the ACTING
  BODY (the possessed companion when one is driven), never the owning player;
- companion presence requires current owner membership through the live party
  binding plus actor-local co-location, so a detached or remote companion
  never qualifies;
- a package-role companion resolves only in the context's own trusted
  package identity, requiring the published package, a currently bound role
  and that exact binding's live NPC;
- time compares the in-world day against the clock rulebook's daypart
  boundaries as a cyclic half-open world-day interval.
- guild rank, quest lifecycle and reward claims read the OWNING player, never
  the acting body: a possessed companion's own registration or quest log can
  never satisfy a progression condition;
- host affinity reads the conversation host's relationship toward the owner and
  compares the canonical stage boundary, never a second ordering table.

Corrupt or unresolvable authoritative state fails closed (``False``) and emits
exactly one bounded ``dialogue_condition_integrity`` facade event per
top-level evaluation, carrying only identifiers and a stable reason code --
never a stored record. Unresolvable canonical HINT labels raise
:class:`DialogueConditionError` instead: a declaration that cannot be rendered
must never ship a hint.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

from world.lore.dialogue.conditions import (
    MAX_CONDITION_CHILDREN,
    MAX_CONDITION_DEPTH,
    AffinityAtLeast,
    All,
    Any as AnyCondition,
    Carries,
    CompanionPresent,
    Condition,
    Exposure,
    GuildRankAtLeast,
    QuestIs,
    RaceIs,
    SkillOwned,
    SocialIdentityIs,
    TimePeriod,
)
from world.lore.scenes import Scene
from world.lore.sexual_vocab import EXPOSURE_LEVELS
from world.observability import log_warn

EVENT_CONDITION_INTEGRITY = "dialogue_condition_integrity"

REASON_DEPTH = "condition_depth_exceeded"
REASON_CHILDREN = "condition_children_invalid"
REASON_ACTOR_MISSING = "actor_missing"
REASON_ACTOR_RACE = "actor_race_unresolved"
REASON_SOCIAL_IDENTITIES = "actor_social_identities_malformed"
REASON_INVENTORY = "actor_inventory_malformed"
REASON_EQUIPMENT = "actor_equipment_malformed"
REASON_EXPOSURE = "actor_exposure_unresolved"
REASON_SKILLS = "actor_skills_malformed"
REASON_PROFICIENCY = "actor_proficiency_malformed"
REASON_CLOCK = "world_clock_unresolved"
REASON_OWNER = "owner_unresolved"
REASON_GUILD_RANK = "owner_guild_rank_unresolved"
REASON_QUEST_LOG = "owner_quest_log_malformed"
REASON_REWARD_CLAIMS = "owner_reward_claims_malformed"
REASON_QUEST_DEFINITION = "quest_definition_unpermitted"
REASON_QUEST_STATE = "quest_state_unsupported"
REASON_AFFINITY = "owner_affinity_unresolved"
REASON_COMPANION_PROVENANCE = "companion_provenance_malformed"
REASON_PACKAGE = "companion_package_unresolved"
REASON_ROLE = "companion_role_unavailable"

#: Marker for a stored record whose shape/vocabulary is authoritative but corrupt.
_INVALID = object()


class DialogueConditionError(ValueError):
    """A condition cannot be evaluated or rendered from canonical data."""


class _Evaluation:
    """Per-call state: the first bounded integrity reason, emitted once."""

    __slots__ = ("context", "reason")

    def __init__(self, context: Any) -> None:
        self.context = context
        self.reason: str | None = None

    def fail(self, reason: str) -> bool:
        if self.reason is None:
            self.reason = reason
        return False

    def finish(self) -> None:
        if self.reason is None:
            return
        log_warn(
            EVENT_CONDITION_INTEGRITY,
            context={
                "reason": self.reason,
                "actor": _identity(getattr(self.context, "actor", None)),
                "owner": _identity(getattr(self.context, "owner", None)),
                "npc": _identity(getattr(self.context, "host", None)),
            },
        )


def _identity(entity: Any) -> str:
    value = getattr(entity, "pk", None)
    return str(value) if value is not None else "?"


def _actor(context: Any) -> Any:
    return getattr(context, "actor", None)


def _owner(context: Any) -> Any:
    return getattr(context, "owner", None)


def evaluate_condition(condition: Condition, context: Any) -> bool:
    """Return whether ``condition`` currently holds for ``context``'s actor."""
    evaluation = _Evaluation(context)
    try:
        result = _evaluate(condition, context, evaluation, depth=1)
    finally:
        evaluation.finish()
    if evaluation.reason is not None:
        # Corrupt authoritative state dominates the whole tree: a matching
        # alternative never rescues a declaration whose evaluation could not
        # read the actor's state truthfully.
        return False
    return result


def condition_hint(condition: Condition, context: Any) -> str:
    """Render one canonical requirement hint for ``condition``.

    The text recurses over the SAME All/Any tree the evaluator walks, with
    explicit parentheses around every group and the localized conjunction
    ``且`` / disjunction ``或``. Labels come from the permitted-reference
    catalog (or, for a package role, the permitted package's own role
    definition), never from an editable display name.
    """
    references = _references()
    return _hint(condition, context, references)


def select_scene_variant(topic: Any, context: Any) -> Scene:
    """Return the unique highest-priority matching variant, or the fallback.

    Declaration validation rejects duplicate variant priorities inside one
    topic, so the winner is deterministic; should a hand-built topic bypass
    that check, the first declaration at the winning priority stays stable.
    """
    best = None
    for variant in getattr(topic, "variants", ()):
        if not evaluate_condition(variant.when, context):
            continue
        if best is None or variant.priority > best.priority:
            best = variant
    return best.scene if best is not None else topic.fallback


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def _evaluate(
    condition: Condition, context: Any, evaluation: _Evaluation, *, depth: int
) -> bool:
    if depth > MAX_CONDITION_DEPTH:
        return evaluation.fail(REASON_DEPTH)

    if isinstance(condition, All):
        if not _children_bounded(condition.children):
            return evaluation.fail(REASON_CHILDREN)
        return all(
            _evaluate(child, context, evaluation, depth=depth + 1)
            for child in condition.children
        )

    if isinstance(condition, AnyCondition):
        if not _children_bounded(condition.children):
            return evaluation.fail(REASON_CHILDREN)
        return any(
            _evaluate(child, context, evaluation, depth=depth + 1)
            for child in condition.children
        )

    if isinstance(condition, RaceIs):
        return _race_matches(condition, context, evaluation)

    if isinstance(condition, SocialIdentityIs):
        return _social_identity_matches(condition, context, evaluation)

    if isinstance(condition, Carries):
        return _carries(condition, context, evaluation)

    if isinstance(condition, CompanionPresent):
        return _companion_present(condition, context, evaluation)

    if isinstance(condition, TimePeriod):
        return _time_period_matches(condition, context, evaluation)

    if isinstance(condition, SkillOwned):
        return _skill_owned(condition, context, evaluation)

    if isinstance(condition, Exposure):
        return _exposure_matches(condition, context, evaluation)

    if isinstance(condition, GuildRankAtLeast):
        return _guild_rank_at_least(condition, context, evaluation)

    if isinstance(condition, QuestIs):
        return _quest_is(condition, context, evaluation)

    if isinstance(condition, AffinityAtLeast):
        return _affinity_at_least(condition, context, evaluation)

    raise DialogueConditionError(f"Unknown condition node: {condition!r}")


def _children_bounded(children: Sequence[Condition]) -> bool:
    return 1 <= len(children) <= MAX_CONDITION_CHILDREN


def _race_matches(
    condition: RaceIs, context: Any, evaluation: _Evaluation
) -> bool:
    from world.lore.races import RACE_REGISTRY

    actor = _actor(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    race_key = getattr(actor, "race", None)
    if not isinstance(race_key, str) or race_key not in RACE_REGISTRY:
        return evaluation.fail(REASON_ACTOR_RACE)
    return race_key == condition.race_key


def _social_identity_matches(
    condition: SocialIdentityIs, context: Any, evaluation: _Evaluation
) -> bool:
    actor = _actor(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    identities = _strict_social_identities(actor)
    if identities is None:
        return evaluation.fail(REASON_SOCIAL_IDENTITIES)
    return condition.identity_key in identities


def _strict_social_identities(entity: Any) -> frozenset[str] | None:
    """Read assigned identities, distinguishing absence from corrupt storage."""
    from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY
    from world.rules.social_identity import SOCIAL_IDENTITIES_ATTRIBUTE

    attributes = getattr(entity, "attributes", None)
    if attributes is None or not hasattr(attributes, "has"):
        return frozenset()
    if not attributes.has(SOCIAL_IDENTITIES_ATTRIBUTE):
        return frozenset()
    raw = attributes.get(SOCIAL_IDENTITIES_ATTRIBUTE)
    if raw is None:
        return frozenset()
    if isinstance(raw, (str, bytes, dict)) or not isinstance(
        raw, (list, tuple, set, frozenset)
    ):
        return None
    keys: set[str] = set()
    for entry in raw:
        if not isinstance(entry, str) or entry not in SOCIAL_IDENTITY_REGISTRY:
            return None
        keys.add(entry)
    return frozenset(keys)


def _carries(condition: Carries, context: Any, evaluation: _Evaluation) -> bool:
    from world.rules.party_inventory import PartyInventoryViewError, _strict_inventory

    actor = _actor(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    try:
        inventory = _strict_inventory(actor)
    except PartyInventoryViewError:  # observability: ignore R2: the evaluation fails closed and its single bounded integrity event reports the malformed inventory
        return evaluation.fail(REASON_INVENTORY)
    return inventory.count(condition.item_key) >= condition.minimum


def _companion_present(
    condition: CompanionPresent, context: Any, evaluation: _Evaluation
) -> bool:
    from world.rules.party import is_companion, live_companions

    actor = _actor(context)
    owner = _owner(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    if owner is None:
        return evaluation.fail(REASON_OWNER)

    if condition.source_kind == "package_role":
        return _package_role_present(condition, context, evaluation)

    actor_location = getattr(actor, "location", None)
    for companion in live_companions(owner):
        if not is_companion(companion, owner):
            continue
        matched = _companion_provenance_matches(companion, condition)
        if matched is _INVALID:
            return evaluation.fail(REASON_COMPANION_PROVENANCE)
        if not matched:
            continue
        if actor_location is None or getattr(companion, "location", None) is not actor_location:
            continue
        return True
    return False


def _companion_provenance_matches(
    companion: Any, condition: CompanionPresent
) -> bool | object:
    """Match one live companion's provenance, or ``_INVALID`` when it is corrupt."""
    if condition.source_kind == "profile":
        from world.rules.npc_persona import provenance_profile_key

        return provenance_profile_key(companion) == condition.source_key

    provenance = _companion_provenance(companion)
    if provenance is None:
        return False
    if provenance is _INVALID:
        return _INVALID
    if provenance.get("kind") != "companion":
        return False
    profile = provenance.get("profile")
    return isinstance(profile, str) and profile == condition.source_key


def _companion_provenance(companion: Any) -> Mapping[str, Any] | None | object:
    """Read one companion's stored provenance mapping.

    ``None`` means "no persona metadata" (not this kind of companion);
    ``_INVALID`` means present but malformed, which fails the evaluation closed.
    """
    attributes = getattr(companion, "attributes", None)
    if attributes is None or not hasattr(attributes, "has"):
        return None
    if not attributes.has("npc_persona_meta"):
        return None
    meta = getattr(getattr(companion, "db", None), "npc_persona_meta", None)
    if meta is None:
        return None
    if not isinstance(meta, Mapping):
        return _INVALID
    provenance = meta.get("provenance")
    if provenance is None:
        return _INVALID
    if not isinstance(provenance, Mapping):
        return _INVALID
    return provenance


def _package_role_present(
    condition: CompanionPresent, context: Any, evaluation: _Evaluation
) -> bool:
    from evennia.objects.objects import ObjectDB

    from world.quests import scene_store
    from world.rules.party import is_companion

    package_id = getattr(getattr(context, "source_identity", None), "package_id", None)
    if not isinstance(package_id, str) or not package_id:
        # A static source has no permitted package, so no package role can
        # ever be present for it.
        return evaluation.fail(REASON_PACKAGE)
    package = scene_store.read_package(package_id)
    if package is None or package.status != scene_store.PACKAGE_STATUS_PUBLISHED:
        return evaluation.fail(REASON_PACKAGE)
    binding = scene_store.get_role_binding(package_id, condition.source_key)
    if binding is None or binding.availability != scene_store.AVAILABILITY_BOUND:
        return evaluation.fail(REASON_ROLE)
    companion = ObjectDB.objects.filter(id=binding.npc_id).first()
    if companion is None:
        return evaluation.fail(REASON_ROLE)
    owner = _owner(context)
    if owner is None:
        return evaluation.fail(REASON_OWNER)
    if not is_companion(companion, owner):
        return False
    actor_location = getattr(_actor(context), "location", None)
    if actor_location is None or getattr(companion, "location", None) is not actor_location:
        return False
    return True


def _time_period_matches(
    condition: TimePeriod, context: Any, evaluation: _Evaluation
) -> bool:
    from world.rules.clock import CLOCK_YAML, read_world_clock

    try:
        clock = read_world_clock()
        calendar = getattr(clock, "calendar", None) if clock is not None else None
    except (TypeError, ValueError, OverflowError):  # observability: ignore R2: the evaluation fails closed and its single bounded integrity event reports the corrupt clock record
        return evaluation.fail(REASON_CLOCK)
    if calendar is None:
        return evaluation.fail(REASON_CLOCK)
    dayparts = CLOCK_YAML.get("dayparts")
    seconds_per_hour = CLOCK_YAML.get("seconds_per_hour")
    if not isinstance(dayparts, Mapping) or not isinstance(seconds_per_hour, int):
        return evaluation.fail(REASON_CLOCK)
    start_hour = dayparts.get(condition.start_daypart)
    end_hour = dayparts.get(condition.end_daypart)
    if (
        isinstance(start_hour, bool)
        or not isinstance(start_hour, int)
        or isinstance(end_hour, bool)
        or not isinstance(end_hour, int)
        or start_hour == end_hour
    ):
        return evaluation.fail(REASON_CLOCK)
    hour = getattr(calendar, "hour", None)
    minute = getattr(calendar, "minute", None)
    second = getattr(calendar, "second", None)
    if not all(isinstance(value, int) for value in (hour, minute, second)):
        return evaluation.fail(REASON_CLOCK)

    current = hour * seconds_per_hour + minute * 60 + second
    start = start_hour * seconds_per_hour
    end = end_hour * seconds_per_hour
    if start < end:
        return start <= current < end
    # The authored interval wraps midnight: [start, end) spans the world day.
    return current >= start or current < end


def _skill_owned(
    condition: SkillOwned, context: Any, evaluation: _Evaluation
) -> bool:
    from world.skills.handler import SkillHandler

    actor = _actor(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    stored_skills = getattr(getattr(actor, "db", None), "skills", None)
    if not _skills_record_valid(stored_skills):
        return evaluation.fail(REASON_SKILLS)
    try:
        owned = SkillHandler(actor).owned_keys()
    except (TypeError, ValueError, OverflowError):  # observability: ignore R2: the evaluation fails closed and its single bounded integrity event reports the corrupt skill counter record
        return evaluation.fail(REASON_SKILLS)
    if condition.skill_key not in owned:
        # A conferred scale-only grant is not ownership.
        return False
    if condition.min_proficiency is None:
        return True

    from world.rules.progression._gates import skill_proficiency_level

    proficiency = getattr(getattr(actor, "db", None), "skill_proficiency", None)
    if not _proficiency_record_valid(proficiency):
        return evaluation.fail(REASON_PROFICIENCY)
    try:
        level = skill_proficiency_level(
            actor, condition.skill_key, proficiency=proficiency
        )
    except (TypeError, ValueError, OverflowError):  # observability: ignore R2: the evaluation fails closed and its single bounded integrity event reports the corrupt proficiency record
        return evaluation.fail(REASON_PROFICIENCY)
    return level >= condition.min_proficiency


def _skills_record_valid(raw: Any) -> bool:
    if raw is None:
        return True
    if not isinstance(raw, Mapping):
        return False
    for container in ("active", "passive"):
        if container not in raw:
            continue
        values = raw[container]
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            return False
        if not all(isinstance(value, str) for value in values):
            return False
    return True


def _proficiency_record_valid(raw: Any) -> bool:
    if raw is None:
        return True
    if not isinstance(raw, Mapping):
        return False
    for key, value in raw.items():
        if not isinstance(key, str):
            return False
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not isfinite(float(value)) or value < 0:
            return False
    return True


def _exposure_matches(
    condition: Exposure, context: Any, evaluation: _Evaluation
) -> bool:
    from world.rules.equipment import normalized_equipment
    from world.rules.equipment_effects import effective_exposure

    actor = _actor(context)
    if actor is None:
        return evaluation.fail(REASON_ACTOR_MISSING)
    stored = _strict_stored_exposure(actor)
    if stored is _INVALID or stored is None:
        # A present-but-corrupt record must never become valid again through
        # the canonical reader's baseline fallback or a relabelled vocabulary.
        return evaluation.fail(REASON_EXPOSURE)
    if normalized_equipment(actor) is None:
        # Malformed worn storage contributes no bias in the canonical reader;
        # the condition must not silently evaluate the bare stored level.
        return evaluation.fail(REASON_EQUIPMENT)
    try:
        effective = effective_exposure(actor)
    except (KeyError, TypeError, ValueError, OverflowError):  # observability: ignore R2: the evaluation fails closed and its single bounded integrity event reports the corrupt exposure record
        return evaluation.fail(REASON_EXPOSURE)
    ordinal = _exposure_ordinal(effective)
    if ordinal is None:
        return evaluation.fail(REASON_EXPOSURE)
    if condition.minimum is not None and ordinal < condition.minimum:
        return False
    if condition.maximum is not None and ordinal > condition.maximum:
        return False
    return True


def _strict_stored_exposure(entity: Any) -> Any:
    """Validate the stored exposure record before the canonical overlay reads it.

    Returns the validated stored value (a canonical level label or ordinal),
    ``None`` when no exposure is stored at all, or ``_INVALID`` for a present
    record whose shape or vocabulary is corrupt. The precedence mirrors
    ``world.rules.stored_sexual_reads.stored_sexual_level`` exactly (materialized
    trait record first, then the import-time baseline), so this is a strict
    pre-check rather than a second exposure formula.
    """
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return None
    traits = attributes.get("sexual_traits", default=None, category="traits")
    if isinstance(traits, Mapping) and "exposure" in traits:
        raw = traits["exposure"]
        if not isinstance(raw, Mapping):
            return _INVALID
        levels = raw.get("levels")
        value = raw.get("value")
        if levels is not None:
            if isinstance(levels, (str, bytes)) or not isinstance(
                levels, (list, tuple)
            ):
                return _INVALID
            if tuple(levels) != EXPOSURE_LEVELS:
                return _INVALID
        if isinstance(value, bool):
            return _INVALID
        if isinstance(value, int):
            if levels is None:
                return _INVALID
            return value if 0 <= value < len(EXPOSURE_LEVELS) else _INVALID
        if isinstance(value, str):
            return value if value in EXPOSURE_LEVELS else _INVALID
        return _INVALID
    baseline = attributes.get("sexual", default=None)
    if isinstance(baseline, Mapping) and "exposure" in baseline:
        value = baseline.get("exposure")
        if isinstance(value, str) and value in EXPOSURE_LEVELS:
            return value
        return _INVALID
    return None


def _exposure_ordinal(effective: Any) -> int | None:
    """Resolve one canonical effective exposure to its EXPOSURE_LEVELS ordinal."""
    levels = getattr(effective, "levels", None)
    if levels is not None:
        if tuple(levels) != EXPOSURE_LEVELS:
            return None
        value = getattr(effective, "value", None)
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        if not 0 <= value < len(EXPOSURE_LEVELS):
            return None
        return value
    if isinstance(effective, str):
        try:
            return EXPOSURE_LEVELS.index(effective)
        except ValueError:  # observability: ignore R2: an unlisted stored label is invalid state, reported by the evaluation's bounded integrity event
            return None
    return None


def _guild_rank_at_least(
    condition: GuildRankAtLeast, context: Any, evaluation: _Evaluation
) -> bool:
    """Compare the owner's canonical rank order against ``condition.rank_key``."""
    from world.lore.guild import GUILD_RANK_REGISTRY
    from world.rules.guild import GuildDataError, parse_guild_registration

    owner = _owner(context)
    if owner is None:
        return evaluation.fail(REASON_OWNER)
    target = GUILD_RANK_REGISTRY.get(condition.rank_key)
    if target is None:
        return evaluation.fail(REASON_GUILD_RANK)
    try:
        registration = parse_guild_registration(owner)
    except GuildDataError:  # observability: ignore R2: corrupt owner state fails closed and is reported by the evaluation's bounded integrity event, never by the stored record
        return evaluation.fail(REASON_GUILD_RANK)
    if registration is None:
        # An unregistered owner is a legitimate unqualified state, and an
        # actor-side rank can never stand in for it.
        return False
    # AttributeProperty defaults autocreate on read, so the rank is read through
    # the non-materializing handler: an evaluator never writes an attribute.
    attributes = getattr(owner, "attributes", None)
    rank_key = (
        attributes.get("guild_rank")
        if attributes is not None
        else getattr(owner, "guild_rank", None)
    )
    if rank_key is None:
        return False
    if not isinstance(rank_key, str) or not rank_key:
        return evaluation.fail(REASON_GUILD_RANK)
    row = GUILD_RANK_REGISTRY.get(rank_key)
    if row is None:
        return evaluation.fail(REASON_GUILD_RANK)
    return row.order >= target.order


def _quest_is(condition: QuestIs, context: Any, evaluation: _Evaluation) -> bool:
    """Match one permitted definition key against the owner's quest records."""
    from world.quests.runtime import QuestDataError, QuestState, read_records

    from world.rules.dialogue_references import permitted_quest_definition

    owner = _owner(context)
    if owner is None:
        return evaluation.fail(REASON_OWNER)
    if not permitted_quest_definition(condition.definition_key):
        return evaluation.fail(REASON_QUEST_DEFINITION)
    db = getattr(owner, "db", None)
    if db is None:
        return evaluation.fail(REASON_QUEST_LOG)
    raw = db.quest_log
    # ``read_records`` treats a falsy scalar as an empty log; a malformed stored
    # shape must fail closed instead of satisfying ``not_accepted``.
    if raw is not None and (
        isinstance(raw, (str, bytes, Mapping)) or not hasattr(raw, "__iter__")
    ):
        return evaluation.fail(REASON_QUEST_LOG)
    try:
        records = read_records(owner)
    except QuestDataError:  # observability: ignore R2: corrupt owner state fails closed and is reported by the evaluation's bounded integrity event, never by the stored record
        return evaluation.fail(REASON_QUEST_LOG)
    matching = [
        record
        for record in records
        if record.definition_key == condition.definition_key
    ]
    if condition.state == "not_accepted":
        return not matching
    if condition.state == "in_progress":
        return any(record.state is QuestState.IN_PROGRESS for record in matching)
    if condition.state == "completed":
        return any(record.state is QuestState.COMPLETED for record in matching)
    if condition.state == "failed":
        return any(record.state is QuestState.FAILED for record in matching)
    if condition.state == "invalidated":
        return any(record.state is QuestState.INVALIDATED for record in matching)
    if condition.state == "reward_claimed":
        from world.rules.guild import RewardClaimError, parse_reward_claims

        raw_claims = db.guild_reward_claims
        if raw_claims is not None and (
            isinstance(raw_claims, (str, bytes, Mapping))
            or not hasattr(raw_claims, "__iter__")
        ):
            return evaluation.fail(REASON_REWARD_CLAIMS)
        try:
            claims = set(parse_reward_claims(owner))
        except RewardClaimError:  # observability: ignore R2: corrupt claim state fails closed and is reported by the evaluation's bounded integrity event, never by the stored ledger
            return evaluation.fail(REASON_REWARD_CLAIMS)
        return any(
            record.state is QuestState.COMPLETED and record.quest_id in claims
            for record in matching
        )
    return evaluation.fail(REASON_QUEST_STATE)


def _affinity_at_least(
    condition: AffinityAtLeast, context: Any, evaluation: _Evaluation
) -> bool:
    """Compare the host-to-owner affinity value against the stage's canonical floor."""
    from world.rules.affinity_config import AffinityConfigError, get_config

    owner = _owner(context)
    if owner is None:
        return evaluation.fail(REASON_OWNER)
    relations = getattr(getattr(context, "host", None), "relations", None)
    if relations is None:
        return evaluation.fail(REASON_AFFINITY)
    try:
        target = get_config().stage_by_id(condition.stage_key)
    except AffinityConfigError:  # observability: ignore R2: a corrupt affinity rulebook fails closed and is reported by the evaluation's bounded integrity event, never by the rulebook contents
        return evaluation.fail(REASON_AFFINITY)
    if target is None:
        return evaluation.fail(REASON_AFFINITY)
    value = relations.affinity_for(owner)
    if isinstance(value, bool) or not isinstance(value, int):
        return evaluation.fail(REASON_AFFINITY)
    return value >= target.floor


# ---------------------------------------------------------------------------
# Hints
# ---------------------------------------------------------------------------


def _references() -> Any:
    from world.rules.dialogue_references import static_dialogue_references

    return static_dialogue_references()


def _label(references: Any, family: str, key: str) -> str:
    label = references.label(family, key)
    if not label:
        raise DialogueConditionError(
            f"Condition label for {family} key {key!r} is not in the permitted catalog"
        )
    return label


def _exposure_label(ordinal: int) -> str:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int):
        raise DialogueConditionError(f"Exposure bound {ordinal!r} is not an integer")
    if not 0 <= ordinal < len(EXPOSURE_LEVELS):
        raise DialogueConditionError(
            f"Exposure bound {ordinal} is outside EXPOSURE_LEVELS"
        )
    return EXPOSURE_LEVELS[ordinal]


def _hint(condition: Condition, context: Any, references: Any) -> str:
    if isinstance(condition, All):
        parts = [_hint(child, context, references) for child in condition.children]
        return "需要（" + "）且（".join(parts) + "）"

    if isinstance(condition, AnyCondition):
        parts = [_hint(child, context, references) for child in condition.children]
        return "需要（" + "）或（".join(parts) + "）"

    if isinstance(condition, RaceIs):
        return f"需要種族為{_label(references, 'race', condition.race_key)}"

    if isinstance(condition, SocialIdentityIs):
        return f"需要{_label(references, 'social_identity', condition.identity_key)}身分"

    if isinstance(condition, Carries):
        label = _label(references, "item", condition.item_key)
        if condition.minimum <= 1:
            return f"需要持有{label}"
        return f"需要持有{label}×{condition.minimum}"

    if isinstance(condition, CompanionPresent):
        return f"需要{_companion_label(condition, context, references)}同行"

    if isinstance(condition, TimePeriod):
        return (
            f"需要在{_label(references, 'daypart', condition.start_daypart)}"
            f"至{_label(references, 'daypart', condition.end_daypart)}之間"
        )

    if isinstance(condition, SkillOwned):
        hint = f"需要技能{_label(references, 'skill', condition.skill_key)}"
        if condition.min_proficiency is not None:
            hint += f"（熟練度至少 {condition.min_proficiency}）"
        return hint

    if isinstance(condition, Exposure):
        if condition.minimum is not None and condition.maximum is not None:
            return (
                f"需要暴露程度在{_exposure_label(condition.minimum)}"
                f"至{_exposure_label(condition.maximum)}之間"
            )
        if condition.minimum is not None:
            return f"需要暴露程度至少為{_exposure_label(condition.minimum)}"
        return f"需要暴露程度至多為{_exposure_label(condition.maximum)}"

    if isinstance(condition, GuildRankAtLeast):
        return (
            "需要公會階級至少為"
            f"{_label(references, 'guild_rank', condition.rank_key)}"
        )

    if isinstance(condition, QuestIs):
        return _quest_hint(condition, references)

    if isinstance(condition, AffinityAtLeast):
        # The stage label is public wording; the current and threshold numeric
        # relationship values never enter a hint.
        return (
            "需要好感階段至少為"
            f"{_label(references, 'affinity_stage', condition.stage_key)}"
        )

    raise DialogueConditionError(f"Unknown condition node: {condition!r}")


def _quest_hint(condition: QuestIs, references: Any) -> str:
    """Render one quest requirement using the canonical definition and state labels."""
    from world.quests.describe import quest_state_label

    label = _label(references, "quest", condition.definition_key)
    state_label = quest_state_label(condition.state)
    if state_label is None:
        raise DialogueConditionError(
            f"Quest state {condition.state!r} has no canonical hint label"
        )
    if condition.state == "not_accepted":
        return f"需要尚未接取任務「{label}」"
    return f"需要任務「{label}」{state_label}"


def _companion_label(
    condition: CompanionPresent, context: Any, references: Any
) -> str:
    if condition.source_kind == "preset":
        return _label(references, "preset", condition.source_key)
    if condition.source_kind == "profile":
        return _label(references, "profile", condition.source_key)
    return _package_role_label(context, condition.source_key)


def _package_role_label(context: Any, role_id: str) -> str:
    """Resolve one permitted package role's authored public label."""
    from world.quests import scene_store
    from world.quests.scene_package import validated_package

    package_id = getattr(getattr(context, "source_identity", None), "package_id", None)
    if not isinstance(package_id, str) or not package_id:
        raise DialogueConditionError(
            f"Package role {role_id!r} has no permitted package in this context"
        )
    row = scene_store.read_package(package_id)
    if row is None:
        raise DialogueConditionError(f"Package {package_id!r} is not published")
    definition = validated_package(package_id, row.payload)
    role = definition.role(role_id) if definition is not None else None
    label = getattr(getattr(role, "characterization", None), "display_name", None)
    if not isinstance(label, str) or not label:
        raise DialogueConditionError(
            f"Package role {role_id!r} has no authored display label"
        )
    return label


__all__ = [
    "DialogueConditionError",
    "EVENT_CONDITION_INTEGRITY",
    "condition_hint",
    "evaluate_condition",
    "select_scene_variant",
]
