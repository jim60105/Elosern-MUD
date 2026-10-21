"""Per-spell narration for the lightning element (instant, white line).

The register is the interval between the flash and the sound: a line drawn
across the field, then the thunder arriving late. A line names the spell's own
invocation, never its result; area spells address the whole field and name no
single body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "static_ward",
        action=(
            "{actor} 讓細小的電光在身周繞行。",
            "{actor} 皮膚上浮起一層發麻的癢意。",
        ),
    ),
    NarrationRow(
        "lightning_flicker",
        action=(
            "{actor} 身形一閃，雷光在原地炸開。",
            "{actor} 一步踏出，白亮的線緊貼著腳跟。",
        ),
    ),
    NarrationRow(
        "thunder_combo",
        action=(
            "{actor} 舉手連揮，一次又一次落下雷擊。",
            "{actor} 讓雷聲接連追著對手的影子。",
        ),
    ),
    NarrationRow(
        "thunder_gods_haste",
        action=(
            "{actor} 把雷收進身體，動作陡然加快。",
            "{actor} 短促地吸氣，電光順著脊椎走過。",
        ),
    ),
    NarrationRow(
        "thunder_shatter_strike",
        action=(
            "{actor} 把所有雷意壓進一次出手。",
            "{actor} 的白線筆直貫向那道身影，聲音才在後面趕到。",
        ),
    ),
    NarrationRow(
        "judgement_thunder",
        action=(
            "{actor} 指向天空，讓審判隨雷落下。",
            "{actor} 抬起手，天頂便應了一聲。",
        ),
    ),
    NarrationRow(
        "spark_shock",
        action=(
            "{actor} 指尖迸出一點雷光，倏地彈出。",
            "{actor} 讓細小的電流順著空氣鑽向對手。",
        ),
    ),
    NarrationRow(
        "chain_lightning",
        action=(
            "{actor} 一線雷光躍出，接連跳過整排身影。",
            "{actor} 讓電在戰場上牽成一條鏈。",
        ),
    ),
    NarrationRow(
        "paralyzing_bolt",
        action=(
            "{actor} 射出一道麻痺的雷，釘住對手。",
            "{actor} 讓雷停在目標身上，許久不走。",
        ),
    ),
    NarrationRow(
        "lightning_strike",
        action=(
            "{actor} 舉手，落雷一道接一道砸下。",
            "{actor} 讓天空裂開白亮的縫，雷聲隨後而至。",
        ),
    ),
    NarrationRow(
        "thunder_prison",
        action=(
            "{actor} 引雷成籠，把人圈在其中。",
            "{actor} 讓電光在四周立起欄杆，圍住那道身影。",
        ),
    ),
    NarrationRow(
        "heavens_thunder",
        action=(
            "{actor} 讓天雷自高處傾倒而下。",
            "{actor} 把整片天空的怒意都引到戰場。",
        ),
    ),
    NarrationRow(
        "divine_lightning_slaughter",
        action=(
            "{actor} 喚下神雷，白光掃過所有敵人。",
            "{actor} 讓天上的裁決化成一擊，落向全場。",
        ),
    ),
    NarrationRow(
        "thunder_apotheosis",
        action=(
            "{actor} 化身為雷霆本身，聲音在事後才追上。",
            "{actor} 的身形散成白光，再從高處聚回。",
        ),
    ),
)

__all__ = ["ROWS"]
