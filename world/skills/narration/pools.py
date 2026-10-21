"""Shared authored narration pools.

Every mechanical entry kind renders from a multi-variant pool, with a
participant-free compact fallback that bounds the rendered line regardless of
how long an entity key is. Action clauses live on the skill/family rows; the
pools here are outcome clauses and must therefore declare at most one
participant slot so an action-plus-outcome pair stays inside the slot budget.

Internal-only kinds intentionally render an empty line: their entry exists to
carry a structured fact, and the text channel never printed prose for them.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .vocab import NarrationRow, RoleClause

#: Kinds that exist only as structured records and always render ``""``.
INTERNAL_KINDS = frozenset(
    {
        "combat_kill_xp",
        "knocked_out_mark",
        "divine_drain_actor",
        "gauge_transfer_actor",
        "damage_divert",
    }
)

#: Every kind the action pipeline and its combat prose surface can emit.
NARRATION_KINDS = (
    "resource_spend",
    "self_return_clear",
    "session_stamp",
    "rite_blessing",
    "rite_shelter",
    "skill_granted",
    "disguise_set",
    "disguise_lifted",
    "reveal_lifted",
    "reveal_noop",
    "buff_applied",
    "grants_revoked",
    "self_buff_applied",
    "buffs_cleansed",
    "equipment_immune",
    "sexual_transition",
    "sexual_resist",
    "pleasure_gain",
    "sexual_counter",
    "trait_delta",
    "roll",
    "damage",
    "heal",
    "self_heal",
    "target_defeated",
    "target_knocked_out",
    "disengage_attempt",
    "skill_practice",
    "divine_pleasure_max",
    "divine_climax_extension",
    "divine_drain",
    "divine_saturate_sensitivity",
    "divine_clamp_shame",
    "divine_mark_submission",
    "divine_restore_purity",
    "pleasure_peak",
    "gauge_transfer",
    "action_skipped",
    "party_retreat",
    "overwhelm_resolution",
    "commanded_action",
    "action_narration",
    *sorted(INTERNAL_KINDS),
)

_KIND_POOLS_SOURCE: dict[str, tuple[str, ...]] = {
    "resource_spend": (
        "{actor} 的魔力自指間流瀉而出。",
        "{actor} 將氣力壓進這一式裡。",
        "{actor} 的呼吸沉了下去，代價已然付出。",
    ),
    "self_return_clear": (
        "{actor} 重整架勢，回到自己的位置上。",
        "{actor} 收勢站定，目光重新鎖住對手。",
        "{actor} 腳步一錯，重新踏回戰陣。",
    ),
    "session_stamp": (
        "{actor} 將誓言刻進了自己的名字。",
        "{actor} 低聲立誓，某種重量落了下來。",
        "{actor} 把決心交了出去，再無退路。",
    ),
    "rite_blessing": (
        "{actor} 的兵刃泛起一層柔光。",
        "{actor} 的武備被聖意輕輕覆過。",
        "{actor} 感到掌心傳來一股安定的暖意。",
    ),
    "rite_shelter": (
        "{actor} 在聖所裡卸下了緊繃。",
        "{actor} 被一層看不見的庇護攏住。",
        "{actor} 的傷勢在安靜中慢慢平息。",
    ),
    "skill_granted": (
        "{target} 的動作裡多了一分不屬於自己的熟練。",
        "{target} 的身上留下了別人的技藝。",
        "{target} 忽然懂了某個原本不會的動作。",
    ),
    "disguise_set": (
        "{target} 的面貌換了一副模樣。",
        "{target} 的氣息被另一層外表蓋住。",
        "{target} 看上去已不再是自己。",
    ),
    "disguise_lifted": (
        "{target} 的偽裝像霧一樣散開。",
        "{target} 露出了原本的面貌。",
        "{target} 身上的假象褪得乾乾淨淨。",
    ),
    "reveal_lifted": (
        "{target} 的偽裝被看穿了。",
        "{target} 的真實面目浮現出來。",
        "{target} 藏不住原本的樣子。",
    ),
    "reveal_noop": (
        "{target} 的偽裝沒有露出破綻。",
        "{target} 仍穩穩藏在表象之後。",
        "{target} 看著毫無異樣。",
    ),
    "buff_applied": (
        "{target} 的身上浮起一層微光。",
        "{target} 感到力量沿著四肢鋪開。",
        "{target} 的狀態悄然改變。",
    ),
    "grants_revoked": (
        "{target} 身上的授予一條條斷開。",
        "{target} 失去了那些借來的力量。",
        "{target} 被收回了一切恩惠。",
    ),
    "self_buff_applied": (
        "{actor} 凝神聚力，氣息沉穩下來。",
        "{actor} 的身周亮起一圈淡淡的光。",
        "{actor} 把力量收進身體深處。",
    ),
    "buffs_cleansed": (
        "{target} 身上的陰影被洗淨。",
        "{target} 的異常狀態逐一消退。",
        "{target} 感到某種沉重被帶走了。",
    ),
    "equipment_immune": (
        "{target} 的裝備將這股力量擋在外面。",
        "{target} 身上的護具發出沉悶的聲響。",
        "{target} 的鎧甲把這道手段消於無形。",
    ),
    "sexual_transition": (
        "{target} 的呼吸微微一亂。",
        "{target} 的身體有了新的反應。",
        "{target} 的狀態悄悄越過了一道界線。",
    ),
    "sexual_resist": (
        "{target} 沒有立刻回應。",
        "{target} 的動作停了一拍。",
        "{target} 靜靜看著眼前的人。",
    ),
    "pleasure_gain": (
        "{target} 的快感一層層漫上來。",
        "{target} 的腰背不由自主地繃緊。",
        "{target} 的呼吸變得又淺又急。",
    ),
    "sexual_counter": (
        "{target} 的身上留下了這次的痕跡。",
        "{target} 的經歷又添了一筆。",
        "{target} 的身體記住了這一刻。",
    ),
    "trait_delta": (
        "{target} 感到一陣虛弱。",
        "{target} 的力量有了增減。",
        "{target} 的身體狀態改變了。",
    ),
    "roll": (
        "{target} 察覺到了逼近的攻勢。",
        "{target} 的動作慢了半分。",
        "{target} 抬起眼來。",
    ),
    "damage": (
        "{target} 悶哼一聲，退了半步。",
        "{target} 的身上添了一道傷。",
        "{target} 的呼吸亂了。",
    ),
    "heal": (
        "{target} 的傷口慢慢收攏。",
        "{target} 感到一股暖流覆上傷處。",
        "{target} 的臉色恢復了些許。",
    ),
    "self_heal": (
        "{actor} 的傷勢緩緩癒合。",
        "{actor} 重新站穩，氣息平復。",
        "{actor} 感到力氣一點點回來。",
    ),
    "target_defeated": (
        "{target} 的身影終於倒下。",
        "{target} 失去了還手的力量。",
        "{target} 倒在地上，不再動彈。",
    ),
    "target_knocked_out": (
        "{target} 眼前一黑，軟倒下去。",
        "{target} 失去意識，跌坐在地。",
        "{target} 的動作戛然而止。",
    ),
    "disengage_attempt": (
        "{actor} 尋找脫身的空隙。",
        "{actor} 試著從戰圈裡抽身。",
        "{actor} 的腳步朝外側挪去。",
    ),
    "skill_practice": (
        "{actor} 把這一式刻進身體裡。",
        "{actor} 的動作比先前更穩了些。",
        "{actor} 從這一擊裡學到了什麼。",
    ),
    "divine_pleasure_max": (
        "{target} 被推到了感官的盡頭。",
        "{target} 的意識在一瞬間被白光淹沒。",
        "{target} 再也承受不住地弓起身子。",
    ),
    "divine_climax_extension": (
        "{target} 的餘韻被硬生生拉長。",
        "{target} 沒能從那陣顫抖裡落下。",
        "{target} 被留在原處，動彈不得。",
    ),
    "divine_drain": (
        "{target} 的力量被抽走了一部分。",
        "{target} 感到自己正被慢慢掏空。",
        "{target} 的氣息黯淡下去。",
    ),
    "divine_saturate_sensitivity": (
        "{target} 的感官被推到極處。",
        "{target} 的肌膚對每一次觸碰都過分敏感。",
        "{target} 連空氣拂過都覺得難以承受。",
    ),
    "divine_clamp_shame": (
        "{target} 的羞恥被徹底剝去。",
        "{target} 再也不知道什麼叫難為情。",
        "{target} 對自己的處境毫無遮掩。",
    ),
    "divine_mark_submission": (
        "{target} 的意志被壓進塵土裡。",
        "{target} 的目光只剩下順從。",
        "{target} 不再想起違抗。",
    ),
    "divine_restore_purity": (
        "{target} 的身體回到最初的潔淨。",
        "{target} 身上的痕跡被抹平。",
        "{target} 像被重新洗過一般。",
    ),
    "pleasure_peak": (
        "{target} 被推上頂點，整個人繃緊。",
        "{target} 的意識在那一瞬碎裂。",
        "{target} 再也壓不住聲音。",
    ),
    "gauge_transfer": (
        "{target} 的量表被另一股力量牽動。",
        "{target} 感到某種東西正被移走。",
        "{target} 的狀態被重新分配。",
    ),
    "action_skipped": (
        "{actor} 被什麼絆住，沒能出手。",
        "{actor} 的動作停在半途。",
        "{actor} 這一刻動彈不得。",
    ),
    "party_retreat": (
        "{actor} 帶著隊伍朝戰圈外退去。",
        "{actor} 的出聲把眾人往後帶。",
        "{actor} 掩護著同伴後撤。",
    ),
    "overwhelm_resolution": (
        "{target} 的防線在轉瞬之間崩塌。",
        "{target} 連還手的機會都沒有。",
        "{target} 的敗勢已成。",
    ),
    "commanded_action": (
        "{actor} 依著先前的指示出手。",
        "{actor} 照著指令把動作做完。",
        "{actor} 順著既定的安排行動。",
    ),
    "action_narration": (
        "{actor} 催動了這一式。",
        "{actor} 將力量聚在掌心。",
        "{actor} 踏前一步，動作展開。",
    ),
}

KIND_POOLS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    dict(_KIND_POOLS_SOURCE)
)

_COMPACT_SOURCE: dict[str, str] = {
    "resource_spend": "氣力自指間流瀉。",
    "self_return_clear": "架勢重新穩住。",
    "session_stamp": "誓言已然立下。",
    "rite_blessing": "武備覆上了一層柔光。",
    "rite_shelter": "庇護靜靜降下。",
    "skill_granted": "借來的力量落了下來。",
    "disguise_set": "面貌換了一副。",
    "disguise_lifted": "偽裝散了。",
    "reveal_lifted": "偽裝被看穿了。",
    "reveal_noop": "偽裝沒有破綻。",
    "buff_applied": "一層微光浮現。",
    "grants_revoked": "授予盡數收回。",
    "self_buff_applied": "氣息沉穩下來。",
    "buffs_cleansed": "陰影被洗淨。",
    "equipment_immune": "裝備擋下了這股力量。",
    "sexual_transition": "身體有了新的反應。",
    "sexual_resist": "對方沒有立刻回應。",
    "pleasure_gain": "快感漫了上來。",
    "sexual_counter": "身上留下了痕跡。",
    "trait_delta": "身體狀態改變了。",
    "roll": "攻勢逼近。",
    "damage": "傷勢添了一筆。",
    "heal": "傷口慢慢收攏。",
    "self_heal": "傷勢緩緩癒合。",
    "target_defeated": "身影終於倒下。",
    "target_knocked_out": "意識中斷了。",
    "disengage_attempt": "尋找脫身的空隙。",
    "skill_practice": "這一式留下了痕跡。",
    "divine_pleasure_max": "感官被推到盡頭。",
    "divine_climax_extension": "餘韻被拉長了。",
    "divine_drain": "力量被抽走了一部分。",
    "divine_saturate_sensitivity": "感官被推到極處。",
    "divine_clamp_shame": "羞恥被剝去了。",
    "divine_mark_submission": "意志被壓了下去。",
    "divine_restore_purity": "身體回到潔淨。",
    "pleasure_peak": "被推上了頂點。",
    "gauge_transfer": "量表被牽動。",
    "action_skipped": "沒能出手。",
    "party_retreat": "隊伍退出了戰圈。",
    "overwhelm_resolution": "防線徹底崩塌。",
    "commanded_action": "依令行動。",
    "action_narration": "這一式展開。",
}

COMPACT_POOLS: Mapping[str, str] = MappingProxyType(dict(_COMPACT_SOURCE))

#: The template every entry starts from before narration selection runs.
FALLBACK_TEMPLATES: Mapping[str, str] = MappingProxyType(
    {
        **dict(_COMPACT_SOURCE),
        **{kind: "" for kind in INTERNAL_KINDS},
    }
)


HIT_LINES = (
    "這一擊扎扎實實落在 {target} 身上。",
    "{target} 沒能完全避開。",
    "攻勢破開了 {target} 的防備。",
)

MISS_LINES = (
    "{target} 側身避開了這一擊。",
    "攻勢擦著 {target} 的衣角落空。",
    "{target} 早已不在原處。",
)

DAMAGE_BAND_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "graze": (
            "{target} 只被擦出一道淺痕。",
            "{target} 幾乎沒受影響。",
            "{target} 偏了偏身，傷得不重。",
        ),
        "light": (
            "{target} 的傷口淺而清晰。",
            "{target} 皺了下眉。",
            "{target} 退了半步，傷勢不深。",
        ),
        "solid": (
            "{target} 悶哼一聲，摀住傷處。",
            "{target} 的動作明顯慢了下來。",
            "{target} 的身影晃了一下。",
        ),
        "heavy": (
            "{target} 幾乎站不穩。",
            "血順著 {target} 的指縫滴落。",
            "{target} 的呼吸變得破碎。",
        ),
        "dire": (
            "{target} 的身子幾乎被折斷。",
            "{target} 眼前發黑，幾乎倒下。",
            "{target} 只憑一口氣撐著。",
        ),
    }
)

HEAL_BAND_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "minor": (
            "{target} 的傷口淺淺收攏。",
            "{target} 感到一絲暖意。",
            "{target} 的疼痛輕了些。",
        ),
        "restoring": (
            "{target} 的傷勢明顯好轉。",
            "{target} 的力氣回來了一些。",
            "{target} 的呼吸平穩下來。",
        ),
        "bountiful": (
            "{target} 的傷口迅速癒合。",
            "{target} 幾乎恢復了全盛。",
            "{target} 感到生命力重新湧上。",
        ),
    }
)

SELF_HEAL_BAND_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "minor": (
            "{actor} 的傷口不再滲血。",
            "{actor} 感到一點暖意。",
            "{actor} 的疼痛減輕了。",
        ),
        "restoring": (
            "{actor} 的傷勢明顯好轉。",
            "{actor} 的力氣正在回來。",
            "{actor} 的呼吸穩了下來。",
        ),
        "bountiful": (
            "{actor} 的傷口迅速閉合。",
            "{actor} 幾乎恢復了全盛。",
            "{actor} 感到生命力重新湧上。",
        ),
    }
)

VERDICT_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "resist": (
            "{target} 輕輕別過臉，拒絕了這場靠近。",
            "{target} 抬手擋住，沒有退讓。",
            "{target} 的態度明白而堅決。",
        ),
        "auto_comply": (
            "{target} 像是早已放棄抵抗，任由對方靠近。",
            "{target} 沒有閃避，也沒有出聲。",
            "{target} 順著那股力道，自己迎了上去。",
        ),
        "comply": (
            "{target} 沒有拒絕，呼吸亂了拍子。",
            "{target} 的眼神動搖，最後什麼也沒說。",
            "{target} 微微垂下眼，默許了這一刻。",
        ),
    }
)

PLEASURE_ACTOR_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "faint": (
            "{actor} 感到一絲細微的熱意。",
            "{actor} 的心跳快了半拍。",
            "{actor} 的身體輕輕一顫。",
        ),
        "clear": (
            "{actor} 的呼吸明顯亂了。",
            "{actor} 感到熱意一路蔓延。",
            "{actor} 的手指微微收緊。",
        ),
        "strong": (
            "{actor} 幾乎站不穩。",
            "{actor} 的意識被那陣浪潮推著走。",
            "{actor} 咬住下唇，仍壓不住聲音。",
        ),
        "overwhelming": (
            "{actor} 的意識被整個捲走。",
            "{actor} 眼前一白，什麼也想不到。",
            "{actor} 徹底沉進那片浪裡。",
        ),
    }
)

PLEASURE_TARGET_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "faint": (
            "{target} 的身子輕輕一顫。",
            "{target} 的呼吸亂了一拍。",
            "{target} 察覺到那點細微的異樣。",
        ),
        "clear": (
            "{target} 的臉上浮起紅暈。",
            "{target} 的聲音變得又輕又軟。",
            "{target} 忍不住縮了一下。",
        ),
        "strong": (
            "{target} 的腰背繃得緊緊的。",
            "{target} 幾乎要站不住。",
            "{target} 的思緒被攪成一團。",
        ),
        "overwhelming": (
            "{target} 徹底失了神。",
            "{target} 的意識被推過了界線。",
            "{target} 只能任由身體自己做主。",
        ),
    }
)

SEXUAL_COUNTER_ACTOR_LINES = (
    "{actor} 明白自己剛才做了什麼。",
    "{actor} 把這一刻收進記憶裡。",
    "{actor} 的身上留下了主動的痕跡。",
)

SEXUAL_COUNTER_SHARED_LINES = (
    "{target} 與對方的身體都記住了這一刻。",
    "{target} 身上的痕跡屬於兩個人。",
    "{target} 的經歷裡多了一頁共同的記錄。",
)

#: One performer clause and one participant clause per lifetime counter any
#: act can credit. The key set is derived from the act catalogue and validated
#: for exact equality at import, so a new counter cannot narrate generically.
SEXUAL_COUNTER_LINES: Mapping[str, RoleClause] = MappingProxyType(
    {
        "duo_act_count": RoleClause(
            performer=(
                "{actor} 記得自己的身體剛才做了什麼。",
                "{actor} 把這一刻收進了自己的記憶。",
            ),
            participant=(
                "{target} 與對方的身體一起記住了這一刻。",
                "{target} 的經歷裡多了一頁兩個人的紀錄。",
            ),
        ),
        "group_act_count": RoleClause(
            performer=(
                "{actor} 在眾人之間留下了自己的那一份。",
                "{actor} 記得自己主動走進了這場熱鬧。",
            ),
            participant=(
                "{target} 與在場的人共有這一頁。",
                "{target} 的身上留著一屋子人的溫度。",
            ),
        ),
        "hostile_act_count": RoleClause(
            performer=(
                "{actor} 知道自己把刀鋒換成了別的手段。",
                "{actor} 把這一手收進記憶裡。",
            ),
            participant=(
                "{target} 與對手之間多了一筆帳。",
                "{target} 的身上留下了敵意的痕跡。",
            ),
        ),
        "interspecies_act_count": RoleClause(
            performer=(
                "{actor} 記得自己主動碰過那副陌生的身體。",
                "{actor} 的手上還留著不屬於人的溫度。",
            ),
            participant=(
                "{target} 的身上留下了異種的痕跡。",
                "{target} 與那副陌生的身體之間有了紀錄。",
            ),
        ),
        "masturbation_count": RoleClause(
            performer=(
                "{actor} 一個人把這件事做完了。",
                "{actor} 記得這是只屬於自己的時刻。",
            ),
            participant=(
                "{target} 成了那場獨處的一部分。",
                "{target} 的身上留下了獨處的餘溫。",
            ),
        ),
        "toy_use_count": RoleClause(
            performer=(
                "{actor} 記得那具玩具碰過自己哪裡。",
                "{actor} 的身體記下了玩具的觸感。",
            ),
            participant=(
                "{target} 知道那具玩具也碰過自己。",
                "{target} 的身上留著器具壓過的痕跡。",
            ),
        ),
        "exposure_act_count": RoleClause(
            performer=(
                "{actor} 把自己攤在光裡，這一刻被記下了。",
                "{actor} 記得自己主動掀開了遮掩。",
            ),
            participant=(
                "{target} 也看見了這一身毫無遮掩。",
                "{target} 的眼裡多了一幕不該看的畫面。",
            ),
        ),
        "watched_count": RoleClause(
            performer=(
                "{actor} 知道自己被看著。",
                "{actor} 記得那些落在自己身上的視線。",
            ),
            participant=(
                "{target} 被收進了旁人的眼底。",
                "{target} 知道有人正看著這一幕。",
            ),
        ),
    }
)

TRAIT_DELTA_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "hp": (
            "{target} 的生命力被抽走了一些。",
            "{target} 的臉色變得蒼白。",
            "{target} 感到身體正在流失什麼。",
        ),
        "mp": (
            "{target} 的魔力淡了下去。",
            "{target} 感到體內的流動變慢了。",
            "{target} 的指尖失去了光。",
        ),
        "sp": (
            "{target} 的體力見了底。",
            "{target} 的四肢變得沉重。",
            "{target} 連抬起手都有些吃力。",
        ),
    }
)

TRANSITION_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "self_exposure": (
            "{target} 將自己暴露在他人眼前。",
            "{target} 不再遮掩自己的樣子。",
            "{target} 讓視線落在自己身上。",
        ),
        "public_exposure": (
            "{target} 的模樣落進了眾人的眼裡。",
            "{target} 在旁人面前失去了遮掩。",
            "{target} 任由自己被人看見。",
        ),
        "masturbation_climax": (
            "{target} 在獨自的動作裡抵達頂點。",
            "{target} 一個人走到了那一步。",
            "{target} 的獨處被自己打斷。",
        ),
        "watched_during_activity": (
            "{target} 知道有人在看。",
            "{target} 察覺到那道視線。",
            "{target} 的動作被旁人收入眼底。",
        ),
        "public_sexual_activity": (
            "{target} 的舉動落進了旁人眼裡。",
            "{target} 沒有避開眾人的目光。",
            "{target} 讓這一幕發生在公開之處。",
        ),
        "breast_sex_performed": (
            "{target} 的胸口留下了溫熱的觸感。",
            "{target} 感到胸前一片燙。",
            "{target} 的呼吸壓在柔軟的觸感裡。",
        ),
        "sexual_activity_with_nonhuman": (
            "{target} 的身體記住了非人的觸感。",
            "{target} 被不屬於人的溫度包住。",
            "{target} 的經驗裡多了一道異樣的痕跡。",
        ),
        "first_vaginal_penetration": (
            "{target} 的身子越過了一道再回不去的界線。",
            "{target} 從這一刻起不再是原本的樣子。",
        ),
        "penetrative_sex_with_female": (
            "{target} 與對方的身體在這一下裡分不出彼此。",
            "{target} 的界線被另一副身體徹底打開。",
        ),
        "penetrative_sex_with_male": (
            "{target} 與對方之間那條界線不再存在。",
            "{target} 在貼合之中失去了距離。",
        ),
        "stimulus_applied": (
            "{target} 的感官被直接撩起。",
            "{target} 的皮膚忽然變得格外敏感。",
            "{target} 被一股看不見的力道掃過全身。",
        ),
    }
)

COMMANDED_ACTION_LINES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "skill": (
            "{actor} 依令出手，招式順著先前的指示展開。",
            "{actor} 照著指令把這一式完整施展。",
            "{actor} 的動作沿著既定的安排落下。",
        ),
        "item": (
            "{actor} 依令取用道具，動作一氣呵成。",
            "{actor} 照著指令把準備好的東西用上。",
            "{actor} 翻手取出道具，依令而行。",
        ),
    }
)

GENERIC_ACTION_LINES = (
    "{actor} 催動了這一式。",
    "{actor} 將力量聚在掌心。",
    "{actor} 踏前一步，動作展開。",
)

#: Every special pool the selector can draw from. Validation walks this map so
#: the authoring guarantee covers the actual runtime selection surface, not
#: only ``KIND_POOLS`` and per-row overrides.
SPECIAL_POOLS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "hit": HIT_LINES,
        "miss": MISS_LINES,
        **{f"damage:{band}": lines for band, lines in DAMAGE_BAND_LINES.items()},
        **{f"heal:{band}": lines for band, lines in HEAL_BAND_LINES.items()},
        **{
            f"self_heal:{band}": lines
            for band, lines in SELF_HEAL_BAND_LINES.items()
        },
        **{f"verdict:{key}": lines for key, lines in VERDICT_LINES.items()},
        **{
            f"pleasure_actor:{key}": lines
            for key, lines in PLEASURE_ACTOR_LINES.items()
        },
        **{
            f"pleasure_target:{key}": lines
            for key, lines in PLEASURE_TARGET_LINES.items()
        },
        "sexual_counter_actor": SEXUAL_COUNTER_ACTOR_LINES,
        "sexual_counter_shared": SEXUAL_COUNTER_SHARED_LINES,
        **{
            f"sexual_counter:{name}:{role}": clause.for_role(role == "performer")
            for name, clause in SEXUAL_COUNTER_LINES.items()
            for role in ("performer", "participant")
        },
        **{
            f"trait_delta:{key}": lines
            for key, lines in TRAIT_DELTA_LINES.items()
        },
        **{
            f"transition:{key}": lines
            for key, lines in TRANSITION_LINES.items()
        },
        **{
            f"commanded:{key}": lines
            for key, lines in COMMANDED_ACTION_LINES.items()
        },
        "generic_action": GENERIC_ACTION_LINES,
    }
)

#: Structural combat prose. Single stable lines on purpose (design D10).
CONTINUE_MESSAGE = "刀光未歇，下一輪交手已然開始。"

TERMINAL_OUTCOME_MESSAGES: Mapping[str, str] = MappingProxyType(
    {
        "victory": "最後一擊落下，廝殺聲終於平息——你贏了。",
        "defeat": "你被擊敗了，意識沉入黑暗，許久之後才在原地醒轉。",
        "fled": "你抽身退去，把廝殺聲留在身後。",
        "exam_passed": "考核官的評語落下，你正式跨過了這道門檻。",
        "exam_failed": "考核官的評語落下，這次你沒能跨過門檻。",
        "cap": "戰線拖得太長，雙方在疲憊中停手。",
    }
)

ENGAGEMENT_OPENING_TEMPLATE = "你搶先一步，朝{name}逼了上去。"

OVERWHELM_SUMMARY_LINE = "{target} 的防線在壓倒性的攻勢下徹底崩塌。"

PARTY_RETREAT_LINES: Mapping[str, str] = MappingProxyType(
    {
        "escaped": "隊伍甩開了追擊，退出了戰圈。",
        "failed": "隊伍試著後撤，卻被對方纏住。",
    }
)

#: Kinds whose selected clause is composed behind the skill's action clause.
COMPOSABLE_KINDS = frozenset(kind for kind in NARRATION_KINDS)


__all__ = [
    "COMMANDED_ACTION_LINES",
    "COMPACT_POOLS",
    "COMPOSABLE_KINDS",
    "CONTINUE_MESSAGE",
    "DAMAGE_BAND_LINES",
    "ENGAGEMENT_OPENING_TEMPLATE",
    "FALLBACK_TEMPLATES",
    "GENERIC_ACTION_LINES",
    "HIT_LINES",
    "HEAL_BAND_LINES",
    "INTERNAL_KINDS",
    "KIND_POOLS",
    "MISS_LINES",
    "NARRATION_KINDS",
    "OVERWHELM_SUMMARY_LINE",
    "PARTY_RETREAT_LINES",
    "PLEASURE_ACTOR_LINES",
    "PLEASURE_TARGET_LINES",
    "SEXUAL_COUNTER_ACTOR_LINES",
    "SEXUAL_COUNTER_LINES",
    "SEXUAL_COUNTER_SHARED_LINES",
    "SELF_HEAL_BAND_LINES",
    "SPECIAL_POOLS",
    "TERMINAL_OUTCOME_MESSAGES",
    "TRAIT_DELTA_LINES",
    "TRANSITION_LINES",
    "VERDICT_LINES",
]
