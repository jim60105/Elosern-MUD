"""關係線 (partner line): partner acts and the D-12 opposite-sex branch.

Ships the two seed acts this change registers; the sexual-catalog-partner
proposal appends the remaining acts to this same tuple and owns no other
file.
"""

from world.skills.registry import SkillDef, TargetSpec
from world.skills.sexual_acts._builder import SexualActDef, _act_family

PARTNER_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = _act_family(
    "關係",
    (
        "partner_caress",
        "愛撫",
        "以溫柔的撫摸回應對方的身體，在肌膚相觸間拉近彼此的距離。",
        TargetSpec.SINGLE,
        {},
        10,
        "腰腹",
        "腰腹",
        0.5,
        ("duo_act_count",),
        ("duo_act_count",),
        (),
        True,
    ),
    (
        "partner_hand_hold",
        "牽手交纏",
        "十指交纏地牽起對方的手，讓曖昧在掌心之間蔓延。",
        TargetSpec.SINGLE,
        {},
        3,
        "腰腹",
        "腰腹",
        0.5,
        ("duo_act_count",),
        ("duo_act_count",),
        (),
        True,
    ),
)
