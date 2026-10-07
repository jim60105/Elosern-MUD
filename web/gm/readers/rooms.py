"""Room inspection reader (S3 §4 "Room").

Coordinates and map layer come from the room typeclass itself, exits and
occupants from the room's own contents, and instance ownership/lifetime from
the instance room's stored attributes — all read through non-creating access.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._entities import dbref_of, label_of, read_attr, typeclass_of
from web.gm.readers._sections import (
    column,
    compute_sections,
    empty,
    group,
    groups,
    ledger,
    link,
    row,
    table,
    table_row,
)

KIND = "rooms"


def place_kind(room: Any) -> str:
    """The map layer this room belongs to, most specific first."""
    from typeclasses.rooms import (
        AnchorRoom,
        GridRoom,
        InstanceRoom,
        LimboRoom,
        Room,
        TerrainRoom,
    )

    for room_type, label in (
        (InstanceRoom, "實例房間"),
        (AnchorRoom, "錨點房間"),
        (TerrainRoom, "荒野地形"),
        (GridRoom, "格線房間"),
        (LimboRoom, "虛境"),
        (Room, "房間"),
    ):
        if isinstance(room, room_type):
            return label
    return type(room).__name__


def coordinates(room: Any) -> list[int] | None:
    """The room's ``(x, y, z)`` grid coordinates, when it has any."""
    value = getattr(room, "xyz", None)
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return [int(part) for part in value]
    return None


def identity_section(room: Any) -> dict[str, Any]:
    rows = [
        row("名稱", label_of(room)),
        row("識別碼", f"#{dbref_of(room)}", mono=True),
        row("型別", typeclass_of(room), mono=True),
        row("地點類型", place_kind(room)),
    ]
    coords = coordinates(room)
    if coords is not None:
        rows.append(row("座標", ", ".join(str(part) for part in coords), mono=True))
    anchor_key = read_attr(room, "anchor_key", default=None)
    if anchor_key:
        rows.append(row("錨點鍵", str(anchor_key), mono=True))
    archetype = read_attr(room, "scene_archetype", default=None)
    if archetype:
        rows.append(row("場景原型", str(archetype), mono=True))
    return ledger(rows)


def exits_section(room: Any) -> dict[str, Any]:
    rows = []
    for index, exit_obj in enumerate(list(getattr(room, "exits", []) or [])):
        destination = getattr(exit_obj, "destination", None)
        dbref = dbref_of(exit_obj)
        cells = {
            "direction": {"value": label_of(exit_obj), "mono": True},
            "exit": {"value": f"#{dbref}", "mono": True, "link": link("object", dbref, label_of(exit_obj))},
            "destination": (
                {
                    "value": f"#{dbref_of(destination)}",
                    "mono": True,
                    "link": link("rooms", dbref_of(destination), label_of(destination)),
                }
                if destination is not None
                else {"value": "—"}
            ),
        }
        rows.append(table_row(cells, key=f"{index}:{dbref}"))
    return table(
        [
            column("direction", "方向", mono=True),
            column("exit", "出口", mono=True),
            column("destination", "目的地", mono=True),
        ],
        rows,
        empty_note="此房間沒有出口。",
    )


def occupants_section(room: Any) -> dict[str, Any]:
    from typeclasses.characters import PlayerCharacter
    from typeclasses.exits import Exit
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC

    buckets: dict[str, list[Any]] = {"player": [], "npc": [], "monster": [], "object": []}
    for entity in list(getattr(room, "contents", []) or []):
        if isinstance(entity, Exit):
            continue
        if isinstance(entity, Monster):
            buckets["monster"].append(entity)
        elif isinstance(entity, NPC):
            buckets["npc"].append(entity)
        elif isinstance(entity, PlayerCharacter):
            buckets["player"].append(entity)
        else:
            buckets["object"].append(entity)
    labels = {"player": "玩家角色", "npc": "NPC", "monster": "魔物", "object": "物件"}
    kind_of = {"player": "characters", "npc": "npcs", "monster": "monsters", "object": "object"}
    items = []
    for bucket, entries in buckets.items():
        if not entries:
            continue
        rows = []
        for entity in entries:
            dbref = dbref_of(entity)
            rows.append(
                row(
                    label_of(entity),
                    f"#{dbref}",
                    key=f"{bucket}:{dbref}",
                    mono=True,
                    link_to=link(kind_of[bucket], dbref, label_of(entity)),
                )
            )
        items.append(group(labels[bucket], rows, key=bucket))
    if not items:
        return empty("此房間目前沒有內容物。")
    return groups(items)


def instance_section(room: Any) -> dict[str, Any]:
    from typeclasses.rooms import InstanceRoom

    if not isinstance(room, InstanceRoom):
        return empty("這不是實例房間。")
    rows = []
    origin = read_attr(room, "origin_room", default=None)
    if origin is not None:
        rows.append(
            row(
                "來源房間",
                f"#{dbref_of(origin)}",
                mono=True,
                link_to=link("rooms", dbref_of(origin), label_of(origin)),
            )
        )
    expire_tick = read_attr(room, "expire_tick", default=None)
    rows.append(
        row(
            "到期 tick",
            "已提升為永久" if expire_tick is None else expire_tick,
            mono=True,
            tone="ok" if expire_tick is None else None,
        )
    )
    named = read_attr(room, "named", default=False)
    rows.append(row("已命名", "是" if named else "否"))
    interacted = read_attr(room, "interacted", default=False)
    rows.append(row("已互動", "是" if interacted else "否"))
    pins = read_attr(room, "pin_reasons", default=None)
    rows.append(row("釘住原因", "、".join(str(item) for item in pins) if pins else "—"))
    owned = read_attr(room, "owned_entities", default=None)
    owned_rows = []
    for entity in list(owned or []):
        dbref = dbref_of(entity)
        if dbref is None:
            continue
        owned_rows.append(
            row(
                label_of(entity),
                f"#{dbref}",
                key=f"owned:{dbref}",
                mono=True,
                link_to=link("object", dbref, label_of(entity)),
            )
        )
    if owned_rows:
        return groups(
            [
                group("實例狀態", rows, key="state"),
                group("擁有的實體", owned_rows, key="owned"),
            ]
        )
    return ledger(rows)


def detail(room: Any) -> dict[str, Any]:
    sections = compute_sections(
        [
            ("identity", "身分與座標", lambda: identity_section(room)),
            ("exits", "出口", lambda: exits_section(room)),
            ("occupants", "內容物", lambda: occupants_section(room)),
            ("instance", "實例狀態", lambda: instance_section(room)),
        ]
    )
    dbref = dbref_of(room)
    return {
        "id": str(dbref),
        "kind": KIND,
        "label": label_of(room),
        "dbref": dbref,
        "typeclass": typeclass_of(room),
        "sections": sections,
    }


def item_of(room: Any) -> dict[str, Any]:
    """One room list row (summary fields only)."""
    dbref = dbref_of(room)
    coords = coordinates(room)
    return {
        "id": str(dbref),
        "kind": KIND,
        "dbref": dbref,
        "label": label_of(room),
        "fields": [
            row("地點類型", place_kind(room)),
            row("座標", ", ".join(str(part) for part in coords) if coords else "—", mono=True),
            row("出口數", len(list(getattr(room, "exits", []) or []))),
        ],
    }


__all__ = ["KIND", "coordinates", "detail", "item_of", "place_kind"]
