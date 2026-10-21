"""Per-spell narration for the earth element (ground, weight, footing).

The register is weight that will not be moved: stone rising where there was
floor, a footing that suddenly is not there, a blow that arrives through the
ground before it arrives through the air. A line names the spell's own
invocation, never its result; area spells address the whole field and name no
single body.

``ROWS`` follows the skill registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "stone_shard",
        action=(
            "{actor} 自腳下凝起碎石，揚手擲出。",
            "{actor} 讓土聚成尖石，朝對手射去。",
        ),
    ),
    NarrationRow(
        "stone_armor",
        action=(
            "{actor} 讓岩石自地面攀上對方的肩背。",
            "{actor} 以土覆身，替對方結成一層岩甲。",
        ),
    ),
    NarrationRow(
        "bedrock_bastion",
        action=(
            "{actor} 令磐石自地底升起，圍在同伴身前。",
            "{actor} 踏實地面，把壁壘逐層疊起來。",
        ),
    ),
    NarrationRow(
        "earthen_ward",
        action=(
            "{actor} 把大地的沉穩分給每一個人。",
            "{actor} 手掌按地，讓庇護從腳下漫開。",
        ),
    ),
    NarrationRow(
        "thorned_carapace",
        action=(
            "{actor} 讓石刺沿著肌理冒出來。",
            "{actor} 收緊身體，土色的甲片逐片扣上。",
        ),
    ),
    NarrationRow(
        "dust_veil",
        action=(
            "{actor} 揚手掀起漫天沙塵。",
            "{actor} 一腳踏地，黃土便撲面而起。",
        ),
    ),
    NarrationRow(
        "ground_fissure",
        action=(
            "{actor} 令地面裂開一道長縫。",
            "{actor} 把土推開，讓裂縫沿著戰場蔓延。",
        ),
    ),
    NarrationRow(
        "rockslide",
        action=(
            "{actor} 震動山壁，讓碎石成片崩落。",
            "{actor} 一抬手，岩層便整塊滑了下來。",
        ),
    ),
    NarrationRow(
        "earthquake",
        action=(
            "{actor} 沉腰踏地，震波自腳下擴散。",
            "{actor} 讓整片大地晃動，裂口隨之張開。",
        ),
    ),
    NarrationRow(
        "fault_rupture",
        action=(
            "{actor} 扯動地脈，讓對手腳下的根鬆開。",
            "{actor} 一掌拍地，一道裂痕筆直追向目標。",
        ),
    ),
    NarrationRow(
        "mountain_collapse",
        action=(
            "{actor} 令山嶽傾倒，土石鋪天蓋地。",
            "{actor} 把整座山的重量壓向戰場。",
        ),
    ),
    NarrationRow(
        "earths_judgment",
        action=(
            "{actor} 借大地的審判，讓地面自對手腳下隆起。",
            "{actor} 低聲喚土，沉重的判決隨之落下。",
        ),
    ),
    NarrationRow(
        "earthen_apotheosis",
        action=(
            "{actor} 讓大地甦醒，裂縫鋪滿整個戰場。",
            "{actor} 的身形沉進土裡，全場的地面一齊翻動。",
        ),
    ),
    NarrationRow(
        "hardened_skin",
        action=(
            "{actor} 讓肌膚逐漸變硬，像風化的岩面。",
            "{actor} 收斂氣息，把身體壓成一塊石。",
        ),
    ),
    NarrationRow(
        "ridge_bracing_kick",
        action=(
            "{actor} 穩住下盤，一腳蹬向對手。",
            "{actor} 借田埂般的沉勢，奮力踢出。",
        ),
    ),
    NarrationRow(
        "rock_echo_ram",
        action=(
            "{actor} 以角撞出沉悶的聲響，土氣四散。",
            "{actor} 低頭衝撞，碎岩般的力道撞上那道身影。",
        ),
    ),
)

__all__ = ["ROWS"]
