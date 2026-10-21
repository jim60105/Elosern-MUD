"""Per-act narration for the 神之秘法 (divine mystery) line.

The register is authority speaking through the caster. Each row adds only the
invocation; the law-giving imagery stays in the shared ``divine_*`` pools, so
the prose here stays short and never restates what a mystery does.

``ROWS`` follows the act registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "divine_extreme_climax_command",
        action=(
            "{actor} 抬手，以律令指向眼前的目標——",
            "{actor} 開口，吐出一個不容違逆的字——",
        ),
    ),
    NarrationRow(
        "divine_timed_copulation",
        action=(
            "{actor} 的手指在空中一劃，把時間撥慢——",
            "{actor} 低聲唸出古老的音節——",
        ),
    ),
    NarrationRow(
        "divine_realm_drain",
        action=(
            "{actor} 張開手，朝目標的方向收攏——",
            "{actor} 的神情不帶溫度，只是抬手——",
        ),
    ),
    NarrationRow(
        "divine_sensitivity_creation",
        action=(
            "{actor} 的指尖朝目標的方向一點——",
            "{actor} 的詠唱落在目標身上——",
        ),
    ),
    NarrationRow(
        "divine_shame_deprivation",
        action=(
            "{actor} 抬手，像是要從目標身上取走什麼——",
            "{actor} 的聲音低下去，帶著不容拒絕的重量——",
        ),
    ),
    NarrationRow(
        "divine_absolute_submission",
        action=(
            "{actor} 抬眼，把目光壓在目標身上——",
            "{actor} 舉手，像是要在誰心上落印——",
        ),
    ),
    NarrationRow(
        "divine_purity_restoration",
        action=(
            "{actor} 合掌，讓光從指縫間漫出——",
            "{actor} 低聲念著逆流的詞句——",
        ),
    ),
    NarrationRow(
        "divine_sexual_arts",
        action=(
            "{actor} 以手勢引出神域的氣息——",
            "{actor} 的低語帶著不屬於凡人的調子——",
        ),
    ),
)
