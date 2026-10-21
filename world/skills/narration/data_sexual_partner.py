"""Per-act narration for the 關係 (partner) line.

The register is closeness rather than spectacle: a hand that slows down, a
body leaning in, attention paid to one other person. Every attempt clause ends
on a turn that the shared verdict clause completes, so a refused cast never
claims a touch it did not have. Each row also voices its own pleasure clause
for the acting body and for the receiving body, because only the act knows
where it is aimed.

``ROWS`` follows the act registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "partner_caress",
        action=(
            "{actor} 的掌心朝對方的腰腹貼近。",
            "{actor} 把手放輕，順著對方身側探去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腰腹在掌心下逐漸熱起來。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的腰腹隨著撫觸一陣接一陣發軟。",),
        },
    ),
    NarrationRow(
        "partner_hand_hold",
        action=(
            "{actor} 伸手，朝對方攤開的掌心靠去。",
            "{actor} 把手指張開，等著與對方交扣。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的掌心被交扣的指尖燙了一下。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的手指被逐根扣住。",),
        },
    ),
    NarrationRow(
        "partner_kiss",
        action=(
            "{actor} 微側著頭，朝那雙唇靠近。",
            "{actor} 垂下眼，把臉湊向對方的唇。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的唇上還留著方才的溫度。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的唇齒之間漫進一陣熱。",),
        },
    ),
    NarrationRow(
        "partner_neck_caress",
        action=(
            "{actor} 的指尖朝對方的頸側探去。",
            "{actor} 俯身，把唇湊近那截頸項。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的頸側也跟著發燙。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的頸項在指下繃緊。",),
        },
    ),
    NarrationRow(
        "partner_breast_play",
        action=(
            "{actor} 抬手，朝對方胸前探去。",
            "{actor} 的指節隔著衣料抵近那處柔軟。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的胸口跟著泛起一陣脹。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的胸前在揉弄下繃了起來。",),
        },
    ),
    NarrationRow(
        "partner_ear_whisper",
        action=(
            "{actor} 湊近對方耳邊，把聲音壓低。",
            "{actor} 的吐息先一步拂上那隻耳朵。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 自己的耳根也熱了起來。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的耳朵被那口氣燙得發紅。",),
        },
    ),
    NarrationRow(
        "partner_deep_caress",
        action=(
            "{actor} 的手掌往下探，朝對方腿間靠近。",
            "{actor} 屈起指節，朝那處幽深探去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的私處也跟著泛起濕意。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的私處在指尖下逐漸濕了。",),
        },
    ),
    NarrationRow(
        "partner_oral_service",
        action=(
            "{actor} 俯下身，把臉埋向對方腿間。",
            "{actor} 的舌尖先探出唇外，朝那處靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的口唇之間漫著對方的氣味。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的私處被濕熱的觸感包住。",),
        },
    ),
    NarrationRow(
        "partner_breast_sex",
        action=(
            "{actor} 挺起胸膛，朝對方胸前迎去。",
            "{actor} 挺起身，讓胸口朝那片柔軟靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的胸前被磨得發燙。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的乳房在推擠之間變了形。",),
        },
    ),
    NarrationRow(
        "partner_thigh_rub",
        action=(
            "{actor} 側過身，讓腿根朝對方的大腿靠去。",
            "{actor} 的腿悄然移過去，朝那片溫熱貼近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腿根在摩擦裡滲出熱意。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的大腿被來回蹭得發軟。",),
        },
    ),
    NarrationRow(
        "partner_foot_service",
        action=(
            "{actor} 伸手朝對方的腳探去。",
            "{actor} 低下身，把臉湊向那截腳踝。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的指尖還留著那截腳踝的溫度。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的腳趾在服侍裡逐根蜷起。",),
        },
    ),
    NarrationRow(
        "partner_anal_sex",
        action=(
            "{actor} 繞到對方身後，朝那處探去。",
            "{actor} 從背後貼近，把手按向對方的腰。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的下腹在挺動裡越收越緊。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的後庭被撐開，整個人繃住。",),
        },
    ),
    NarrationRow(
        "partner_mutual_masturbation",
        action=(
            "{actor} 在對方面前坐下，手朝自己腿間探去。",
            "{actor} 與對方相對而坐，伸手朝彼此的腿間探去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的私處在自己的手裡發燙。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的私處被對方的手指帶著走。",),
        },
    ),
    NarrationRow(
        "partner_vaginal_sex",
        action=(
            "{actor} 把身體壓近，朝對方腿間迎上去。",
            "{actor} 把重心前移，朝那處緩慢靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的私處被緊密包住。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的體內被逐層填滿。",),
        },
    ),
    NarrationRow(
        "partner_deep_vaginal_sex",
        action=(
            "{actor} 壓低身子，朝最深的地方迎去。",
            "{actor} 收緊手臂，把距離收到最短。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的下腹一陣接一陣發麻。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的深處被頂得發顫。",),
        },
    ),
    NarrationRow(
        "partner_group_caress",
        action=(
            "{actor} 張開手，同時朝身邊的人探去。",
            "{actor} 側身讓開，把手分給在場的每一個人。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腰腹也被人們的動作撩得發熱。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的腰腹在指掌之間輾轉。",),
        },
    ),
    NarrationRow(
        "partner_group_orgy",
        action=(
            "{actor} 把自己放進那群交疊的身體之間。",
            "{actor} 朝最近的那副身體靠過去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 在人群裡被推得幾乎失了神。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的身體在許多手中沉了下去。",),
        },
    ),
    NarrationRow(
        "partner_group_service",
        action=(
            "{actor} 屈膝，朝身邊的人逐一探手。",
            "{actor} 低下頭，把注意力分給在場的每一個人。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腿在輪替之間逐漸發軟。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 被服侍得說不出話。",),
        },
    ),
)
