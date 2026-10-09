"""Normal persistent adventurer assembly and branch-qualified identity selection.

This additive boundary does not start examinations or replace rank factories.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.npcs import LLMNPC, NPC, ensure_npc_canonical_age
from world.art.official_refs import NPC_PROFILE_PROVENANCE_ATTRIBUTE
from world.lore.guild_adventurers import (
    ADVENTURER_REGISTRY, EXAM_QUALIFICATIONS, UTILITY_SKILLS,
    ExamQualification, GuildAdventurer,
)
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.maps.bootstrap import resolve_residence_route
from world.observability import log_info
from world.rules.equipment import toggle_equipment
from world.rules.npc_identity import (
    live_key_taken_by_other, validate_npc_name, validate_npc_title,
)
from world.rules.npc_persona import initialize_npc_persona
from world.rules.npc_schedules import get_rulebook, resolve_schedule, set_npc_schedule
from world.rules.progression import apply_lineage_auto_seed
from world.rules.traits import _trait_config
from world.skills.registry import SKILL_REGISTRY, SkillKind

PERSON_ATTRIBUTE = "guild_adventurer_person_key"
_BASE_KEYS = ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power")


class GuildHostIntegrityError(ValueError):
    """Authored or persistent identity cannot select one coherent person."""


def qualification_for(
    branch_key: str, target_rank: str, *,
    people: Mapping[str, GuildAdventurer] | None = None,
    qualifications: Sequence[ExamQualification] | None = None,
) -> GuildAdventurer:
    """Select exactly one local qualified person; never fall back across branches."""
    people = ADVENTURER_REGISTRY if people is None else people
    qualifications = EXAM_QUALIFICATIONS if qualifications is None else qualifications
    matches = [row for row in qualifications
               if row.branch_key == branch_key and row.target_rank == target_rank]
    if len(matches) != 1 or matches[0].person_key not in people:
        raise GuildHostIntegrityError(f"qualification {branch_key!r}/{target_rank!r} is missing or ambiguous")
    person = people[matches[0].person_key]
    if person.branch_key != branch_key:
        raise GuildHostIntegrityError(f"qualification {branch_key!r}/{target_rank!r} names a wrong-branch person")
    return person


def find_persistent_adventurer(person_key: str) -> NPC | None:
    """Reuse by authored person provenance, never displayed key or location."""
    matches = [npc for npc in NPC.objects.all_family()
               if npc.attributes.get(PERSON_ATTRIBUTE) == person_key]
    if len(matches) > 1:
        raise GuildHostIntegrityError(f"person {person_key!r} has {len(matches)} persistent hosts")
    return matches[0] if matches else None


def qualified_host(branch_key: str, target_rank: str, **kwargs: Any) -> NPC:
    """Resolve authority to the actual persistent dbref without creating a host."""
    person = qualification_for(branch_key, target_rank, **kwargs)
    host = find_persistent_adventurer(person.key)
    if host is None:
        raise GuildHostIntegrityError(f"qualified person {person.key!r} has no persistent host")
    return host


def validate_adventurers(
    people: Mapping[str, GuildAdventurer], profiles: Mapping,
    qualifications: Sequence[ExamQualification],
) -> None:
    """Validate all authored inputs before any map or NPC creation writes."""
    from world.imports.validate import validate_character
    from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
    from world.lore.items import ITEM_REGISTRY
    from world.lore.npc_card import NpcCard, normalize_offline_greeting
    from world.lore.settlements.places import PLACE_REGISTRY

    seen_profiles = set()
    for key, person in people.items():
        if person.key != key or person.profession != "adventurer":
            raise GuildHostIntegrityError(f"person {key!r} has invalid identity/profession")
        validate_npc_name(person.name)
        validate_npc_title(person.title)
        profile = profiles.get(person.profile_key)
        if profile is None or person.profile_key in seen_profiles:
            raise GuildHostIntegrityError(f"person {key!r} has missing or shared profile {person.profile_key!r}")
        seen_profiles.add(person.profile_key)
        for field in ("age", "apparent_age"):
            value = getattr(profile, field)
            if type(value) is not int or not 0 <= value <= 10000:
                raise GuildHostIntegrityError(f"profile {person.profile_key!r} has invalid {field}")
        NpcCard.from_record(profile.card.to_record())
        for field in ("greeting", "misunderstood"):
            value = getattr(profile.voice, field)
            if not isinstance(value, str) or not value.strip():
                raise GuildHostIntegrityError(f"profile {person.profile_key!r} lacks {field}")
            normalize_offline_greeting(value)
        if person.home_key not in PLACE_REGISTRY or PLACE_REGISTRY[person.home_key].service_id is not None:
            raise GuildHostIntegrityError(f"person {key!r} needs a registered hostless home")
        if person.rank not in GUILD_RANK_REGISTRY or len(person.bases) != len(_BASE_KEYS):
            raise GuildHostIntegrityError(f"person {key!r} has invalid rank or bases")
        declared = (*UTILITY_SKILLS, person.sword_skill, *person.sword_branches)
        for skill_key in declared:
            if skill_key not in SKILL_REGISTRY:
                raise GuildHostIntegrityError(f"person {key!r} has unknown skill {skill_key!r}")
        for item_key in person.equipment:
            if item_key not in ITEM_REGISTRY or ITEM_REGISTRY[item_key].equipment_slot is None:
                raise GuildHostIntegrityError(f"person {key!r} has unsupported equipment {item_key!r}")
        record = {
            "record_type": "character", "schema_version": 1, "key": person.name,
            "display_name": person.name, "title": person.title,
            "race": "human", "subrace": person.subrace, "sex": "other",
            "age": profile.age, "apparent_age": profile.apparent_age,
            "stats": dict(zip(_BASE_KEYS, person.bases, strict=True)),
            "skills": [k for k in declared if SKILL_REGISTRY[k].kind is SkillKind.ACTIVE],
            "passives": [k for k in declared if SKILL_REGISTRY[k].kind is SkillKind.PASSIVE],
            "inventory": list(person.equipment), "equipment": {},
            "disguised_stats": {},
            "sexual_baseline": {"arousal": "平靜", "virgin": False, "sensitivity": {}},
            "persona": profile.card.to_record(),
        }
        report = validate_character(record, LLMNPC)
        if not report.is_valid:
            raise GuildHostIntegrityError(f"person {key!r} invalid normal character: {report.rejections}")
        parsed = resolve_schedule({"schema_version": 1, "template": person.schedule_template})
        if parsed.default_state != "duty" or any(
            entry.kind == "move" and entry.target not in {"home", "frontage", "guild"}
            for entry in parsed.entries
        ):
            raise GuildHostIntegrityError(f"person {key!r} has invalid residence routine")
    seen = set()
    for row in qualifications:
        binding = (row.branch_key, row.target_rank)
        if (binding in seen or row.branch_key not in GUILD_BRANCH_REGISTRY
                or row.target_rank not in GUILD_RANK_REGISTRY or row.person_key not in people
                or people[row.person_key].branch_key != row.branch_key):
            raise GuildHostIntegrityError(f"invalid or duplicate qualification {binding!r}")
        seen.add(binding)


def _bound_schedule(person: GuildAdventurer, rooms: Mapping) -> dict:
    template = get_rulebook().template_by_key(person.schedule_template)
    return {
        "schema_version": 1, "template": person.schedule_template,
        "overrides": {str(index): {"target": rooms[entry.target].dbref}
                      for index, entry in enumerate(template.entries) if entry.kind == "move"},
    }


def sync_persistent_adventurers(
    *, people: Mapping[str, GuildAdventurer] | None = None,
    profiles: Mapping | None = None,
    qualifications: Sequence[ExamQualification] | None = None,
) -> tuple[NPC, ...]:
    """Create each normal person once; existing mutable state is wholly untouched."""
    people = ADVENTURER_REGISTRY if people is None else people
    profiles = NPC_PROFILE_REGISTRY if profiles is None else profiles
    qualifications = EXAM_QUALIFICATIONS if qualifications is None else qualifications
    validate_adventurers(people, profiles, qualifications)
    with transaction.atomic():
        # Preflight every existing identity and route before the first creation.
        existing = {key: find_persistent_adventurer(key) for key in people}
        routes = {key: resolve_residence_route(row.home_key, "altoria_guild_hall")
                  for key, row in people.items() if existing[key] is None}
        hosts = []
        for key, person in people.items():
            host = existing[key]
            if host is None:
                rooms = routes[key]
                profile = profiles[person.profile_key]
                host = create_object(LLMNPC, key=person.name, location=rooms["home"])
                host.attributes.add(PERSON_ATTRIBUTE, key)
                host.attributes.add(NPC_PROFILE_PROVENANCE_ATTRIBUTE, person.profile_key)
                host.npc_title = person.title
                host.race, host.subrace, host.sex = "human", person.subrace, "other"
                host.db.profession = person.profession
                host.db.guild_rank = person.rank
                host._apply_trait_config(_trait_config({
                    **dict(zip(_BASE_KEYS, person.bases, strict=True)), "guild_merit": 0,
                }))
                ensure_npc_canonical_age(host, age=profile.age, apparent_age=profile.apparent_age)
                initialize_npc_persona(host, profile.card.to_record(),
                                      {"kind": "profile", "profile": person.profile_key})
                declared = (*UTILITY_SKILLS, person.sword_skill, *person.sword_branches)
                host.db.skills = {
                    "active": [k for k in declared if SKILL_REGISTRY[k].kind is SkillKind.ACTIVE],
                    "passive": [k for k in declared if SKILL_REGISTRY[k].kind is SkillKind.PASSIVE],
                }
                apply_lineage_auto_seed(host)
                host.db.inventory = list(person.equipment)
                for item_key in person.equipment:
                    outcome = toggle_equipment(host, item_key)
                    if outcome.outcome == "rejected":
                        raise GuildHostIntegrityError(f"person {key!r} equipment rejected: {outcome.reason}")
                set_npc_schedule(host, _bound_schedule(person, rooms))
                if live_key_taken_by_other(host):
                    host.key = f"{person.name}-{host.pk}"
                host.save()
                transaction.on_commit(lambda context={
                    "host": host.pk, "person": key, "profile": person.profile_key,
                    "home": rooms["home"].pk, "target": rooms["guild"].pk,
                }: log_info("guild_adventurer_created", context=context))
            hosts.append(host)
    return tuple(hosts)
