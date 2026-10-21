"""Per-spell narration for the water element (tide, flow, quiet pressure).

The register is the weight of water and the pull of a receding tide: nothing
shatters, everything is drawn under. A line names the spell's own invocation,
never its result; area spells address the whole field and name no single
body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "tide_pull",
        action=(
            "{actor} 抬手一引，潮水便朝對手捲去。",
            "{actor} 指尖勾起一線水流，往自己的方向收。",
        ),
    ),
    NarrationRow(
        "ebbing_blight",
        action=(
            "{actor} 讓水退去，把對手腳下的餘力一併帶走。",
            "{actor} 引一道退潮，漫過目標又悄然抽離。",
        ),
    ),
    NarrationRow(
        "water_shield",
        action=(
            "{actor} 讓水貼著身體凝成一層輕薄的膜。",
            "{actor} 抬手，水氣在身前悄然攏起。",
        ),
    ),
    NarrationRow(
        "ring_of_reflux",
        action=(
            "{actor} 在水面畫出一個環，讓流動重新歸位。",
            "{actor} 輕推一下，水便繞著對方回轉。",
        ),
    ),
    NarrationRow(
        "drowned_surging",
        action=(
            "{actor} 讓水聲淹過一切，逐漸沒過眼前的身影。",
            "{actor} 引發一股溺潮，從四面八方壓過來。",
        ),
    ),
    NarrationRow(
        "sigil_of_the_barren_sea",
        action=(
            "{actor} 在對方身上落下枯海的印。",
            "{actor} 畫下那道印，讓水從此退得乾淨。",
        ),
    ),
    NarrationRow(
        "abyssal_surge",
        action=(
            "{actor} 引動深淵的潮汛，水漫過所有同伴的腳邊。",
            "{actor} 讓一層幽深的水光鋪開，悄然回流。",
        ),
    ),
    NarrationRow(
        "water_bolt",
        action=(
            "{actor} 把水收成一束，筆直射向對手。",
            "{actor} 指間的水線繃緊，倏地離手。",
        ),
    ),
    NarrationRow(
        "deep_current_spike",
        action=(
            "{actor} 讓水面下積起的暗流突起成刺。",
            "{actor} 自深處抽出一道水，尖端朝那道身影遞去。",
        ),
    ),
    NarrationRow(
        "abyssal_whirlpool",
        action=(
            "{actor} 令水面凹陷，漩渦在戰場中央張開。",
            "{actor} 引動深海的迴轉，把四周都捲進中心。",
        ),
    ),
    NarrationRow(
        "abyssal_maw",
        action=(
            "{actor} 張開一道深淵般的口，水與光一齊被吞進去。",
            "{actor} 讓巨口在對手腳下張開，貪婪地吸吮。",
        ),
    ),
    NarrationRow(
        "tsunami",
        action=(
            "{actor} 舉手，整片海便立了起來。",
            "{actor} 喚起滔天的水牆，朝戰場壓下。",
        ),
    ),
    NarrationRow(
        "abyssal_tide",
        action=(
            "{actor} 讓深淵的巨潮漫過整個戰場。",
            "{actor} 引一道沉默的大水，將一切淹沒。",
        ),
    ),
    NarrationRow(
        "abyssal_heart",
        action=(
            "{actor} 讓深海的心臟在戰場上跳動，潮水隨之收放。",
            "{actor} 的腳下浮起幽暗的脈動，水朝兩方分流。",
        ),
    ),
    NarrationRow(
        "tide_devouring_bite",
        action=(
            "{actor} 讓水纏上牙關，朝對手咬合。",
            "{actor} 借潮水的力道收緊一擊。",
        ),
    ),
)

__all__ = ["ROWS"]
