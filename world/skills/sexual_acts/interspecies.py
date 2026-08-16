"""異種線 (interspecies line): acts performed against monsters.

Seven counter-gated acts across four tiers: two at
``hostile_act_count >= 10`` (觸碰異種, 異種愛撫), two at
``hostile_act_count >= 30`` (異種纏繞, 承受異種 — the latter carrying the
catalog's highest one-way actor ratio, 0.9), one compound-gated on
``hostile_act_count >= 30`` and ``climax_count >= 20`` (異種交合, the sole
emitter of ``sexual_activity_with_nonhuman``), and two at
``interspecies_act_count >= 20`` (異種支配, 異種共鳴).

Every act targets a single entity and declares no ``target_part``: 異種 is a
parless line, so the target always resolves to ``GENERIC_BODY_PART`` through
``resolve_part``'s ``Monster`` collapse. Every act credits
``interspecies_act_count`` on the actor only — a ``Monster`` target is never
credited a lifetime counter, matching the asymmetric crediting the combat
line established for hostile targets.
"""

from world.skills.registry import SkillDef, TargetSpec
from world.skills.sexual_acts._builder import SexualActDef, _act_family

INTERSPECIES_ACTS: tuple[tuple[SkillDef, SexualActDef], ...] = _act_family(
    "異種",
    (
        "interspecies_touch",
        "觸碰異種",
        "以掌心撫上異種的身軀，感受與人類截然不同的溫度和觸感。",
        TargetSpec.SINGLE,
        {"hostile_act_count": 10},
        12,
        "腰腹",
        None,
        0.5,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
    (
        "interspecies_caress",
        "異種愛撫",
        "沿著異種的輪廓細膩愛撫，讓陌生的快感在指間蔓延。",
        TargetSpec.SINGLE,
        {"hostile_act_count": 10},
        14,
        "私處",
        None,
        0.6,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
    (
        "interspecies_entangle",
        "異種纏繞",
        "任由異種的肢體纏上腰腹，在絞纏與擠壓之中尋求快感。",
        TargetSpec.SINGLE,
        {"hostile_act_count": 30},
        18,
        "腰腹",
        None,
        0.7,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
    (
        "interspecies_receive",
        "承受異種",
        "敞開身體承受異種的衝撞，讓對方在自己的體內留下痕跡。",
        TargetSpec.SINGLE,
        {"hostile_act_count": 30},
        18,
        "私處",
        None,
        0.9,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
    (
        "interspecies_mating",
        "異種交合",
        "與異種深深交合，跨越物種的隔閡交換體內的熱度。",
        TargetSpec.SINGLE,
        {"hostile_act_count": 30, "climax_count": 20},
        26,
        "私處",
        None,
        0.7,
        ("interspecies_act_count",),
        (),
        ("sexual_activity_with_nonhuman",),
        True,
    ),
    (
        "interspecies_domination",
        "異種支配",
        "騎上異種的身軀，以大腿夾緊對方的動作宣示支配。",
        TargetSpec.SINGLE,
        {"interspecies_act_count": 20},
        22,
        "大腿",
        None,
        0.6,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
    (
        "interspecies_resonance",
        "異種共鳴",
        "將異種攬入懷中貼近胸口，讓彼此的律動融為一體。",
        TargetSpec.SINGLE,
        {"interspecies_act_count": 20},
        22,
        "乳房",
        None,
        0.6,
        ("interspecies_act_count",),
        (),
        (),
        True,
    ),
)
