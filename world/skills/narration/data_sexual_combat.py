"""Per-act narration for the 戰鬥 (combat) line.

The register is urgency: a blade's length of space, a breath spent on a word
instead of a strike, the fight bleeding into touch. Every attempt clause stays
inside the exchange and leaves the outcome to the verdict clause.

``ROWS`` follows the act registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "combat_tease",
        action=(
            "{actor} 在交鋒之間朝對方遞出一個挑逗的眼神——",
            "{actor} 讓腳步慢半拍，把笑意先送過去——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的心跳在戰意裡亂了一拍。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的動作被那一瞬分了神。",),
        },
    ),
    NarrationRow(
        "combat_tease_whisper",
        action=(
            "{actor} 貼近半步，把聲音送進對方耳裡——",
            "{actor} 趁著錯身，把一句話壓低——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 自己的耳根先熱了。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的耳畔被那句話燒了一下。",),
        },
    ),
    NarrationRow(
        "combat_tease_touch",
        action=(
            "{actor} 趁著錯身，指尖朝對方腰腹掠去——",
            "{actor} 讓手背在交錯時朝那片腰腹靠近——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的指尖還帶著那一下的觸感。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的腰腹在掠過之後一陣發麻。",),
        },
    ),
    NarrationRow(
        "combat_charm",
        action=(
            "{actor} 側過身，讓姿態與聲音一同纏上去——",
            "{actor} 收住攻勢，改用另一種方式逼近——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 在施展之間也亂了氣息。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的心神被牽得鬆了手。",),
        },
    ),
    NarrationRow(
        "combat_bind_caress",
        action=(
            "{actor} 伸手朝對方的大腿纏去——",
            "{actor} 側身朝那條腿靠攏，準備纏上去——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的手臂在纏繞裡發熱。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的大腿被纏得使不上力。",),
        },
    ),
    NarrationRow(
        "combat_forced_pleasure",
        action=(
            "{actor} 壓過去，手朝對方腿間直取——",
            "{actor} 不給對方讓開的餘地，硬是往下探——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的呼吸在壓制裡變得粗重。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的私處被硬生生逼出反應。",),
        },
    ),
    NarrationRow(
        "combat_forced_climax",
        action=(
            "{actor} 加快逼近，朝對方的弱處施壓——",
            "{actor} 不放慢腳步，一點點收緊距離——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的手在緊繃裡微微發抖。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 被推過那道界線，整個人散了。",),
        },
    ),
    NarrationRow(
        "combat_relentless_torment",
        action=(
            "{actor} 不給對方喘息的空隙，手朝臀後探去——",
            "{actor} 收緊手腕，準備把節奏疊上去——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的呼吸隨著節奏越來越急。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的臀部在連番責弄下紅了。",),
        },
    ),
    NarrationRow(
        "combat_climax_domination",
        action=(
            "{actor} 立在戰場中央，把氣勢朝所有人壓去——",
            "{actor} 抬手一揮，讓氣勢掃過整個戰圈——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 在支配的姿態裡也燒了起來。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 被那股氣勢壓得抬不起頭。",),
        },
    ),
)
