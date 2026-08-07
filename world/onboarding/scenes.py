"""Immutable arrival-scene beat data for the onboarding guide (D1).

Every beat is a frozen dataclass describing one authored step of the South Gate
arrival scene. ``GUIDED_CORRIDOR`` is a data constant of the room keys that keep
the guide active; entering any other room marks the guide skipped. No imports
from ``world.rules``, ``typeclasses``, or Evennia.
"""

from dataclasses import dataclass
from enum import StrEnum


class TriggerKind(StrEnum):
    """The kind of player action that advances a beat."""

    COMMAND_LOOK = "command_look"
    ENTER_ROOM = "enter_room"


@dataclass(frozen=True)
class Beat:
    """One authored onboarding beat with its continuation."""

    beat_id: str
    prose: str
    trigger: TriggerKind
    next_beat_id: str | None


ARRIVAL_BEAT_ID = "arrival"
LOOK_BEAT_ID = "look"
GUIDANCE_BEAT_ID = "guidance"

GUIDED_CORRIDOR: frozenset[str] = frozenset(
    {"南門", "南大道", "中央廣場", "冒險者公會外"}
)
SOUTH_GATE_ROOM_KEY = "南門"
GUILD_EXTERIOR_ROOM_KEY = "冒險者公會外"

ARRIVAL_BEAT = Beat(
    beat_id=ARRIVAL_BEAT_ID,
    prose=(
        "你踏上了伊洛瑟恩大陸的土地。聖潔王都的南門在你身後展開，"
        "城牆投下長長的影子，市集的吆喝聲從街道深處隱約傳來。"
    ),
    trigger=TriggerKind.ENTER_ROOM,
    next_beat_id=LOOK_BEAT_ID,
)

LOOK_BEAT = Beat(
    beat_id=LOOK_BEAT_ID,
    prose=(
        "守衛打量了你一眼，開口說道：「你是新來的冒險者吧？"
        "先用「看」看看四周，熟悉一下這座城門。之後我會告訴你該往哪裡走。」"
    ),
    trigger=TriggerKind.COMMAND_LOOK,
    next_beat_id=GUIDANCE_BEAT_ID,
)

GUIDANCE_BEAT = Beat(
    beat_id=GUIDANCE_BEAT_ID,
    prose=(
        "守衛點頭：「先向北走到南大道，再向東到冒險者公會外。"
        "到那裡去註冊，領取你的第一份委託。」"
    ),
    trigger=TriggerKind.ENTER_ROOM,
    next_beat_id=None,
)

BEAT_REGISTRY: dict[str, Beat] = {
    ARRIVAL_BEAT_ID: ARRIVAL_BEAT,
    LOOK_BEAT_ID: LOOK_BEAT,
    GUIDANCE_BEAT_ID: GUIDANCE_BEAT,
}
