"""Per-spell narration for the dark element (absence, erosion, whisper).

The register is what is not seen: a shadow that leans closer, a name spoken
where no one can hear it, a hole in the world that the light declines to
enter. Nothing here is gory and nothing is cruel for show; the dark simply
takes away.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "weaken",
        action=(
            "{actor} 讓一道影子朝對手貼過去，無聲地收緊——",
            "{actor} 低聲喚出一個名字，讓它朝對手落下去——",
        ),
    ),
    NarrationRow(
        "curse",
        action=(
            "{actor} 在暗處畫下一個名字——",
            "{actor} 讓看不見的手朝對手伸去——",
        ),
    ),
    NarrationRow(
        "curse_spread",
        action=(
            "{actor} 讓暗影從腳下散開，纏住每一道身影——",
            "{actor} 的低語在場上迴盪，把重負分給所有人——",
        ),
    ),
    NarrationRow(
        "dark_dominion",
        action=(
            "{actor} 展開一片支配的暗，朝四周壓下——",
            "{actor} 讓黑暗收攏過來，圍住每一道身影——",
        ),
    ),
    NarrationRow(
        "shadow_torture",
        action=(
            "{actor} 讓影子伸出手，一點點擰緊——",
            "{actor} 把對方的影拉長，從那裡開始侵蝕——",
        ),
    ),
    NarrationRow(
        "shadow_blight",
        action=(
            "{actor} 注入一縷深暗，讓它慢慢啃食——",
            "{actor} 讓暗影滲進皮膚底下，無聲地蔓延——",
        ),
    ),
    NarrationRow(
        "underworld_judgment",
        action=(
            "{actor} 讓冥界的門開了一道縫——",
            "{actor} 指向對手，那句判詞便落了下來——",
        ),
    ),
    NarrationRow(
        "shadow_bolt",
        action=(
            "{actor} 抽出一道影，朝對手射出——",
            "{actor} 指間的黑凝成箭，倏地離手——",
        ),
    ),
    NarrationRow(
        "dark_burst",
        action=(
            "{actor} 讓暗在戰場中央炸開——",
            "{actor} 收攏所有影子，再一口氣放掉——",
        ),
    ),
    NarrationRow(
        "dark_corrosion_domain",
        action=(
            "{actor} 展開一片侵蝕的領域，邊緣慢慢化開——",
            "{actor} 讓黑暗在地面上爬，所過之處都留下缺口——",
        ),
    ),
    NarrationRow(
        "abyss_devour",
        action=(
            "{actor} 讓腳下張開一片什麼都沒有的黑——",
            "{actor} 指向對手，深淵便應聲張口——",
        ),
    ),
    NarrationRow(
        "void_annihilation",
        action=(
            "{actor} 讓虛空在戰場上張開，一切都被抹平——",
            "{actor} 抬手，存在本身先薄了一層——",
        ),
    ),
    NarrationRow(
        "abyssal_apotheosis",
        action=(
            "{actor} 顯露深淵的神格，讓四周的光一齊退開——",
            "{actor} 的身形融進黑暗，讓它漫過整片戰場——",
        ),
    ),
)

__all__ = ["ROWS"]
