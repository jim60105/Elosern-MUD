"""Per-act narration for the 羞恥 (shame) line.

The register is exposure and the heat it leaves: a hem raised, a collar
loosened, a body discovered by other eyes. The prose never stages humiliation
as a spectacle; the heat belongs to the body that chose to be seen. Self
exposure acts voice the acting body's pleasure, and the three area acts add
the clause for a body caught in that gaze.

``ROWS`` follows the act registry's own in-order block; order is authoring
order, not a behavioural input.
"""

from __future__ import annotations

from .vocab import NarrationRow

ROWS: tuple[NarrationRow, ...] = (
    NarrationRow(
        "shame_hem_lift",
        action=(
            "{actor} 捏住衣襬，慢慢往上提——",
            "{actor} 的手按在衣角上，作勢掀起——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腰側在空氣裡泛起涼意。",),
        },
    ),
    NarrationRow(
        "shame_half_expose_chest",
        action=(
            "{actor} 拉低領口，讓鎖骨露出來——",
            "{actor} 把衣領往旁一帶，胸口露出半邊——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的胸前在目光裡發燙。",),
        },
    ),
    NarrationRow(
        "shame_half_expose_lower",
        action=(
            "{actor} 捏住裙擺，緩緩往上收——",
            "{actor} 的膝蓋微微一屈，讓下襬鬆開——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的腿間在涼意裡縮了一下。",),
        },
    ),
    NarrationRow(
        "shame_loosen_collar",
        action=(
            "{actor} 抬手解開胸前的釦子——",
            "{actor} 的指尖挑開衣襟的第一道縫——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的鎖骨下透進一陣風。",),
        },
    ),
    NarrationRow(
        "shame_full_expose",
        action=(
            "{actor} 伸手拉開最後一層遮掩——",
            "{actor} 一件件卸下身上的衣物——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的全身在空氣裡毫無遮蔽。",),
        },
    ),
    NarrationRow(
        "shame_public_masturbation",
        action=(
            "{actor} 在眾人眼前把手探向自己腿間——",
            "{actor} 當著那些視線，慢慢張開雙腿——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的私處在注視下更快地熱起來。",),
        },
    ),
    NarrationRow(
        "shame_provocative_gaze",
        action=(
            "{actor} 抬眼，把挑逗的目光送向對方——",
            "{actor} 偏過頭，讓視線在對方身上停住——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 的呼吸先亂了一拍。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 被那道目光看得心神一盪。",),
        },
    ),
    NarrationRow(
        "shame_public_performance",
        action=(
            "{actor} 站到眾人眼前，慢慢擺開身體——",
            "{actor} 抬起下巴，把整個人交到視線底下——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 在眾目之下越演越熱。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 的目光被那具身體牽住。",),
        },
    ),
    NarrationRow(
        "shame_devoted_pose",
        action=(
            "{actor} 屈膝跪坐，把自己攤開在眾人面前——",
            "{actor} 垂下肩，擺出獻出一切的姿態——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 在獻出的姿勢裡發燙。",),
        },
        participant_lines={
            "pleasure_gain": ("{target} 看著那份毫無保留的姿態。",),
        },
    ),
    NarrationRow(
        "shame_shameless_declaration",
        action=(
            "{actor} 抬起頭，開口宣告自己的無恥——",
            "{actor} 迎著視線，把心裡的話說出聲——",
        ),
        performer_lines={
            "pleasure_gain": ("{actor} 說出口的話讓自己更熱。",),
        },
    ),
)
