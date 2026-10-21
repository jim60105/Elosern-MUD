"""Per-spell narration for the wind element (pressure, cut air, drift).

The register is moving air: a sudden stillness, a cut that arrives before its
sound, a body carried a step further than it meant to go. A line names the
spell's own invocation, never its result; area spells address the whole field
and name no single body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "gale_step",
        action=(
            "{actor} 腳下生風，身形先一步輕了起來。",
            "{actor} 讓氣流貼著腿側流過，把人往前送。",
        ),
    ),
    NarrationRow(
        "gale_chain_step",
        action=(
            "{actor} 一步接一步，把速度疊在速度上。",
            "{actor} 借上一動的餘勢，再快一分。",
        ),
    ),
    NarrationRow(
        "afterimage_step",
        action=(
            "{actor} 動得太快，原地留下一個來不及散的影。",
            "{actor} 身形一晃，殘影還停在原來的位置。",
        ),
    ),
    NarrationRow(
        "haste_domain",
        action=(
            "{actor} 讓風在同伴之間流轉，整片場地都輕快起來。",
            "{actor} 張開一圈氣流，把速度分給每一個人。",
        ),
    ),
    NarrationRow(
        "wind_blade",
        action=(
            "{actor} 揮手，風被削成數片薄刃。",
            "{actor} 讓氣流貼地掠過，所過之處皆被切開。",
        ),
    ),
    NarrationRow(
        "tornado_blade",
        action=(
            "{actor} 聚起一道旋風，尖端指向對手。",
            "{actor} 擰腕成渦，風刃在掌前成形。",
        ),
    ),
    NarrationRow(
        "storm_domain",
        action=(
            "{actor} 展開暴風，把整片戰場圈進風眼。",
            "{actor} 讓氣壓驟然下沉，風從中央炸開。",
        ),
    ),
    NarrationRow(
        "gale_dance_strike",
        action=(
            "{actor} 隨風起舞，刃光一連閃了兩次。",
            "{actor} 腳步帶著身體旋轉，斬擊接連落下。",
        ),
    ),
    NarrationRow(
        "heavens_wrath_storm",
        action=(
            "{actor} 抬手，天上的風被扯下來壓向地面。",
            "{actor} 讓天譴般的狂風掃過所有人。",
        ),
    ),
    NarrationRow(
        "sky_rending_slash",
        action=(
            "{actor} 把風收成一道長刃，朝天劃落。",
            "{actor} 一斬而下，氣流被撕開一條白線。",
        ),
    ),
    NarrationRow(
        "sky_tempest",
        action=(
            "{actor} 令整片蒼穹翻湧，暴風壓向戰場。",
            "{actor} 引落天頂的亂流，把所有人往後推。",
        ),
    ),
    NarrationRow(
        "vacuum_severance",
        action=(
            "{actor} 抽走身前所有的空氣，留下一道真空。",
            "{actor} 指尖一劃，無聲的風刃切向那道身影。",
        ),
    ),
    NarrationRow(
        "sky_apotheosis",
        action=(
            "{actor} 展露天穹的神格，風從高處傾瀉。",
            "{actor} 的身後張開一片空無，氣流自那處湧出。",
        ),
    ),
    NarrationRow(
        "grain_shaking_peck",
        action=(
            "{actor} 以短促的氣流啄向對手。",
            "{actor} 一記快得看不清的點擊，氣流隨之收束。",
        ),
    ),
    NarrationRow(
        "mane_crosswind_pounce",
        action=(
            "{actor} 借側風撲出，身形忽左忽右。",
            "{actor} 讓風掩住動作，朝對方猛撲。",
        ),
    ),
)

__all__ = ["ROWS"]
