"""Hand-written deterministic quest catalog (quest-runtime D-2).

Content here uses only permanent world content and no AI services. The
introductory hunt completes through ordinary ``ActionResolver`` combat; change
16 supplies the player-facing accept/combat-entry/turn-in that turns this into
a playable milestone.

The regional species hunts below are the approved published content of
``monster-regional-species-hunts`` (user balance approval of 2026-10-06, landed
by ``monster-balance-profiles``): one hunt per (region, species) pair the
authored ambient placement covers. Numbers and narrative are literals — each
value is the approved value transcribed verbatim, never re-derived, re-tuned,
or interpolated from a display name, a threat tier, another definition, or a
variant's individual danger grade.

The bound site clear-outs below are the approved published content of
``monster-site-clear-out-hunts`` (the same approval): each names one authored
site, binds exactly that site's own living individuals as its targets, and
carries its own authored rank, rationale, flavor, and rank-banded reward. They
are the hand-written half of the objective vocabulary — the compile boundary
never authors a site key — and their prose states the local conflict at the site
rather than an effect of an ability that has no executable mechanics.
"""

from .definitions import (
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)


INTRODUCTORY_HUNT = QuestDefinition(
    key="introductory_hunt",
    display_name="討伐低階魔物",
    quest_type=QuestType.DEFEAT,
    rank="F",
    stages=(
        QuestStage(
            index=0,
            objective=QuestObjective(
                kind=ObjectiveKind.DEFEAT,
                quantity=1,
                monster_tier="low",
            ),
        ),
    ),
    deadline_hours=None,
)

#: The approved regional species hunts (``monster-regional-species-hunts``).
#: Coverage is derived from the authored ambient placement, never invented: the
#: countable variants are the species' ordinary baseline plus its stronger
#: partner (so a qualifying stronger individual counts once), the quantity sits
#: at the region's authored per-coordinate legal supply ``min(quantity,
#: capacity)``, and no hunt asks for more than its region can legally provision.
#: ``southeast_coast`` carries no hunt because it has no authored ambient rule,
#: so a hunt there could never be satisfied by construction; its species
#: presence is published as bound site content instead.
#: Ranks are authored from the arrangement — group composition, numbers, and
#: terrain — and never from a countable variant's individual danger grade: the
#: two mid hunts stay ``D`` although their strongest countable variant is graded
#: ``C``. ``background_flavor_zh`` carries the bestiary's approved commission
#: background for the species; ``rating_rationale_zh`` is authored beside it.
#: No published prose asserts an effect of one of the six approved special
#: abilities, none of which has executable mechanics yet. No hunt carries a
#: deadline (design D-R8).
REGIONAL_SPECIES_HUNTS: tuple[QuestDefinition, ...] = (
    QuestDefinition(
        key="eastern_plains_sway_whistle_sparrow",
        display_name="驅除東部平原穗鳴雀",
        quest_type=QuestType.DEFEAT,
        rank="F",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=2,
                    region_key="eastern_plains",
                    species_key="sway_whistle_sparrow",
                    countable_variant_keys=("grain_pecker", "flock_leader"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "低階群居鳥類，較強個體會自不同方向干擾驅趕者；"
            "個體不難應付，但數量分散，取巧不易。"
        ),
        background_flavor_zh=(
            "收穫已近尾聲，東側田區每天清晨仍有成群穗鳴雀來訪。"
            "農戶請公會處理持續侵入的族群，以免今年最後一批穀物留不下來。"
        ),
    ),
    QuestDefinition(
        key="eastern_plains_ridge_burrow_hare",
        display_name="驅除東部平原築埂兔",
        quest_type=QuestType.DEFEAT,
        rank="F",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=2,
                    region_key="eastern_plains",
                    species_key="ridge_burrow_hare",
                    countable_variant_keys=("burrow_maker", "nest_guard"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "平原鬆土讓牠們容易鑽回洞道，護巢型又會加固入口；"
            "個體不強，逐一找出田埂間的巢口才是難處。"
        ),
        background_flavor_zh=(
            "平原邊緣的鬆土帶出現新的築埂兔巢，坑洞妨礙農具與牲畜通行。"
            "農戶請公會清除這一帶的族群，讓田間作業恢復。"
        ),
    ),
    QuestDefinition(
        key="northwest_highland_forest_fog_mane_lynx",
        display_name="討伐西北高地森林霧鬃山貓",
        quest_type=QuestType.DEFEAT,
        rank="D",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    region_key="northwest_highland_forest",
                    species_key="fog_mane_lynx",
                    countable_variant_keys=("wood_stalker", "trail_hunter"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "中階獵食者會反覆試探隊伍邊緣，避開完整隊列；"
            "高地森林的晨霧讓接近方向難以判斷，落單的人風險明顯上升。"
        ),
        background_flavor_zh=(
            "高地運輸隊連續在晨霧中失去馱獸，獵人找到的足跡始終沿道路外緣移動。"
            "部族請公會處理已開始追逐運輸隊的個體。"
        ),
    ),
    QuestDefinition(
        key="southwest_coast_tide_lamp_crab",
        display_name="清理西南海岸潮燈蟹",
        quest_type=QuestType.DEFEAT,
        rank="E",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    region_key="southwest_coast",
                    species_key="tide_lamp_crab",
                    countable_variant_keys=("shore_walker", "reef_warden"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "低階甲殼類，但守礁型占據狹窄洞口，防禦遠高於同階個體；"
            "礁隙與潮池讓隊伍無法展開，只能逐處清理。"
        ),
        background_flavor_zh=(
            "港外的候船燈附近聚集了一批潮燈蟹，已有夜歸小船認錯泊岸方向。"
            "碼頭請公會清理這處聚集地，恢復燈號辨識。"
        ),
    ),
    QuestDefinition(
        key="western_hills_valleys_ridge_burrow_hare",
        display_name="清理西部丘陵築埂兔",
        quest_type=QuestType.DEFEAT,
        rank="E",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    region_key="western_hills_valleys",
                    species_key="ridge_burrow_hare",
                    countable_variant_keys=("burrow_maker", "nest_guard"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "谷地的築埂兔沿灌溉渠築巢，土埂堵住分水口；"
            "渠岸狹窄又讓較強個體難以繞過，得在水道旁動手。"
        ),
        background_flavor_zh=(
            "兩戶農家原以為渠水不足是分水爭議，查找後才發現分水口旁有築埂兔巢。"
            "公會受託處理占據渠岸的族群，讓灌溉恢復。"
        ),
    ),
    QuestDefinition(
        key="western_hills_valleys_rock_echo_goat",
        display_name="討伐西部丘陵岩響山羊",
        quest_type=QuestType.DEFEAT,
        rank="D",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    region_key="western_hills_valleys",
                    species_key="rock_echo_goat",
                    countable_variant_keys=("cliff_stepper", "pass_warden"),
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "中階個體，守隘型會守住岩坡入口；"
            "坡面狹窄、碎石鬆動，隊伍難以同時展開，只能沿單側接近。"
        ),
        background_flavor_zh=(
            "採石場的運料路被岩響山羊占據。工人能聽見上方敲岩聲，卻不敢再推車通過。"
            "業主請公會處理守路個體，重新開通運料線。"
        ),
    ),
)

#: The approved bound site clear-outs (``monster-site-clear-out-hunts``).
#: Each objective is a DEFEAT stage declaring ``requires_bound_targets=True``
#: plus the key of one authored site, so acceptance binds that site's own living
#: individuals — the site is a source, never a spawn — and its quantity never
#: exceeds the site's authored capacity.
#: Ranks are authored from the arrangement, exactly as the hunts' are: the
#: recurrable camp and the single sheltered boss site stay ``D`` although their
#: strongest individual is danger-graded ``C``, so the shipped content again
#: demonstrates that a grade never supplies a rank. The one-shot nest is ``E``:
#: a low-tier bound pair, including the stronger guard, in a narrow entrance.
#: No published rationale or flavor asserts an effect of one of the six approved
#: special abilities, none of which has executable mechanics; each states the
#: composition and terrain instead (the crocodile's flavor names the berth
#: conflict rather than the bestiary example's drain symptom, and the goat's
#: rationale describes narrow loose-scree terrain rather than rockfall). No
#: clear-out carries a deadline, and the three below are the only definitions
#: that declare each of their sites.
SITE_CLEAR_OUTS: tuple[QuestDefinition, ...] = (
    QuestDefinition(
        key="ridge_burrow_nest_clear_out",
        display_name="清剿掘巢兔巢穴",
        quest_type=QuestType.DEFEAT,
        rank="E",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=2,
                    requires_bound_targets=True,
                    site_key="ridge_burrow_nest",
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "據點入口狹窄，較強個體會擋在通道上；兩隻綁定目標必須一次清除，"
            "洞道又妨礙隊伍輪替。"
        ),
        background_flavor_zh=(
            "谷地的灌溉渠岸出現一整片加固過的土埂，渠水已被堵住。"
            "公會受託一次清出這個巢穴，讓下游恢復供水。"
        ),
    ),
    QuestDefinition(
        key="cliff_echo_camp_clear_out",
        display_name="掃蕩回聲崖營地",
        quest_type=QuestType.DEFEAT,
        rank="D",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=2,
                    requires_bound_targets=True,
                    site_key="cliff_echo_camp",
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "岩坡入口的營地，兩隻中階個體會守住通道；坡面狹窄、碎石鬆動，"
            "隊伍只能沿單側接近，撤退也不容易。"
        ),
        background_flavor_zh=(
            "採石場上方的營地再度聚集岩響山羊，運料路每天都有人被趕下山坡。"
            "業主請公會一次掃蕩整座營地。"
        ),
    ),
    QuestDefinition(
        key="tide_mouth_boss_site_clear_out",
        display_name="清剿河口守灣鱷",
        quest_type=QuestType.DEFEAT,
        rank="D",
        stages=(
            QuestStage(
                index=0,
                objective=QuestObjective(
                    kind=ObjectiveKind.DEFEAT,
                    quantity=1,
                    requires_bound_targets=True,
                    site_key="tide_mouth_boss_site",
                ),
            ),
        ),
        deadline_hours=None,
        rating_rationale_zh=(
            "單一個體，但佔據有遮蔽的泊岸入口；水深妨礙長兵器展開，"
            "近身纏鬥的風險集中在一次交手。"
        ),
        background_flavor_zh=(
            "河口渡運站的側灣出現吞潮鱷，船員已停用該泊位。"
            "渡運站請公會清出這條水道，讓貨船重新靠岸。"
        ),
    ),
)


QUEST_CATALOG: tuple[QuestDefinition, ...] = (
    INTRODUCTORY_HUNT,
    *REGIONAL_SPECIES_HUNTS,
    *SITE_CLEAR_OUTS,
)


def register_catalog() -> None:
    """Register every catalog definition idempotently."""
    for definition in QUEST_CATALOG:
        register_quest_definition(definition)