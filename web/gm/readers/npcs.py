"""NPC inspection reader: character fields plus the NPC-only surfaces.

Everything a player character shows (through the shared
:mod:`web.gm.readers.characters` projection) plus title, profession, service
components, the seven-section persona card with its version, today's schedule
and the current slot, and the dialogue key. The 記憶 and 對話 tabs read through
their own list/detail families (``memories``/``snapshots``/``dialogue``), which
this reader only links to.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers import characters
from web.gm.readers._entities import component_names, dbref_of, label_of, read_attr, typeclass_of
from web.gm.readers._json import json_value
from web.gm.readers._sections import (
    SectionError,
    chip,
    chips,
    column,
    compute_sections,
    empty,
    group,
    groups,
    ledger,
    link,
    list_summary,
    row,
    table,
    table_row,
    tree,
)

KIND = "npcs"

#: Stable Traditional Chinese labels for the entity's service components.
COMPONENT_LABELS: dict[str, str] = {}


def _component_labels() -> dict[str, str]:
    if COMPONENT_LABELS:
        return COMPONENT_LABELS
    from typeclasses import components as component_types

    pairs = (
        (component_types.GuildStaff, "公會櫃檯"),
        (component_types.ChurchHost, "教會神職"),
        (component_types.GuildExaminer, "公會考官"),
        (component_types.Merchant, "商人"),
        (component_types.ScriptedDialogue, "腳本對話"),
        (component_types.QuestIssuer, "委託發布者"),
    )
    for component_type, label in pairs:
        COMPONENT_LABELS[str(component_type.name)] = label
    return COMPONENT_LABELS


def _day_seconds() -> int:
    from world.rules.clock import CLOCK_YAML

    return int(CLOCK_YAML["seconds_per_hour"]) * int(CLOCK_YAML["hours_per_day"])


def _professions(npc: Any) -> list[str]:
    labels = _component_labels()
    names = [name for name in component_names(npc) if name in labels]
    return [labels[name] for name in names]


def _dialogue_key(npc: Any) -> str | None:
    from world.rules.dialogue import dialogue_key_for

    return dialogue_key_for(npc)


def identity_section(npc: Any) -> dict[str, Any]:
    from world.rules import npc_identity

    rows = [
        row("名稱", npc_identity.npc_display_name(npc)),
        row("物件鍵", label_of(npc)),
        row("識別碼", f"#{dbref_of(npc)}", mono=True),
        row("型別", typeclass_of(npc), mono=True),
    ]
    title = npc_identity.npc_title_value(npc)
    rows.append(row("稱號", title or "—"))
    professions = _professions(npc)
    rows.append(row("職業", "、".join(professions) or "—"))
    key = _dialogue_key(npc)
    rows.append(row("對話鍵", key or "—", mono=True))
    location = getattr(npc, "location", None)
    if location is not None:
        rows.append(
            row(
                "所在房間",
                f"#{dbref_of(location)}",
                mono=True,
                link_to=link("rooms", dbref_of(location), label_of(location)),
            )
        )
    return ledger(rows)


def persona_section(npc: Any) -> dict[str, Any]:
    from world.rules import npc_persona

    snapshot = npc_persona.read_npc_persona(npc)
    if isinstance(snapshot, npc_persona.NpcPersonaUnavailable):
        return ledger([], note=f"人物設定目前無法讀取：{snapshot.reason}")
    card = snapshot.card
    items = [
        group("身分", [row("公開身分", card.identity.public or "—"), row("隱秘身分", card.identity.hidden or "—")]),
        group("外貌", [row("外貌", card.appearance or "—")]),
        group("性格", [row("性格", card.personality or "—")]),
        group("語氣", [row("語氣", card.speech_style or "—")]),
        group("生平", [row("生平", card.life_story or "—")]),
        group("習慣", [row("習慣", card.habit or "—")]),
        group("人際連結", [row("人際連結", card.social_connection or "—")]),
    ]
    note = f"版本 {snapshot.version}（世代 {snapshot.generation}）"
    return groups(items, note=note)


def services_section(npc: Any) -> dict[str, Any]:
    labels = _component_labels()
    names = component_names(npc)
    rows = []
    for name in names:
        fields = _component_fields(npc, name)
        rows.append(
            table_row(
                {
                    "component": {"value": labels.get(name, name)},
                    "slot": {"value": name, "mono": True},
                    "fields": {
                        "value": "、".join(f"{key}={value}" for key, value in sorted(fields.items()))
                        or "—",
                        "mono": True,
                    },
                },
                key=name,
            )
        )
    return table(
        [
            column("component", "服務元件"),
            column("slot", "插槽", mono=True),
            column("fields", "欄位", mono=True),
        ],
        rows,
        empty_note="此 NPC 目前沒有服務元件。",
    )


def _component_fields(npc: Any, slot: str) -> dict[str, Any]:
    from web.gm.readers._entities import component_rows

    for entry in component_rows(npc):
        if entry["name"] == slot:
            return dict(entry["fields"])
    return {}


def schedule_section(npc: Any) -> dict[str, Any]:
    from world.rules import npc_schedules
    from world.rules.clock import read_world_clock

    parsed = npc_schedules.parse_stored_schedule(npc)
    if parsed is None:
        return empty("此 NPC 目前沒有排程。")
    clock = read_world_clock()
    current_offset: int | None = None
    if clock is not None:
        current_offset = int(clock.tick) % _day_seconds()
    state = read_attr(npc, "schedule_state", default=None)
    rows = []
    current_index = None
    offsets = sorted(
        (entry.tick_offset for entry in parsed.entries), key=lambda value: value
    )
    if current_offset is not None and offsets:
        eligible = [value for value in offsets if value <= current_offset]
        if eligible:
            current_index = max(eligible)
    for entry in parsed.entries:
        is_current = current_index is not None and entry.tick_offset == current_index
        cells = {
            "offset": {"value": entry.tick_offset, "mono": True},
            "kind": {"value": entry.kind, "mono": True},
            "target": {"value": entry.target or "—", "mono": True},
            "state": {"value": entry.state or "—", "mono": True},
        }
        if is_current:
            cells["offset"]["tone"] = "gold"
        rows.append(table_row(cells, key=f"{entry.tick_offset}:{entry.kind}"))
    note_parts = []
    if parsed.effective_from_tick is not None:
        note_parts.append(f"生效起點 {parsed.effective_from_tick}")
    if current_offset is None:
        note_parts.append("世界時鐘目前無法讀取，僅顯示完整排程")
    elif current_index is None:
        note_parts.append("今日尚無已生效的時段")
    else:
        note_parts.append(f"目前時段 tick_offset={current_index}")
    if state is not None:
        note_parts.append(f"目前狀態 {state}")
    return table(
        [
            column("offset", "當日 tick", mono=True),
            column("kind", "類型", mono=True),
            column("target", "目標", mono=True),
            column("state", "狀態", mono=True),
        ],
        rows,
        note="；".join(note_parts),
    )


def detail(npc: Any) -> dict[str, Any]:
    """The NPC detail payload: shared character sections plus NPC-only ones."""
    from world.rules import npc_identity

    sections = characters.character_sections(npc)
    sections.extend(
        compute_sections(
            [
                ("npc_identity", "NPC 身分", lambda: identity_section(npc)),
                ("persona", "人物設定", lambda: persona_section(npc)),
                ("services", "服務與職業", lambda: services_section(npc)),
                ("schedule", "今日排程", lambda: schedule_section(npc)),
            ]
        )
    )
    dbref = dbref_of(npc)
    sections.append(
        {
            "key": "narrative_tabs",
            "title": "敘事檢視",
            **chips(
                [
                    chip(
                        "記憶",
                        key="memories",
                        link_to=link("memories", f"owner:{dbref}", label_of(npc)),
                    ),
                    chip(
                        "對話",
                        key="dialogue",
                        link_to=link("dialogue", dbref, label_of(npc)),
                    ),
                    chip(
                        "情境快照",
                        key="snapshots",
                        link_to=link("snapshots", f"owner:{dbref}", label_of(npc)),
                    ),
                ]
            ),
        }
    )
    return {
        "id": str(dbref),
        "kind": KIND,
        "label": npc_identity.npc_display_name(npc),
        "dbref": dbref,
        "typeclass": typeclass_of(npc),
        "sections": sections,
    }


def item_of(npc: Any) -> dict[str, Any]:
    """One NPC list row (summary fields only)."""
    from world.rules import npc_identity

    dbref = dbref_of(npc)
    professions = _professions(npc)
    return {
        "id": str(dbref),
        "kind": KIND,
        "dbref": dbref,
        "label": npc_identity.npc_display_name(npc),
        "fields": [
            row("職業", "、".join(professions) or "—"),
            row("稱號", npc_identity.npc_title_value(npc) or "—"),
            row(
                "所在房間",
                label_of(npc.location) if npc.location is not None else "—",
            ),
        ],
    }


# --- NPC narrative tabs (design §5) -----------------------------------------

#: The bounded snapshot projection: the newest ten rows per owner.
MAX_SNAPSHOTS = 10

#: The recall query bound; an over-long query is refused before execution.
MAX_RECALL_QUERY_CODE_POINTS = 2000


def owner_identity(filters: dict[str, Any]) -> tuple[str, Any | None]:
    """The owner identity a narrative-tab filter names, resolved when numeric."""
    from web.gm.readers.errors import InvalidFilter, ObjectNotFound

    raw = filters.get("owner")
    if raw in (None, ""):
        raise InvalidFilter("此檢視必須指定 NPC（?owner=#dbref）。")
    text = str(raw).strip().lstrip("#")
    if not text:
        raise InvalidFilter("擁有者識別碼不正確。")
    if text.isdigit():
        from evennia.objects.models import ObjectDB

        entity = ObjectDB.objects.filter(pk=int(text)).first()
        if entity is None:
            raise ObjectNotFound()
        return str(entity.pk), entity
    return text, None


def memory_list_items(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Filtered effective memory views for one owner (design §5 記憶)."""
    import json

    from world.narrative.memory import get_owner_memories

    owner_id, _entity = owner_identity(filters)
    views = get_owner_memories(
        owner_id=owner_id,
        requester_id=owner_id,
        include_superseded=_flag(filters.get("include_superseded")),
        include_inactive=_flag(filters.get("include_inactive")),
        tier=filters.get("tier") or None,
        scope=filters.get("scope") or None,
        category=filters.get("category") or None,
    )
    items = []
    for view in views:
        items.append(
            {
                "id": str(view.id),
                "kind": "memories",
                "dbref": None,
                "label": str(view.source_id or f"記憶 #{view.id}"),
                "owner": owner_id,
                "fields": [
                    row("類別", view.category, mono=True),
                    row("層級", view.tier, mono=True),
                    row("可用性", view.availability, mono=True),
                    row("知識範圍", view.knowledge_scope, mono=True),
                    row("顯著度", view.salience, mono=True),
                    row("信心", view.confidence, mono=True),
                    row("tick", view.tick, mono=True),
                    row(
                        "來源",
                        view.source_id or "—",
                        mono=True,
                        link_to=link("narrative", f"event:{view.source_id}", "事件")
                        if view.source_id
                        else None,
                    ),
                    row(
                        "內容",
                        json.dumps(view.content, ensure_ascii=False, sort_keys=True),
                        mono=True,
                    ),
                    row("主體", "、".join(str(item) for item in view.subjects) or "—", mono=True),
                ],
            }
        )
    return items


def _flag(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def memory_detail(identity: Any, filters: dict[str, Any]) -> dict[str, Any]:
    """One memory record with its complete revision history."""
    from world.narrative.models import MemoryRecord
    from web.gm.readers.errors import ObjectNotFound

    # The owner is part of the identity: a record projected through this view
    # must belong to the owner the caller named, so a numeric primary key can
    # never reach another owner's cognition.
    owner_id, _entity = owner_identity(filters)
    text = str(identity).strip()
    if not text.isdigit():
        raise ObjectNotFound()
    record = MemoryRecord.objects.filter(pk=int(text)).first()
    if record is None:
        raise ObjectNotFound()
    if str(record.owner_id) != owner_id:
        raise ObjectNotFound()

    def identity_section() -> dict[str, Any]:
        return ledger(
            [
                row("紀錄", record.pk, mono=True),
                row("擁有者", record.owner_id, mono=True),
                row("類別", record.category, mono=True),
                row("tick", record.tick, mono=True),
                row("顯著度", record.salience, mono=True),
                row("信心", record.confidence, mono=True),
                row("知識範圍", record.knowledge_scope, mono=True),
                row("有效層級", record.effective_tier, mono=True),
                row("有效可用性", record.effective_availability, mono=True),
                row("最新修訂", record.latest_revision_number, mono=True),
                row(
                    "來源",
                    record.source_id or "—",
                    mono=True,
                    link_to=link("narrative", f"event:{record.source_id}", "事件")
                    if record.source_id
                    else None,
                ),
                row(
                    "投影版本",
                    record.projector_version if record.projector_version is not None else "—",
                    mono=True,
                ),
                row(
                    "衍生世代",
                    record.derived_generation if record.derived_generation is not None else "—",
                    mono=True,
                ),
            ]
        )

    def revision_section() -> dict[str, Any]:
        revisions = record.revisions.order_by("-revision_number", "-id")
        return table(
            [
                column("revision", "修訂", mono=True),
                column("availability", "可用性", mono=True),
                column("tier", "層級", mono=True),
                column("supersedes", "取代", mono=True),
                column("decay", "衰減", mono=True),
                column("relations", "關聯", mono=True),
                column("created", "建立時間", mono=True),
            ],
            [
                table_row(
                    {
                        "revision": {"value": entry.revision_number, "mono": True},
                        "availability": {"value": entry.availability, "mono": True},
                        "tier": {"value": entry.tier, "mono": True},
                        "supersedes": {"value": entry.supersedes_record_id or "—", "mono": True},
                        "decay": {"value": json_value(entry.decay_metadata), "mono": True},
                        "relations": {"value": json_value(entry.relations), "mono": True},
                        "created": {"value": json_value(entry.created_at), "mono": True},
                    },
                    key=str(entry.pk),
                )
                for entry in revisions
            ],
            empty_note="此記憶沒有修訂紀錄。",
        )

    sections = compute_sections(
        [
            ("identity", "記憶紀錄", identity_section),
            ("content", "內容", lambda: tree(json_value(record.content))),
            ("revisions", "修訂歷史", revision_section),
            (
                "subjects",
                "主體",
                lambda: list_summary([str(item) for item in (record.subjects or [])])
                if record.subjects
                else empty("此記憶沒有主體。"),
            ),
        ]
    )
    return {
        "id": str(record.pk),
        "kind": "memories",
        "label": str(record.source_id or f"記憶 #{record.pk}"),
        "dbref": None,
        "typeclass": "",
        "sections": sections,
        "raw": {
            "record": json_value(
                {
                    "id": record.pk,
                    "owner_id": record.owner_id,
                    "tick": record.tick,
                    "category": record.category,
                    "content": record.content,
                    "salience": record.salience,
                    "knowledge_scope": record.knowledge_scope,
                    "confidence": record.confidence,
                    "subjects": record.subjects,
                    "source_id": record.source_id,
                    "projector_version": record.projector_version,
                    "derived_generation": record.derived_generation,
                    "effective_tier": record.effective_tier,
                    "effective_availability": record.effective_availability,
                    "latest_revision_number": record.latest_revision_number,
                }
            )
        },
    }


def snapshot_list_items(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """The newest ten context snapshots for one owner."""
    from world.narrative.models import NarrativeContextSnapshot

    owner_id, _entity = owner_identity(filters)
    rows = NarrativeContextSnapshot.objects.filter(owner_id=owner_id).order_by(
        "-created_at", "-id"
    )[:MAX_SNAPSHOTS]
    items = []
    for snapshot in rows:
        payload = snapshot.rendered_payload or {}
        items.append(
            {
                "id": snapshot.snapshot_id,
                "kind": "snapshots",
                "dbref": None,
                "label": snapshot.capability,
                "owner": owner_id,
                "fields": [
                    row("能力", snapshot.capability, mono=True),
                    row("擁有者世代", snapshot.owner_generation, mono=True),
                    row("建立時間", json_value(snapshot.created_at), mono=True),
                    row("區塊數", len(payload.get("sections") or []), mono=True),
                    row("截斷決策數", len(snapshot.truncation_decisions or []), mono=True),
                ],
            }
        )
    return items


def snapshot_detail(identity: Any, filters: dict[str, Any]) -> dict[str, Any]:
    """One context snapshot: sections, token accounting and evidence links."""
    from world.narrative.models import NarrativeContextSnapshot
    from web.gm.readers.errors import ObjectNotFound

    owner_id, _entity = owner_identity(filters)
    snapshot = NarrativeContextSnapshot.objects.filter(snapshot_id=str(identity)).first()
    if snapshot is None:
        raise ObjectNotFound()
    if str(snapshot.owner_id) != owner_id:
        raise ObjectNotFound()
    payload = snapshot.rendered_payload or {}

    def sections() -> dict[str, Any]:
        stored = payload.get("sections") or []
        return table(
            [
                column("name", "區塊", mono=True),
                column("heading", "標題", mono=True),
                column("tokens", "token 數", mono=True),
                column("sha256", "雜湊", mono=True),
            ],
            [
                table_row(
                    {
                        "name": {"value": entry.get("name", "—"), "mono": True},
                        "heading": {"value": entry.get("heading", "—"), "mono": True},
                        "tokens": {"value": entry.get("token_count", "—"), "mono": True},
                        "sha256": {"value": str(entry.get("sha256", ""))[:16], "mono": True},
                    },
                    key=str(index),
                )
                for index, entry in enumerate(stored)
                if isinstance(entry, dict)
            ],
            empty_note="此快照沒有保存任何區塊。",
        )

    def truncations() -> dict[str, Any]:
        decisions = [str(item) for item in (snapshot.truncation_decisions or [])]
        if not decisions:
            return empty("此快照沒有截斷或捨棄的來源。")
        return list_summary(decisions)

    def sources() -> dict[str, Any]:
        stored = snapshot.sources or []
        return table(
            [
                column("source", "來源", mono=True),
                column("record", "紀錄", mono=True),
                column("revision", "修訂", mono=True),
                column("scope", "知識範圍", mono=True),
                column("owner", "擁有者", mono=True),
                column("thread", "故事線修訂", mono=True),
            ],
            [
                table_row(
                    {
                        "source": {"value": entry.get("source_id", "—"), "mono": True},
                        "record": {"value": entry.get("record_id", "—"), "mono": True},
                        "revision": {"value": entry.get("revision_number", "—"), "mono": True},
                        "scope": {"value": entry.get("knowledge_scope", "—"), "mono": True},
                        "owner": {"value": entry.get("owner_id", "—"), "mono": True},
                        "thread": {"value": entry.get("thread_revision", "—"), "mono": True},
                    },
                    key=str(index),
                )
                for index, entry in enumerate(stored)
                if isinstance(entry, dict)
            ],
            empty_note="此快照沒有來源紀錄。",
        )

    sections_payload = compute_sections(
        [
            (
                "identity",
                "情境快照",
                lambda: ledger(
                    [
                        row("快照識別", snapshot.snapshot_id, mono=True),
                        row("能力", snapshot.capability, mono=True),
                        row("擁有者", snapshot.owner_id, mono=True),
                        row("擁有者世代", snapshot.owner_generation, mono=True),
                        row("提示版本", snapshot.prompt_version, mono=True),
                        row("結構版本", snapshot.schema_version or "—", mono=True),
                        row("渲染版本", snapshot.rendering_version, mono=True),
                        row("建立時間", json_value(snapshot.created_at), mono=True),
                    ]
                ),
            ),
            ("sections", "區塊", sections),
            ("tokens", "token 計量", lambda: tree(json_value(snapshot.budget_accounting))),
            ("truncation", "截斷與捨棄", truncations),
            ("sources", "來源", sources),
            ("evidence", "S2 證據連結", lambda: _snapshot_evidence(payload)),
        ]
    )
    return {
        "id": snapshot.snapshot_id,
        "kind": "snapshots",
        "label": snapshot.capability,
        "dbref": None,
        "typeclass": "",
        "sections": sections_payload,
        "raw": {
            "record": json_value(
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "capability": snapshot.capability,
                    "prompt_version": snapshot.prompt_version,
                    "schema_version": snapshot.schema_version,
                    "rendering_version": snapshot.rendering_version,
                    "owner_id": snapshot.owner_id,
                    "owner_generation": snapshot.owner_generation,
                    "thread_revisions": snapshot.thread_revisions,
                    "section_hashes": snapshot.section_hashes,
                }
            )
        },
    }


def _snapshot_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Existing S2 evidence the snapshot names, if any (never inferred)."""
    import re

    call_id = payload.get("call_id")
    trace_id = payload.get("trace_id")
    rows = []
    if trace_id:
        rows.append(row("trace_id", str(trace_id), mono=True))
    if call_id:
        text = str(call_id)
        rows.append(
            row(
                "call_id",
                text,
                mono=True,
                link_to=link("call", text) if re.fullmatch(r"[0-9a-f]{32}", text) else None,
            )
        )
    if not rows:
        return empty("此快照沒有可用的 S2 證據連結。")
    return ledger(rows)


def dialogue_list_items(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Dialogue epochs and frames grouped by player, for one NPC owner."""
    from world.narrative.epochs import epoch_frames
    from world.narrative.models import DialogueEpoch

    owner_id, _entity = owner_identity(filters)
    epochs = DialogueEpoch.objects.filter(npc_id=owner_id).order_by(
        "player_id", "sequence", "id"
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for epoch in epochs:
        grouped.setdefault(epoch.player_id, []).append(
            {
                "epoch_id": epoch.pk,
                "sequence": epoch.sequence,
                "version": epoch.version,
                "reason": epoch.reason,
                "start_turn_id": epoch.start_turn_id,
                "summary": epoch.summary,
                "generation_id": epoch.generation_id,
                "snapshot_id": epoch.snapshot_id,
                "source_refs": json_value(epoch.source_refs),
                "frames": [
                    {
                        "identity": frame.identity,
                        "tick": frame.tick,
                        "content": frame.content,
                        "sources": json_value(frame.sources),
                    }
                    for frame in epoch_frames(epoch)
                ],
            }
        )
    items = []
    for player_id, entries in grouped.items():
        items.append(
            {
                "id": player_id,
                "kind": "dialogue",
                "dbref": None,
                "label": player_id,
                "owner": owner_id,
                "epochs": entries,
                "fields": [
                    row("玩家", player_id, mono=True),
                    row("紀元數", len(entries), mono=True),
                    row(
                        "對話框數",
                        sum(len(entry["frames"]) for entry in entries),
                        mono=True,
                    ),
                ],
            }
        )
    return items


def dialogue_detail(identity: Any, filters: dict[str, Any]) -> dict[str, Any]:
    """One player's dialogue epochs and frames, with S2 call links."""
    import re

    from world.narrative.epochs import epoch_frames
    from world.narrative.models import DialogueEpoch, DialogueFrame
    from web.gm.readers.errors import ObjectNotFound

    owner_id, _npc = owner_identity(filters)
    player_id = str(identity)
    epochs = list(
        DialogueEpoch.objects.filter(npc_id=owner_id, player_id=player_id).order_by(
            "sequence", "id"
        )
    )
    if not epochs:
        raise ObjectNotFound()

    def epoch_groups() -> dict[str, Any]:
        items = []
        for epoch in epochs:
            rows = []
            for frame in epoch_frames(epoch):
                call_id = next(
                    (
                        str(entry.get("call_id"))
                        for entry in (frame.sources or [])
                        if isinstance(entry, dict)
                        and entry.get("call_id")
                        and re.fullmatch(r"[0-9a-f]{32}", str(entry.get("call_id")))
                    ),
                    None,
                )
                rows.append(
                    row(
                        frame.identity,
                        frame.content,
                        key=str(frame.pk),
                        link_to=link("call", call_id) if call_id else None,
                    )
                )
            items.append(
                group(
                    f"第 {epoch.sequence} 紀元",
                    rows,
                    key=str(epoch.pk),
                    note="；".join(
                        part
                        for part in (
                            f"版本 {epoch.version}",
                            f"成因 {epoch.reason}",
                            f"摘要 {epoch.summary}" if epoch.summary else "",
                            f"快照 {epoch.snapshot_id}" if epoch.snapshot_id else "",
                        )
                        if part
                    ),
                )
            )
        return groups(items)

    sections = compute_sections(
        [
            (
                "identity",
                "對話",
                lambda: ledger(
                    [
                        row("NPC", owner_id, mono=True),
                        row("玩家", player_id, mono=True),
                        row("紀元數", len(epochs), mono=True),
                        row(
                            "對話框總數",
                            DialogueFrame.objects.filter(epoch__in=epochs).count(),
                            mono=True,
                        ),
                    ]
                ),
            ),
            ("epochs", "紀元與對話框", epoch_groups),
        ]
    )
    return {
        "id": player_id,
        "kind": "dialogue",
        "label": player_id,
        "dbref": None,
        "typeclass": "",
        "sections": sections,
    }


def recall(owner_identity_value: Any, body: dict[str, Any]) -> dict[str, Any]:
    """The read-only recall preview (§5 記憶): same query, same permissions."""
    from typeclasses.npcs import NPC
    from world.narrative.recall import fast_recall
    from web.gm.readers.errors import (
        InvalidFilter,
        KindMismatch,
        ObjectNotFound,
        QueryTooLong,
    )

    query = str((body or {}).get("query", ""))
    if len(query) > MAX_RECALL_QUERY_CODE_POINTS:
        raise QueryTooLong()
    text = str(owner_identity_value or "").strip().lstrip("#")
    if not text.isdigit():
        raise InvalidFilter("recall 必須指定 NPC 的 dbref。")
    npc = NPC.objects.filter(pk=int(text)).first()
    if npc is None:
        raise ObjectNotFound()
    thread = (body or {}).get("thread")
    result = fast_recall(
        owner_id=str(npc.pk),
        requester_id=str(npc.pk),
        query=query,
        thread_id=str(thread) if thread else None,
        include_superseded=_flag((body or {}).get("include_superseded")),
        include_inactive=_flag((body or {}).get("include_inactive")),
    )

    def selection(entry: Any) -> dict[str, Any]:
        view = getattr(entry, "view", entry)
        payload = {
            "id": view.id,
            "tier": view.tier,
            "category": view.category,
            "salience": view.salience,
            "confidence": view.confidence,
            "source_id": view.source_id,
            "tick": view.tick,
            "content": json_value(view.content),
        }
        if hasattr(entry, "final_score"):
            payload["score"] = {
                "lexical": entry.lexical_score,
                "metadata": entry.metadata_bonus,
                "final": entry.final_score,
            }
        return payload

    return {
        "owner_id": result.owner_id,
        "generation": result.generation,
        "tokenizer_version": result.tokenizer_version,
        "ranker_version": result.ranker_version,
        "query": result.query,
        "thread_id": result.thread_id,
        "thread_revision": result.thread_revision,
        "core": [selection(entry) for entry in result.core],
        "working": [selection(entry) for entry in result.working],
        "recalled": [selection(entry) for entry in result.recalled],
    }


__all__ = [
    "KIND",
    "MAX_RECALL_QUERY_CODE_POINTS",
    "MAX_SNAPSHOTS",
    "detail",
    "dialogue_detail",
    "dialogue_list_items",
    "item_of",
    "memory_detail",
    "memory_list_items",
    "owner_identity",
    "recall",
    "snapshot_detail",
    "snapshot_list_items",
]
