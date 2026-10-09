"""Persistent adventurer identities; examination authority is a separate binding."""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class GuildAdventurer:
    key: str
    name: str
    title: str
    profile_key: str
    home_key: str
    rank: str
    subrace: str
    bases: tuple[int, int, int, int, int, int, int]
    sword_skill: str
    equipment: tuple[str, ...]
    schedule_template: str
    profession: str = "adventurer"
    sword_branches: tuple[str, ...] = ()
    branch_key: str = "guild_branch_altoria"


@dataclass(frozen=True)
class ExamQualification:
    branch_key: str
    target_rank: str
    person_key: str


ADVENTURER_REGISTRY = MappingProxyType({
    row.key: row for row in (
        GuildAdventurer(
            "altoria_hok", "霍克‧赤刃", "沿海B級冒險者",
            "altoria_hok_adventurer", "altoria_hok_home", "B", "human_coastal",
            (145, 110, 110, 14, 14, 13, 25), "thousand_blade_art",
            ("military_b_sword", "military_b_armor"), "guild_hok_daily",
            sword_branches=("blade_storm",),
        ),
        GuildAdventurer(
            "altoria_cassandra", "卡珊卓‧銀輝", "A級冒險者",
            "altoria_cassandra_adventurer", "altoria_cassandra_home", "A", "human_plains",
            (170, 120, 120, 17, 17, 16, 30), "blade_saint_arts",
            ("military_a_sword", "military_a_armor"), "guild_cassandra_weekly",
            sword_branches=("thousand_army_slash",),
        ),
        GuildAdventurer(
            "altoria_augustine", "奧古斯丁‧無名", "S級冒險者",
            "altoria_augustine_adventurer", "altoria_augustine_home", "S", "human_plains",
            (200, 120, 120, 20, 20, 19, 35), "true_sword_saint",
            ("military_s_sword", "military_s_armor"), "guild_augustine_weekly",
        ),
    )
})

EXAM_QUALIFICATIONS = tuple(
    ExamQualification("guild_branch_altoria", rank, person)
    for rank, person in (
        ("E", "altoria_hok"), ("D", "altoria_hok"),
        ("C", "altoria_hok"), ("B", "altoria_hok"),
        ("A", "altoria_cassandra"), ("S", "altoria_augustine"),
    )
)

# Skill kinds and prerequisite closure are resolved by the shared initializer.
UTILITY_SKILLS = (
    "body_enhancement_basic", "defense_instinct", "concentration", "heal",
    "light_arrow", "purify", "gale_step",
)
