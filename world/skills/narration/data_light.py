"""Per-spell narration for the light element (radiance, warmth, clarity).

The register is brightness that reveals and warms before it cuts: a beam
laid across a wound, a white line that simply makes the dark irrelevant. It
is deliberately not the liturgical register of the holy-rite family — no
consecration, no oil, no mark, no rite.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "heal",
        action=(
            "{actor} 讓一束光落在傷處，暖意慢慢滲進去——",
            "{actor} 掌心亮起，把光輕輕推向對方——",
        ),
    ),
    NarrationRow(
        "light_arrow",
        action=(
            "{actor} 拉開一線光，讓它筆直飛出——",
            "{actor} 指間凝出光的箭，朝對手射去——",
        ),
    ),
    NarrationRow(
        "mass_heal",
        action=(
            "{actor} 讓光鋪滿整片場地，替每個人裹住傷口——",
            "{actor} 舉手，溫暖的光同時落在所有身影上——",
        ),
    ),
    NarrationRow(
        "purify",
        action=(
            "{actor} 讓清亮的光掃過，把附著的東西一層層剝掉——",
            "{actor} 把光聚在對方身上，直到一切歸於乾淨——",
        ),
    ),
    NarrationRow(
        "penitent_touch",
        action=(
            "{actor} 伸手觸上，光在接觸處變得銳利——",
            "{actor} 讓指節映出一道白亮，落在對方身上——",
        ),
    ),
    NarrationRow(
        "advanced_heal",
        action=(
            "{actor} 捧起更濃的光，一點不留地送進去——",
            "{actor} 讓光自掌心湧出，把傷口整個蓋住——",
        ),
    ),
    NarrationRow(
        "sanctified_ward",
        action=(
            "{actor} 讓光在同伴腳下連成一片——",
            "{actor} 抬手，柔和的光罩住每一個人——",
        ),
    ),
    NarrationRow(
        "judgment_strike",
        action=(
            "{actor} 把光收成一道刃，直直落下——",
            "{actor} 高舉的手帶著白亮，斬向那道身影——",
        ),
    ),
    NarrationRow(
        "revival_light",
        action=(
            "{actor} 把最亮的一束光送到對方面前——",
            "{actor} 讓光一點點攀回對方身上——",
        ),
    ),
    NarrationRow(
        "holy_radiance",
        action=(
            "{actor} 讓光輝自身上散開，掃過整片戰場——",
            "{actor} 的光亮得讓人睜不開眼，暗處被一併洗去——",
        ),
    ),
    NarrationRow(
        "goddess_blessing",
        action=(
            "{actor} 承接一道溫柔的光，再分給所有人——",
            "{actor} 讓光像暖流一樣漫過每一位同伴——",
        ),
    ),
    NarrationRow(
        "holy_kiss_heal",
        action=(
            "{actor} 靠近，讓溫熱的光隨著距離縮短而亮起——",
            "{actor} 把光留在接觸的地方，久久不散——",
        ),
    ),
    NarrationRow(
        "goddess_milk",
        action=(
            "{actor} 讓柔和的光沿著手心淌下——",
            "{actor} 把滋養般的亮意一點點遞過去——",
        ),
    ),
    NarrationRow(
        "blessed_climax",
        action=(
            "{actor} 讓光一下子推到最亮，覆住所有同伴——",
            "{actor} 的光在戰場上滿溢出來，暖得發燙——",
        ),
    ),
    NarrationRow(
        "heavens_judgment_light",
        action=(
            "{actor} 指向對手，讓天上的光筆直墜落——",
            "{actor} 把裁決交給光，一線白亮從雲端落下——",
        ),
    ),
    NarrationRow(
        "bliss_apotheosis",
        action=(
            "{actor} 讓神格的光同時落在兩方——",
            "{actor} 的身形亮成一片，溫暖與鋒利一同散開——",
        ),
    ),
    NarrationRow(
        "lamp_carapace_claw",
        action=(
            "{actor} 的甲殼泛起微光，向前一夾——",
            "{actor} 收緊外殼，順勢朝對手揮出——",
        ),
    ),
)

__all__ = ["ROWS"]
