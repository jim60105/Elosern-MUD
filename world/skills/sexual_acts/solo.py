"""獨處線 (solo line): solo acts.

Ships the three seed acts this change registers; the sexual-catalog-solo
proposal appends the remaining acts to this same tuple and owns no other
file.
"""

from world.skills.registry import SkillDef, TargetSpec
from world.skills.sexual_acts._builder import SexualActDef, _act_family

SOLO_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = _act_family(
    "獨處",
    (
        "solo_self_touch",
        "自撫",
        "獨處時撫弄自己的私處，讓身體在快感中逐漸甦醒。",
        TargetSpec.SELF,
        {},
        12,
        "私處",
        None,
        1.0,
        ("masturbation_count",),
        (),
        ("masturbation_climax",),
        False,
    ),
    (
        "solo_fondle_breasts",
        "揉捏胸部",
        "隔著衣物或直接揉弄自己的乳房，享受肌膚的觸感。",
        TargetSpec.SELF,
        {},
        9,
        "乳房",
        None,
        1.0,
        ("masturbation_count",),
        (),
        (),
        False,
    ),
    (
        "solo_thigh_rub",
        "摩擦大腿",
        "夾緊雙腿來回摩擦，以隱晦的方式安撫逐漸升溫的身體。",
        TargetSpec.SELF,
        {},
        8,
        "大腿",
        None,
        1.0,
        ("masturbation_count",),
        (),
        (),
        False,
    ),
)
