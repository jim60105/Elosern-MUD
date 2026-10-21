"""Per-skill narration for the holy-rite family (liturgical light).

The register is liturgical: consecration, shelter, absolution. A line names
the rite's own act — the water, the oil, the mark, the kiss — and never a
mechanic, so a rite reads as something performed rather than something
applied. The blessing and shelter rows also carry the outcome clause their
own act earns, instead of the shared pool line.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "rite_heal_light",
        action=(
            "{actor} 將掌心覆上，讓光逐漸滲進傷處。",
            "{actor} 捧起一束光，輕按在對方身上。",
        ),
    ),
    NarrationRow(
        "rite_cleanse",
        action=(
            "{actor} 以指蘸水，在對方額前畫下潔淨的記號。",
            "{actor} 低聲誦念，把附在身上的沉重逐層洗去。",
        ),
    ),
    NarrationRow(
        "rite_calm",
        action=(
            "{actor} 放慢聲調，領著對方把呼吸平靜下來。",
            "{actor} 按住對方的手，讓紛亂逐漸退去。",
        ),
    ),
    NarrationRow(
        "rite_bless_water",
        action=(
            "{actor} 舉起聖水，讓禱詞落進水面。",
            "{actor} 在聖水上畫下祝福，再灑向對方。",
        ),
    ),
    NarrationRow(
        "rite_sanctify_ground",
        action=(
            "{actor} 俯身按地，把聖意鋪向四周。",
            "{actor} 繞行一圈，腳下所過之處皆成聖域。",
        ),
    ),
    NarrationRow(
        "rite_absolution",
        action=(
            "{actor} 垂下眼，替對方說出那句赦免。",
            "{actor} 覆上對方的手，把罪與重擔一併接過。",
        ),
    ),
    NarrationRow(
        "rite_lamb_mark",
        action=(
            "{actor} 在自己額上按下代贖的印記。",
            "{actor} 抬手按額，把那道印記留給自己。",
        ),
        kind_lines={
            "self_buff_applied": (
                "{actor} 額上的印記沉了下去，替旁人受著。",
                "{actor} 感覺到那道印記正替他擋下什麼。",
            ),
        },
    ),
    NarrationRow(
        "rite_martyrdom_vow",
        action=(
            "{actor} 立於原地，把名字交了出去。",
            "{actor} 仰望聖所深處，低聲許下再無退路的願。",
        ),
        kind_lines={
            "session_stamp": (
                "{actor} 感到某種重量從此壓在肩上。",
                "{actor} 的每一步都帶著不再回頭的分量。",
            ),
        },
    ),
    NarrationRow(
        "rite_anointing_touch",
        action=(
            "{actor} 蘸著聖油，沿著對方的肌膚抹開。",
            "{actor} 讓溫熱的油在指尖化開，逐寸敷上。",
        ),
    ),
    NarrationRow(
        "rite_milk_blessing",
        action=(
            "{actor} 將對方攬近，讓祝福安靜地落進身體。",
            "{actor} 以最輕的力道，讓滋養與安寧落進對方身體。",
        ),
    ),
    NarrationRow(
        "rite_holy_kiss",
        action=(
            "{actor} 俯身，以一個吻完成這場聖儀。",
            "{actor} 捧住對方的臉，讓聖吻久一點才落下。",
        ),
    ),
    NarrationRow(
        "rite_confession_bed",
        action=(
            "{actor} 領著對方躺下，讓告解從身體開始。",
            "{actor} 在床邊俯身，把未說出口的話都接下。",
        ),
    ),
    NarrationRow(
        "rite_martial_blessing",
        action=(
            "{actor} 抬手為武備覆上一層聖意。",
            "{actor} 將兵刃舉到光下，讓禱詞附上去。",
        ),
        kind_lines={
            "rite_blessing": (
                "{actor} 的兵刃被聖意裹住，泛著微光。",
                "{actor} 的武備在禱詞裡安靜地亮起。",
            ),
        },
    ),
    NarrationRow(
        "rite_shelter",
        action=(
            "{actor} 在聖所裡張開一層庇護。",
            "{actor} 關上門，讓庇護安然落在自己身上。",
        ),
        kind_lines={
            "rite_shelter": (
                "{actor} 的傷勢在門後逐漸平息。",
                "{actor} 的呼吸終於在門內慢了下來。",
            ),
        },
    ),
)

__all__ = ["ROWS"]
