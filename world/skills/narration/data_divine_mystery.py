"""Per-skill narration for the divine-mystery family (the authority of the divine).

The register is authority speaking through the caster: a hand extended, a name
pronounced, a weight that does not belong to a mortal settling on the field.
A row adds only the invocation; the law-giving imagery stays in the shared
``skill_granted`` and ``buff_applied`` pools, except where a mystery's own
authority would otherwise read as generic — the grant, the recall, the veil
and the true-name sight each carry their own outcome clause.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "dominion_art",
        action=(
            "{actor} 抬起手，把屬於自己的權柄分了出去。",
            "{actor} 以不容置疑的口吻，將力量的一部分交予對方。",
        ),
        kind_lines={
            "skill_granted": (
                "{target} 手上多了一分被授予的從容。",
                "{target} 借來的動作穩得像練了許久。",
            ),
        },
    ),
    NarrationRow(
        "dominion_recall",
        action=(
            "{actor} 抬手一招，作勢收回借出的一切。",
            "{actor} 只是開口，唸出那些授予的來處。",
        ),
        kind_lines={
            "grants_revoked": (
                "{target} 身上借來的一切同時斷了線。",
                "{target} 感到那份從容被整個收了回去。",
            ),
        },
    ),
    NarrationRow(
        "shared_dominion",
        action=(
            "{actor} 的聲音傳遍全場，權柄同時落向每一個人。",
            "{actor} 展手一揮，讓同一份授予覆蓋整支隊伍。",
        ),
        kind_lines={
            "skill_granted": (
                "{target} 與旁人一同分到了那份權柄。",
                "{target} 察覺到別人的技藝也落進了自己手裡。",
            ),
        },
    ),
    NarrationRow(
        "sovereign_investiture",
        action=(
            "{actor} 以王者的姿態，授予更重的權柄。",
            "{actor} 立於陣前，讓更高的權柄從他身上漫開。",
        ),
        kind_lines={
            "skill_granted": (
                "{target} 承接了更重的權柄。",
                "{target} 身上的授予沉得幾乎有了重量。",
            ),
        },
    ),
    NarrationRow(
        "mentors_covenant",
        action=(
            "{actor} 以長者的聲音，讓對方跟上自己的節奏。",
            "{actor} 覆上對方的手，將自己的步調分了一半。",
        ),
        kind_lines={
            "buff_applied": (
                "{target} 的學習節奏被悄然撥快。",
                "{target} 的動作一次比一次更像樣。",
            ),
        },
    ),
    NarrationRow(
        "chorus_of_ages",
        action=(
            "{actor} 領著眾人同聲，讓漫長的歲月在隊伍裡迴響。",
            "{actor} 一起聲，便像有許多代人在同時開口。",
        ),
        kind_lines={
            "buff_applied": (
                "{target} 聽見了比自己更長的歲月在指路。",
                "{target} 的每一步都像走過很多遍。",
            ),
        },
    ),
    NarrationRow(
        "undying_tutelage",
        action=(
            "{actor} 的話語帶著不受時間侵蝕的重量。",
            "{actor} 把一段幾乎無盡的耐心，交到每個人手裡。",
        ),
        kind_lines={
            "buff_applied": (
                "{target} 的時間像是被拉長了。",
                "{target} 感到自己還有很久可以學。",
            ),
        },
    ),
    NarrationRow(
        "status_disguise",
        action=(
            "{actor} 垂下眼簾，讓眾人看見另一個自己。",
            "{actor} 的神色一換，連身形都跟著陌生起來。",
        ),
        kind_lines={
            "disguise_set": (
                "{target} 看上去已經換了一個人。",
                "{target} 的模樣被另一層外表接手。",
            ),
            "disguise_lifted": (
                "{target} 收回了那副借來的模樣。",
                "{target} 原本的面貌重新浮現。",
            ),
        },
    ),
    NarrationRow(
        "bestowed_veil",
        action=(
            "{actor} 伸手，替對方蓋上一層別的面貌。",
            "{actor} 隨手一抹，讓對方看上去不再是自己。",
        ),
        kind_lines={
            "disguise_set": (
                "{target} 的外表被另一層模樣覆住。",
                "{target} 看上去成了另一個不曾存在的人。",
            ),
            "disguise_lifted": (
                "{target} 臉上的帷幕被收了回去。",
                "{target} 又變回自己原本的樣子。",
            ),
        },
    ),
    NarrationRow(
        "true_name_sight",
        action=(
            "{actor} 直視對方的真名，看穿那層表象。",
            "{actor} 的目光停在原處，卻已越過偽裝。",
        ),
        kind_lines={
            "reveal_lifted": (
                "{target} 的偽裝在真名之前散了。",
                "{target} 藏著的那張臉被整個揭開。",
            ),
            "reveal_noop": (
                "{target} 身上沒有可掀的帷幕。",
                "{target} 表裡如一，沒有藏起什麼。",
            ),
        },
    ),
    NarrationRow(
        "crown_apotheosis",
        action=(
            "{actor} 戴上那頂看不見的冠冕。",
            "{actor} 站到眾人之首，讓權柄、歲月與帷幕同時落下。",
        ),
        kind_lines={
            "skill_granted": (
                "{target} 分到了冠冕之下的一部份權柄。",
                "{target} 的動作裡多了一層不容置疑的分量。",
            ),
            "buff_applied": (
                "{target} 的時間被延得更長，也更從容。",
                "{target} 感到自己忽然有了無盡的時間。",
            ),
            "disguise_set": (
                "{target} 被冠冕的陰影換了一副面貌。",
                "{target} 看上去已屬於另一個位置。",
            ),
            "disguise_lifted": (
                "{target} 頭上的冠冕陰影散去，露出原本的面貌。",
                "{target} 收回了那副屬於王座的面貌。",
            ),
        },
    ),
)

__all__ = ["ROWS"]
