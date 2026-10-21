"""Per-act narration for the 異種 (interspecies) line.

The register is unfamiliar anatomy met as wonder and risk, never gore. These
acts declare no target part, so the receiving clause speaks of a whole body
rather than a named place.

``ROWS`` follows the act registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "interspecies_touch",
        action=(
            "{actor} 朝那具非人的身軀伸出手。",
            "{actor} 放慢腳步，把手掌朝那片陌生靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的掌心還留著那不屬於人的溫度。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的身軀在觸碰下起了一層異樣的顫。",),
        },
    ),
    NarrationRow(
        "interspecies_caress",
        action=(
            "{actor} 順著那副陌生軀體的輪廓探去。",
            "{actor} 的手朝那副從未見過的形狀探去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的指尖被陌生的觸感燙著。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 被撫過的地方泛起從未有過的反應。",),
        },
    ),
    NarrationRow(
        "interspecies_entangle",
        action=(
            "{actor} 朝纏繞過來的肢體迎上去。",
            "{actor} 讓自己的身體朝那些肢體靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 被擠壓得幾乎喘不過氣。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的肢體收得更緊。",),
        },
    ),
    NarrationRow(
        "interspecies_receive",
        action=(
            "{actor} 敞開身體，朝那副身軀迎去。",
            "{actor} 不再退開，讓對方朝自己靠近。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的體內被陌生的形狀撐開。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 在衝撞裡留下自己的節奏。",),
        },
    ),
    NarrationRow(
        "interspecies_mating",
        action=(
            "{actor} 朝那副非人的身體貼近，往深處迎去。",
            "{actor} 伸手朝那具身軀探去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 被陌生的熱度整個裹住。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 與人類的體溫交纏在一起。",),
        },
    ),
    NarrationRow(
        "interspecies_domination",
        action=(
            "{actor} 翻身逼近那具身軀，用大腿朝它扣去。",
            "{actor} 抬高身子，朝那具軀體的上方移去。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腿在夾緊之中發燙。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的動作被壓得動彈不得。",),
        },
    ),
    NarrationRow(
        "interspecies_resonance",
        action=(
            "{actor} 張開手臂，朝那具身軀迎去。",
            "{actor} 朝那具身軀靠攏，等著兩邊的律動對上。",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的胸口被陌生的律動帶著走。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的律動逐漸跟上對方的心跳。",),
        },
    ),
)
