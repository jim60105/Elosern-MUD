"""Immutable guard keyword-to-response dialogue table (onboarding-guide D5).

Keyed by ``dialogue_key`` so the same table can be attached to any NPC later.
No imports from ``world.rules``, ``typeclasses``, or Evennia.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordResponse:
    """One authored guard response to a player keyword."""

    keyword: str
    response: str


GUARD_DIALOGUE_KEY = "south_gate_guard"

NO_UNDERSTANDING_LINE = "守衛皺起眉頭：「我不太明白你的意思。」"

GUARD_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "公會",
        "「冒險者公會就在北邊的中央廣場附近。沿著南大道往北走，"
        "你很快就會看到那棟掛著招牌的大建築。」",
    ),
    KeywordResponse(
        "冒險",
        "「想要踏上冒險，先到公會註冊成為冒險者吧。公會會為你準備"
        "第一份適合新手的討伐委託。」",
    ),
    KeywordResponse(
        "危險",
        "「王都外的荒野並不安全，低階魔物對新手依然致命。"
        "出發前記得在公會補給，不要單獨深入。」",
    ),
    KeywordResponse(
        "再見",
        "「祝你一路順風，冒險者。需要指引的時候，隨時回來找我。」",
    ),
)

DIALOGUE_TABLE: dict[str, tuple[KeywordResponse, ...]] = {
    GUARD_DIALOGUE_KEY: GUARD_RESPONSES,
}
