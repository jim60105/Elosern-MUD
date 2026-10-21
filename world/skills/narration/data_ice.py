"""Per-spell narration for the ice element (still air, fracture, held breath).

The register is cold as an absence of motion: air that stops, frost creeping
where it was not invited, a sound that cracks before anything visibly
breaks. A line names the spell's own invocation, never its result; area
spells address the whole field and name no single body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "frost_breath",
        action=(
            "{actor} 吐出一口白氣，冷意逐漸漫過去。",
            "{actor} 的呼吸落成霜，貼上對手。",
        ),
    ),
    NarrationRow(
        "ice_wall",
        action=(
            "{actor} 讓空氣凝住，在身側立起一道牆。",
            "{actor} 抬手，霜自地面爬上成牆。",
        ),
    ),
    NarrationRow(
        "frost_mire",
        action=(
            "{actor} 讓整片地面凝霜，踩上去便下陷。",
            "{actor} 把冷氣鋪開，泥土凍成黏滯的沼。",
        ),
    ),
    NarrationRow(
        "permafrost_domain",
        action=(
            "{actor} 展開永凍的領域，空氣停止流動。",
            "{actor} 讓寂靜的冷從腳下往外長。",
        ),
    ),
    NarrationRow(
        "absolute_tundra",
        action=(
            "{actor} 令大地化為凍土，寒氣同時封住所有人。",
            "{actor} 把最後一點暖意抽走，地表白成一片。",
        ),
    ),
    NarrationRow(
        "eternal_ice_field",
        action=(
            "{actor} 鋪開長夜的冰原，冷得沒有盡頭。",
            "{actor} 讓極寒的平原在戰場上延伸開來。",
        ),
    ),
    NarrationRow(
        "ice_shard",
        action=(
            "{actor} 凝出一根冰錐，筆直送去。",
            "{actor} 讓空氣結成尖銳的冰，朝那道身影刺出。",
        ),
    ),
    NarrationRow(
        "frost_arrow_rain",
        action=(
            "{actor} 抬手，冷凍的箭雨自上方落下。",
            "{actor} 讓霜氣在空中凝成數支箭。",
        ),
    ),
    NarrationRow(
        "ice_prison",
        action=(
            "{actor} 讓寒冰沿著對方的四周合攏。",
            "{actor} 一圈霜牆生出，把人關在裡頭。",
        ),
    ),
    NarrationRow(
        "blizzard",
        action=(
            "{actor} 喚起狂暴的風雪，天地一片白。",
            "{actor} 讓雪片橫掃過整片戰場。",
        ),
    ),
    NarrationRow(
        "crystal_shatter",
        action=(
            "{actor} 找到附在目標身上的霜屑，輕彈一下。",
            "{actor} 讓凝住的冰晶同時裂開。",
        ),
    ),
    NarrationRow(
        "absolute_zero",
        action=(
            "{actor} 把溫度壓到極處，一切聲音都停了。",
            "{actor} 讓最後的寒氣收束在對方身上。",
        ),
    ),
    NarrationRow(
        "eternal_frost_apotheosis",
        action=(
            "{actor} 顯露永凍的神格，長冬在戰場上降臨。",
            "{actor} 的身形覆滿霜，四周的時間慢了下來。",
        ),
    ),
)

__all__ = ["ROWS"]
