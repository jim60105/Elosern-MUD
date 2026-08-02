"""Immutable keyed dialogue tables (onboarding-guide D5, scripted-dialogue D2).

Keyed by ``dialogue_key`` so the same table can be attached to any NPC.
Each table is a frozen ``DialogueDefinition`` carrying an optional no-keyword
greeting plus its keyword responses. No imports from ``world.rules``,
``typeclasses``, or Evennia.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class KeywordResponse:
    """One authored response to a player keyword."""

    keyword: str
    response: str


@dataclass(frozen=True)
class DialogueDefinition:
    """One immutable dialogue table: an optional greeting plus keyword responses.

    ``greeting`` is the no-keyword topic line shown by ``talk <npc>``. ``None``
    means the host has no authored greeting and falls back to the no-response
    line for a keyword-less talk.
    """

    greeting: str | None
    responses: tuple[KeywordResponse, ...]


GUARD_DIALOGUE_KEY = "south_gate_guard"
GUILD_STAFF_DIALOGUE_KEY = "guild_staff"

NO_UNDERSTANDING_LINE = "對方皺起眉頭：「我不太明白你的意思。」"

GUARD_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "公會",
        "「冒險者公會就在南大道的東端。先向北走到南大道，再向東走，"
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

GUILD_STAFF_RESPONSES: tuple[KeywordResponse, ...] = (
    KeywordResponse(
        "註冊",
        "「先在櫃檯註冊成為冒險者（guild register），你的階級會是 F，"
        "之後就可以接取任務了。」",
    ),
    KeywordResponse(
        "任務",
        "「用 guild list 查看任務板上適合你階級的委託，用 guild accept "
        "<任務名> 接取，完成後用 guild turnin <任務編號> 回報。」",
    ),
    KeywordResponse(
        "公會",
        "「這裡是埃洛西恩冒險者公會的阿爾托利亞分會。公會命令有 "
        "guild register、guild list、guild accept、guild log、guild show、"
        "guild turnin、guild abandon 與 guild merit。」",
    ),
    KeywordResponse(
        "工會",
        "「你是想問冒險者公會的事吧？用 guild 相關命令可以註冊、接取"
        "任務、查看進度與回報。」",
    ),
    KeywordResponse(
        "再見",
        "「願你的冒險順遂。需要的時候，隨時回來公會。」",
    ),
)

DIALOGUE_TABLE: MappingProxyType = MappingProxyType(
    {
        GUARD_DIALOGUE_KEY: DialogueDefinition(
            greeting=None,
            responses=GUARD_RESPONSES,
        ),
        GUILD_STAFF_DIALOGUE_KEY: DialogueDefinition(
            greeting=(
                "櫃檯的公會職員抬起頭：「歡迎來到冒險者公會。想成為冒險者，"
                "就用 guild register 註冊；之後用 guild list 查看任務、"
                "guild accept 接取、guild log 與 guild show 查看進度，"
                "完成後以 guild turnin 回報，還有 guild abandon 與 guild merit。」"
            ),
            responses=GUILD_STAFF_RESPONSES,
        ),
    }
)
