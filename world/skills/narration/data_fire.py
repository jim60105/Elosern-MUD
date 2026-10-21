"""Per-spell narration for the fire element (heat, ember, ignition).

The register is heat and what it leaves behind: embers, scorched air, a room
that stays warm after the flame is gone. A line names the spell's own
invocation, never its result; the shared outcome pools still say whether the
strike landed and how hard. Area spells address the field and name no single
body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "fire_arrow",
        action=(
            "{actor} 張弓不需弦，一線赤焰便離了指間——",
            "{actor} 併指成矢，把火收成一條細線射向眼前的影子——",
        ),
    ),
    NarrationRow(
        "fire_ball",
        action=(
            "{actor} 把火焰壓進掌心，揉成一團擲出——",
            "{actor} 掌中的火越聚越沉，終於脫手滾向對手——",
        ),
    ),
    NarrationRow(
        "scorching_wave",
        action=(
            "{actor} 貼地推出一道熱浪，火氣黏上對手的腳邊——",
            "{actor} 讓灼意一波波漫過去，久久不散——",
        ),
    ),
    NarrationRow(
        "firestorm",
        action=(
            "{actor} 抬手，火焰在整片戰場上空翻湧而下——",
            "{actor} 一句短促的咒，火便從四面八方圍攏過來——",
        ),
    ),
    NarrationRow(
        "flame_shroud",
        action=(
            "{actor} 讓烈焰沿著眼前那副身軀纏上——",
            "{actor} 指尖一引，火舌一圈圈收緊——",
        ),
    ),
    NarrationRow(
        "scorching_armor",
        action=(
            "{actor} 讓熱意貼著皮膚鋪開，像一層看不見的甲——",
            "{actor} 把火壓進衣袍底下，靜靜地煨著——",
        ),
    ),
    NarrationRow(
        "lava_burst",
        action=(
            "{actor} 令腳下地面迸裂，熔岩朝四面噴起——",
            "{actor} 一踏地面，整片戰場湧出赤紅的裂口——",
        ),
    ),
    NarrationRow(
        "hellfire",
        action=(
            "{actor} 指向對手，讓煉獄的火自地面爬升——",
            "{actor} 低聲喚出那不該被點燃的火——",
        ),
    ),
    NarrationRow(
        "dragon_flame",
        action=(
            "{actor} 吐息之間，龍的烈焰鋪滿整片戰場——",
            "{actor} 身後浮起龍影，火從那張巨口裡傾倒而下——",
        ),
    ),
    NarrationRow(
        "final_blaze",
        action=(
            "{actor} 把最後一點火也交出去，焰流筆直貫向那道身影——",
            "{actor} 不再留手，讓焚世的火找到唯一的落點——",
        ),
    ),
    NarrationRow(
        "sacrificial_flame",
        action=(
            "{actor} 以自己的體溫為薪，火在整片戰場上燒開——",
            "{actor} 將自身獻作柴薪，燔祭的火吞過每一道身影——",
        ),
    ),
    NarrationRow(
        "crimson_apotheosis",
        action=(
            "{actor} 化作紅蓮，讓業火在戰場上同時綻放——",
            "{actor} 身形被赤焰吞沒，火從那處向四方漫開——",
        ),
    ),
)

__all__ = ["ROWS"]
