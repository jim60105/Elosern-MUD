"""Per-skill narration for the martial-arts family (steel and shadow).

The register is the body's discipline: footwork, blade arcs, the weight of a
weapon finding its line. It carries no wuxia vocabulary — no 內力, no 真氣, no
江湖. Each row holds the attempt, never the result, so the shared outcome
clauses still read correctly after a hit and after a miss.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "basic_attack",
        action=(
            "{actor} 平平無奇地踏前，抬手便是一擊——",
            "{actor} 沒有多餘的動作，直取眼前的空隙——",
        ),
    ),
    NarrationRow(
        "basic_swordplay",
        action=(
            "{actor} 的劍尖穩穩指向對手，腳下先動了半步——",
            "{actor} 把劍舉到眼前，等著對方先露出破綻——",
        ),
    ),
    NarrationRow(
        "flowing_strikes",
        action=(
            "{actor} 順著上一劍的餘勢，反手再遞出一記——",
            "{actor} 不收劍，讓斬勢一記接一記地疊上去——",
        ),
    ),
    NarrationRow(
        "tendon_sever",
        action=(
            "{actor} 壓低劍勢，朝對手的手腕切去——",
            "{actor} 貼身而入，劍鋒沿著關節的縫隙劃下——",
        ),
    ),
    NarrationRow(
        "whirlwind_slash",
        action=(
            "{actor} 擰腰旋身，兵刃繞出一整圈弧線——",
            "{actor} 的腳步帶動身形，劍光掃過半個場地——",
        ),
    ),
    NarrationRow(
        "thousand_blade_art",
        action=(
            "{actor} 的劍光一層疊上一層，快得沒有空隙——",
            "{actor} 連續遞劍，每一劍都追著上一劍的落點——",
        ),
    ),
    NarrationRow(
        "blade_storm",
        action=(
            "{actor} 的劍勢鋪展開來，把整片場地都罩了進去——",
            "{actor} 一步踏入陣中，劍刃在身周織成一張網——",
        ),
    ),
    NarrationRow(
        "blade_saint_arts",
        action=(
            "{actor} 的劍筆直落下，沒有一絲多餘——",
            "{actor} 收盡所有花巧，只留下最乾淨的一斬——",
        ),
    ),
    NarrationRow(
        "thousand_army_slash",
        action=(
            "{actor} 沉步向前，一劍劈開對陣的鋒線——",
            "{actor} 迎著人牆遞出劍，硬生生開出一條路——",
        ),
    ),
    NarrationRow(
        "true_sword_saint",
        action=(
            "{actor} 收劍於身側，氣息沉得幾乎聽不見——",
            "{actor} 站定不動，只讓劍尖說明一切——",
        ),
    ),
    NarrationRow(
        "light_sword_style",
        action=(
            "{actor} 將劍舉至眼前，刃上映著一線光——",
            "{actor} 側身而立，讓劍身斜斜擋在身前——",
        ),
    ),
    NarrationRow(
        "shadow_slash",
        action=(
            "{actor} 的身影貼著地面滑出，劍從低處挑起——",
            "{actor} 踏進對方的影子裡，刃尖才露出來——",
        ),
    ),
    NarrationRow(
        "phantom_dance",
        action=(
            "{actor} 的殘影先一步越過了距離——",
            "{actor} 的動作留下幾道殘像，真身已在近前——",
        ),
    ),
    NarrationRow(
        "dual_blade_waltz",
        action=(
            "{actor} 雙刃交錯，步伐輕得像在跳舞——",
            "{actor} 左手引開攻勢，右刃順著節拍落下——",
        ),
    ),
    NarrationRow(
        "shadow_veil_execution",
        action=(
            "{actor} 自陰影裡探出刃尖，一擊收在暗處——",
            "{actor} 藏在影中，等對方走過才動手——",
        ),
    ),
    NarrationRow(
        "shadow_dance_finale",
        action=(
            "{actor} 的劍在暗處劃下最後一道弧——",
            "{actor} 以一個收勢的轉身結束整套劍舞——",
        ),
    ),
)

__all__ = ["ROWS"]
