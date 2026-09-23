"""Registry data slice: the Light Church clergy block (Series A/B/D).

The ordination-ladder rows appended by ``implement-church-redemption``
(design 2026-09-22 §5.5): ``vow_of_service`` plus the eight Series B rite
actives and the four Series D sexual-ministry actives. ``ROWS`` is the
contiguous, in-order entry block the assembly concatenates LAST, so every
pre-existing registry row keeps its observable position.

Declarations only by design: the combat rails of ``rite_lamb_mark`` /
``rite_martyrdom_vow`` land with ``implement-church-combat-ministry``, the
cast mechanics of the remaining rites (heal/cleanse/buff lanes) and the
ministry acts are future content, and ``vow_of_service``'s ledger
multipliers ride the ``church.yaml`` ``passive_effects`` rows consumed by
``world/rules/church.py`` — the row itself declares no effect rail, exactly
like the pre-existing clergy qualifier passives in ``data_utility_passives``.
The three Series A legacy passives (``pain_to_pleasure``, ``priestly_grace``,
``rapture_renewal``) stay in their original slice: catalogue entry is a
``REDEEM_CATALOG`` fact, never a row move (design decision D2).
"""

from world.skills.registry.builders import (
    _skill,
)

from world.skills.registry.vocab import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

ROWS: tuple[SkillDef, ...] = (
        # ---- Series A (4th clergy qualifier; the three legacy passives
        # stay in data_utility_passives) ----
        _skill(
            "vow_of_service",
            "侍奉之誓",
            "向教會立下侍奉之誓：獻上服務的銅錢收入與恩寵累積獲得神聖加乘，純粹增益。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        # ---- Series B — rite actives (8) ----
        _skill(
            "rite_heal_light",
            "光癒聖禮",
            "施行光癒聖禮，為單一目標恢復少量生命力。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_cleanse",
            "淨滌聖禮",
            "施行淨滌聖禮，解除單一目標一個負面狀態。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_calm",
            "鎮靜聖禮",
            "施行鎮靜聖禮，將目標的快感帶向平靜，不施加任何刺激。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_bless_water",
            "祝聖聖水",
            "以聖水祝聖，賦予單一目標短暫的神聖祝福。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_sanctify_ground",
            "聖化領域",
            "聖化腳下土地，使範圍內的友方沐浴聖光並削弱敵方。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_absolution",
            "赦罪聖禮",
            "施行赦罪聖禮，將目標的狀態洗滌歸正並解除負面效果。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_lamb_mark",
            "代贖羔印",
            "在自己身上烙下代贖羔印，吸引敵方的攻擊（代贖之力由教會聖儀授予）。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        _skill(
            "rite_martyrdom_vow",
            "殉者之誓",
            "立下殉者之誓，將自己獻為戰敗時的犧牲者（殉道之力由教會聖儀授予）。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            element="light",
            category=SkillCategory.ENHANCEMENT,
        ),
        # ---- Series D — sexual-ministry actives (4; doubling as advanced
        # OFFERING_CATALOG rows through the shared act key) ----
        _skill(
            "rite_anointing_touch",
            "聖油敷禮",
            "以聖油敷禮，喚起伴侶的潤澤與興奮。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            category=SkillCategory.SEXUAL_ACT,
            group="聖禮",
        ),
        _skill(
            "rite_milk_blessing",
            "聖乳祝福",
            "輕柔的授乳聖儀，為伴侶帶來滋養與安寧。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            category=SkillCategory.SEXUAL_ACT,
            group="聖禮",
        ),
        _skill(
            "rite_holy_kiss",
            "聖吻聖儀",
            "以聖吻施行聖儀，推動伴侶的快感並喚起持續治癒。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            category=SkillCategory.SEXUAL_ACT,
            group="聖禮",
        ),
        _skill(
            "rite_confession_bed",
            "告解之床",
            "在告解之床獻上自身，雙方高潮後的恩寵彼此流淌。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            category=SkillCategory.SEXUAL_ACT,
            group="聖禮",
        ),
)