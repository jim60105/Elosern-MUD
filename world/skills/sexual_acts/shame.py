"""羞恥線 (shame line): exposure- and shame-driven acts.

Ships the one seed act this change registers; the sexual-catalog-shame
proposal appends the remaining acts to this same tuple and owns no other
file.
"""

from world.skills.registry import SkillDef, TargetSpec
from world.skills.sexual_acts._builder import SexualActDef, _act_family

SHAME_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = _act_family(
    "羞恥",
    (
        "shame_hem_lift",
        "撩起衣襬",
        "撩起自己的衣襬，讓肌膚在他人目光下微微裸露。",
        TargetSpec.SELF,
        {},
        6,
        None,
        None,
        1.0,
        ("exposure_act_count",),
        (),
        ("self_exposure",),
        False,
    ),
)
