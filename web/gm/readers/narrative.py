"""Narrative record inspection reader (S3 §4 "Narrative").

One projectable subtype per approved record family — events, story threads,
letters, dream sessions, director decisions, scheduled beats, authoring drafts
and creative requests — projected from the narrative models through pure reads.
Subtype detail also exposes the stored record fields as raw data, because these
are Django records, not Evennia objects with Attributes (design §3).
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._json import json_value
from web.gm.readers._sections import (
    cell,
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
    text,
    tree,
)

KIND = "narrative"

SUBTYPES = (
    "event",
    "thread",
    "letter",
    "dream",
    "decision",
    "beat",
    "draft",
    "request",
)

SUBTYPE_LABELS = {
    "event": "事件",
    "thread": "故事線",
    "letter": "書信",
    "dream": "夢境",
    "decision": "導演決策",
    "beat": "排程節拍",
    "draft": "創作草稿",
    "request": "創作請求",
}


def split_identity(raw: Any) -> tuple[str, str]:
    """Split ``<subtype>:<identity>``; a bare identity is an error."""
    from web.gm.readers.errors import InvalidFilter

    value = str(raw or "").strip()
    subtype, separator, identity = value.partition(":")
    if not separator or subtype not in SUBTYPES or not identity:
        raise InvalidFilter(
            "敘事紀錄的識別碼格式為 <subtype>:<identity>，其中 subtype 必須是 "
            + "、".join(SUBTYPES)
            + "。"
        )
    return subtype, identity


def source_link(source_kind: Any, source_ref: Any) -> dict[str, Any] | None:
    """The link a provenance reference resolves to, or None when unaddressable."""
    kind = str(source_kind or "")
    reference = str(source_ref or "")
    if not reference:
        return None
    if kind == "event":
        return link("narrative", f"event:{reference}", "事件")
    if kind == "letter":
        return link("narrative", f"letter:{reference}", "書信")
    if kind == "thread":
        return link("narrative", f"thread:{reference}", "故事線")
    if kind == "dream":
        return link("narrative", f"dream:{reference}", "夢境")
    if kind == "request":
        return link("narrative", f"request:{reference}", "創作請求")
    if kind == "draft":
        return link("narrative", f"draft:{reference}", "創作草稿")
    if kind == "memory":
        identifier = reference.split(":", 1)[1] if ":" in reference else reference
        return link("memories", identifier, "記憶")
    return None


def _identity_cell(source_kind: Any, source_ref: Any) -> dict[str, Any]:
    target = source_link(source_kind, source_ref)
    value = {"value": str(source_ref or "—"), "mono": True}
    if target is not None:
        value["link"] = target
    return value


# --- lists ------------------------------------------------------------------


def list_items(subtype: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Every record of one subtype, newest first with a unique tie-break."""
    from world.narrative import models

    owner = filters.get("owner")
    if subtype == "event":
        queryset = models.NarrativeEvent.objects.all()
        if filters.get("event_type"):
            queryset = queryset.filter(event_type=str(filters["event_type"]))
        if filters.get("visibility"):
            queryset = queryset.filter(visibility=str(filters["visibility"]))
        if owner:
            queryset = queryset.filter(location=str(owner))
        rows = queryset.order_by("-tick", "-id")
        return [
            _item(
                "event",
                record.source_id,
                record.event_type,
                [
                    row("事件類型", record.event_type, mono=True),
                    row("tick", record.tick, mono=True),
                    row("可見性", record.visibility),
                    row("地點", record.location or "—"),
                ],
            )
            for record in rows
        ]
    if subtype == "thread":
        queryset = models.StoryThread.objects.all()
        if filters.get("state"):
            queryset = queryset.filter(state=str(filters["state"]))
        rows = queryset.order_by("-created_tick", "-id")
        if owner:
            rows = [
                record
                for record in rows
                if str(owner) in {str(item) for item in (record.participants or [])}
                or str(owner) in {str(item) for item in (record.visible_to or [])}
            ]
        return [
            _item(
                "thread",
                record.thread_id,
                record.origin,
                [
                    row("狀態", record.state),
                    row("修訂", record.revision, mono=True),
                    row("建立 tick", record.created_tick, mono=True),
                    row("來源", record.origin or "—"),
                ],
            )
            for record in rows
        ]
    if subtype == "letter":
        queryset = models.LetterSend.objects.all()
        if filters.get("sender"):
            queryset = queryset.filter(sender_id=str(filters["sender"]))
        if filters.get("recipient"):
            queryset = queryset.filter(recipient_id=str(filters["recipient"]))
        if filters.get("status"):
            queryset = queryset.filter(letterstate__status=str(filters["status"]))
        rows = queryset.order_by("-due_tick", "-id")
        letters = list(rows)
        states = {
            state.letter_id: state
            for state in models.LetterState.objects.filter(
                letter_id__in=[record.pk for record in letters]
            )
        }
        items = []
        for record in letters:
            state = states.get(record.pk)
            items.append(
                _item(
                    "letter",
                    record.source_id,
                    record.recipient_id,
                    [
                        row("寄件人", record.sender_id, mono=True),
                        row("收件人", record.recipient_id, mono=True),
                        row("狀態", getattr(state, "status", "—")),
                        row("到期 tick", record.due_tick, mono=True),
                    ],
                )
            )
        return items
    if subtype == "dream":
        queryset = models.DreamSession.objects.all()
        if owner:
            queryset = queryset.filter(owner_id=str(owner))
        if filters.get("state"):
            queryset = queryset.filter(state=str(filters["state"]))
        return [
            _item(
                "dream",
                record.session_id,
                record.owner_id,
                [
                    row("擁有者", record.owner_id, mono=True),
                    row("狀態", record.state),
                    row("完成次數", record.completed_exchanges, mono=True),
                    row("結果", record.outcome or "—"),
                ],
            )
            for record in queryset.order_by("-created_tick", "-id")
        ]
    if subtype == "decision":
        queryset = models.StoryDirectorDecision.objects.all()
        if owner:
            queryset = queryset.filter(owner_id=str(owner))
        if filters.get("outcome"):
            queryset = queryset.filter(outcome=str(filters["outcome"]))
        if filters.get("thread"):
            queryset = queryset.filter(thread_id=str(filters["thread"]))
        return [
            _item(
                "decision",
                record.decision_id,
                record.source_ref,
                [
                    row("擁有者", record.owner_id, mono=True),
                    row("來源", f"{record.source_kind}:{record.source_ref}", mono=True),
                    row("結果", record.outcome),
                    row("已排程", "是" if record.scheduled else "否"),
                ],
            )
            for record in queryset.order_by("-created_tick", "-id")
        ]
    if subtype == "beat":
        queryset = models.ScheduledBeat.objects.all()
        if owner:
            queryset = queryset.filter(owner_id=str(owner))
        if filters.get("kind"):
            queryset = queryset.filter(kind=str(filters["kind"]))
        if filters.get("thread"):
            queryset = queryset.filter(thread__thread_id=str(filters["thread"]))
        return [
            _item(
                "beat",
                record.beat_id,
                record.effect,
                [
                    row("種類", record.kind, mono=True),
                    row("效果", record.effect, mono=True),
                    row("擁有者", record.owner_id, mono=True),
                    row("執行參照", record.execution_ref or "—", mono=True),
                ],
            )
            for record in queryset.order_by("-created_tick", "-id")
        ]
    if subtype == "draft":
        queryset = models.AuthoringDraft.objects.all()
        if owner:
            queryset = queryset.filter(owner_id=str(owner))
        return [
            _item(
                "draft",
                record.draft_id,
                record.owner_id,
                [
                    row("擁有者", record.owner_id, mono=True),
                    row("修訂", record.revision, mono=True),
                    row(
                        "已確認版本",
                        record.confirmed_revision if record.confirmed_revision is not None else "—",
                        mono=True,
                    ),
                    row("建立 tick", record.created_tick, mono=True),
                ],
            )
            for record in queryset.order_by("-created_tick", "-id")
        ]
    if subtype == "request":
        queryset = models.CreativeRequest.objects.all()
        if owner:
            queryset = queryset.filter(owner_id=str(owner))
        if filters.get("status"):
            queryset = queryset.filter(validation_status=str(filters["status"]))
        return [
            _item(
                "request",
                record.submission_key,
                record.owner_id,
                [
                    row("擁有者", record.owner_id, mono=True),
                    row("版本", record.version, mono=True),
                    row("驗證", record.validation_status),
                    row("提交 tick", record.submitted_tick, mono=True),
                ],
            )
            for record in queryset.order_by("-submitted_tick", "-id")
        ]
    from web.gm.readers.errors import InvalidFilter

    raise InvalidFilter(f"不支援的敘事子類型：{subtype}。")


def _item(subtype: str, identity: Any, label: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": f"{subtype}:{identity}",
        "kind": KIND,
        "dbref": None,
        "label": str(label or identity),
        "subtype": subtype,
        "fields": fields,
    }


# --- details ----------------------------------------------------------------


def detail(subtype: str, identity: str) -> dict[str, Any]:
    from web.gm.readers.errors import InvalidFilter, ObjectNotFound

    builders = {
        "event": _event_detail,
        "thread": _thread_detail,
        "letter": _letter_detail,
        "dream": _dream_detail,
        "decision": _decision_detail,
        "beat": _beat_detail,
        "draft": _draft_detail,
        "request": _request_detail,
    }
    build = builders.get(subtype)
    if build is None:
        raise InvalidFilter(f"不支援的敘事子類型：{subtype}。")
    payload = build(identity)
    if payload is None:
        raise ObjectNotFound()
    return payload


def _envelope(subtype: str, identity: str, label: str, sections: list[dict[str, Any]], raw: Any) -> dict[str, Any]:
    return {
        "id": f"{subtype}:{identity}",
        "kind": KIND,
        "label": label,
        "dbref": None,
        "typeclass": "",
        "subtype": subtype,
        "sections": sections,
        "raw": {"record": json_value(raw)},
    }


def _event_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import NarrativeEvent

    record = NarrativeEvent.objects.filter(source_id=identity).first()
    if record is None:
        return None
    sections = compute_sections(
        [
            (
                "identity",
                "事件",
                lambda: ledger(
                    [
                        row("來源識別", record.source_id, mono=True),
                        row("事件類型", record.event_type, mono=True),
                        row("tick", record.tick, mono=True),
                        row("可見性", record.visibility),
                        row("地點", record.location or "—"),
                        row("顯著度", record.salience, mono=True),
                        row("建立時間", json_value(record.created_at), mono=True),
                    ]
                ),
            ),
            (
                "participants",
                "參與者",
                lambda: list_summary([str(item) for item in (record.participants or [])])
                if record.participants
                else empty("此事件沒有記錄參與者。"),
            ),
            ("content", "內容", lambda: tree(json_value(record.content))),
        ]
    )
    return _envelope("event", record.source_id, record.event_type, sections, _event_raw(record))


def _event_raw(record: Any) -> dict[str, Any]:
    return {
        "source_id": record.source_id,
        "event_type": record.event_type,
        "tick": record.tick,
        "visibility": record.visibility,
        "location": record.location,
        "salience": record.salience,
        "participants": record.participants,
        "content": record.content,
    }


def _thread_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import StoryThread

    record = StoryThread.objects.filter(thread_id=identity).first()
    if record is None:
        return None

    def links() -> dict[str, Any]:
        rows = [
            table_row(
                {
                    "source": _identity_cell(entry.source_kind, entry.source_ref),
                    "kind": cell(entry.source_kind, mono=True),
                    "relation": cell(entry.relation, mono=True),
                    "tick": cell(entry.created_tick, mono=True),
                },
                key=str(entry.pk),
            )
            for entry in record.links.all().order_by("id")
        ]
        return table(
            [
                column("source", "來源", mono=True),
                column("kind", "種類", mono=True),
                column("relation", "關係", mono=True),
                column("tick", "tick", mono=True),
            ],
            rows,
            empty_note="此故事線沒有連結來源。",
        )

    def revisions() -> dict[str, Any]:
        rows = [
            table_row(
                {
                    "revision": cell(entry.revision_number, mono=True),
                    "operation": cell(entry.operation, mono=True),
                    "state": cell(entry.state, mono=True),
                    "tick": cell(json_value(entry.created_at), mono=True),
                },
                key=str(entry.pk),
            )
            for entry in record.revisions.all().order_by("revision_number", "id")
        ]
        return table(
            [
                column("revision", "修訂", mono=True),
                column("operation", "操作", mono=True),
                column("state", "狀態", mono=True),
                column("tick", "建立時間", mono=True),
            ],
            rows,
            empty_note="此故事線沒有修訂紀錄。",
        )

    sections = compute_sections(
        [
            (
                "identity",
                "故事線",
                lambda: ledger(
                    [
                        row("識別碼", record.thread_id, mono=True),
                        row("來源", record.origin or "—"),
                        row("狀態", record.state),
                        row("修訂", record.revision, mono=True),
                        row("建立 tick", record.created_tick, mono=True),
                    ]
                ),
            ),
            (
                "summary",
                "事實摘要",
                lambda: text(record.factual_summary) if record.factual_summary else empty("此故事線沒有事實摘要。"),
            ),
            (
                "commitments",
                "承諾與待解問題",
                lambda: groups(
                    [
                        group("待解問題", [row(str(index), str(item)) for index, item in enumerate(record.unresolved_questions or [])], key="questions"),
                        group("擬定計畫", [row(str(index), str(item)) for index, item in enumerate(record.proposed_plans or [])], key="plans"),
                        group("既有承諾", [row(str(index), str(item)) for index, item in enumerate(record.commitments or [])], key="commitments"),
                    ]
                )
                if (record.unresolved_questions or record.proposed_plans or record.commitments)
                else empty("此故事線沒有承諾或待解問題。"),
            ),
            ("links", "連結來源", links),
            ("revisions", "修訂歷史", revisions),
            (
                "participants",
                "參與者與可見範圍",
                lambda: groups(
                    [
                        group("參與者", [row(str(index), str(item)) for index, item in enumerate(record.participants or [])], key="participants"),
                        group("可見對象", [row(str(index), str(item)) for index, item in enumerate(record.visible_to or [])], key="visible"),
                        group("記憶參照", [row(str(index), str(item)) for index, item in enumerate(record.memory_references or [])], key="memory"),
                    ]
                ),
            ),
        ]
    )
    return _envelope("thread", record.thread_id, record.origin or record.thread_id, sections, _thread_raw(record))


def _thread_raw(record: Any) -> dict[str, Any]:
    return {
        "thread_id": record.thread_id,
        "origin": record.origin,
        "state": record.state,
        "revision": record.revision,
        "created_tick": record.created_tick,
        "participants": record.participants,
        "visible_to": record.visible_to,
        "factual_summary": record.factual_summary,
        "unresolved_questions": record.unresolved_questions,
        "proposed_plans": record.proposed_plans,
        "commitments": record.commitments,
        "memory_references": record.memory_references,
        "development_ticks": record.development_ticks,
    }


def _letter_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import LetterReplyWork, LetterSend, LetterState

    record = LetterSend.objects.filter(source_id=identity).select_related("state").first()
    if record is None:
        return None
    state = LetterState.objects.filter(letter=record).first()
    work = LetterReplyWork.objects.filter(letter=record).first()

    def state_section() -> dict[str, Any]:
        if state is None:
            return empty("此書信沒有投遞狀態紀錄。")
        return ledger(
            [
                row("狀態", state.status),
                row("到期 tick", state.due_tick, mono=True),
                row("轉換識別", state.transition_id or "—", mono=True),
                row("領取 tick", state.collection_tick if state.collection_tick is not None else "—", mono=True),
                row("閱讀 tick", state.read_tick if state.read_tick is not None else "—", mono=True),
            ]
        )

    def work_section() -> dict[str, Any]:
        if work is None:
            return empty("此書信沒有回信工作。")
        return ledger(
            [
                row("狀態", work.status),
                row("快照", work.snapshot_id or "—", mono=True),
                row("回信來源", work.outgoing_source_id or "—", mono=True),
            ]
        )

    sections = compute_sections(
        [
            (
                "identity",
                "書信",
                lambda: ledger(
                    [
                        row("來源識別", record.source_id, mono=True),
                        row("寄件人", record.sender_id, mono=True),
                        row("收件人", record.recipient_id, mono=True),
                        row("收件人類型", record.recipient_kind, mono=True),
                        row("寄出 tick", record.sent_tick, mono=True),
                        row("到期 tick", record.due_tick, mono=True),
                        row(
                            "回覆對象",
                            record.reply_to or "—",
                            mono=True,
                            link_to=source_link("letter", record.reply_to) if record.reply_to else None,
                        ),
                        row("情境快照", record.source_snapshot_id or "—", mono=True),
                    ]
                ),
            ),
            ("state", "投遞狀態", state_section),
            ("reply_work", "回信工作", work_section),
            ("body", "信件內容", lambda: text(record.body) if record.body else empty("此書信沒有內容。")),
        ]
    )
    return _envelope("letter", record.source_id, record.recipient_id, sections, _letter_raw(record, state, work))


def _letter_raw(record: Any, state: Any, work: Any) -> dict[str, Any]:
    return {
        "letter": {
            "source_id": record.source_id,
            "sender_id": record.sender_id,
            "recipient_id": record.recipient_id,
            "recipient_kind": record.recipient_kind,
            "sent_tick": record.sent_tick,
            "due_tick": record.due_tick,
            "reply_to": record.reply_to,
            "source_snapshot_id": record.source_snapshot_id,
        },
        "state": None
        if state is None
        else {
            "status": state.status,
            "due_tick": state.due_tick,
            "transition_id": state.transition_id,
            "collection_tick": state.collection_tick,
            "read_tick": state.read_tick,
        },
        "reply_work": None
        if work is None
        else {
            "status": work.status,
            "snapshot_id": work.snapshot_id,
            "outgoing_source_id": work.outgoing_source_id,
        },
    }


def _dream_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import DreamSession

    record = DreamSession.objects.filter(session_id=identity).first()
    if record is None:
        return None

    def exchanges() -> dict[str, Any]:
        rows = [
            table_row(
                {
                    "number": cell(entry.exchange_number, mono=True),
                    "submission": cell(entry.submission_id, mono=True),
                    "response": cell(entry.response_ref or "—", mono=True),
                    "tick": cell(entry.tick, mono=True),
                },
                key=str(entry.pk),
            )
            for entry in record.exchanges.all().order_by("exchange_number", "id")
        ]
        return table(
            [
                column("number", "次序", mono=True),
                column("submission", "提交識別", mono=True),
                column("response", "回應參照", mono=True),
                column("tick", "tick", mono=True),
            ],
            rows,
            empty_note="此夢境工作階段沒有已交付的交換。",
        )

    sections = compute_sections(
        [
            (
                "identity",
                "夢境工作階段",
                lambda: ledger(
                    [
                        row("工作階段", record.session_id, mono=True),
                        row("擁有者", record.owner_id, mono=True),
                        row("狀態", record.state),
                        row("結果", record.outcome or "—"),
                        row("完成次數", record.completed_exchanges, mono=True),
                        row("修訂", record.revision, mono=True),
                        row("建立 tick", record.created_tick, mono=True),
                    ]
                ),
            ),
            (
                "pending",
                "進行中的提交",
                lambda: ledger(
                    [
                        row("提交識別", record.pending_submission_id or "—", mono=True),
                        row("暫存輸入", record.saved_input or "—"),
                        row("草稿", record.draft_id or "—", mono=True),
                        row("請求鍵", record.request_key or "—", mono=True),
                    ]
                ),
            ),
            ("exchanges", "交換紀錄", exchanges),
        ]
    )
    return _envelope("dream", record.session_id, record.owner_id, sections, _dream_raw(record))


def _dream_raw(record: Any) -> dict[str, Any]:
    return {
        "session_id": record.session_id,
        "owner_id": record.owner_id,
        "state": record.state,
        "outcome": record.outcome,
        "completed_exchanges": record.completed_exchanges,
        "revision": record.revision,
        "created_tick": record.created_tick,
        "pending_submission_id": record.pending_submission_id,
        "draft_id": record.draft_id,
        "request_key": record.request_key,
    }


def _decision_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import StoryDirectorDecision

    record = StoryDirectorDecision.objects.filter(decision_id=identity).first()
    if record is None:
        return None
    sections = compute_sections(
        [
            (
                "identity",
                "導演決策",
                lambda: ledger(
                    [
                        row("決策識別", record.decision_id, mono=True),
                        row("擁有者", record.owner_id, mono=True),
                        row("來源", f"{record.source_kind}:{record.source_ref}", mono=True),
                        row("來源修訂", record.source_revision, mono=True),
                        row("結果", record.outcome),
                        row("已排程", "是" if record.scheduled else "否"),
                        row("建立 tick", record.created_tick, mono=True),
                    ]
                ),
            ),
            (
                "links",
                "相關紀錄",
                lambda: groups(
                    [
                        group(
                            "故事線",
                            [
                                row(
                                    record.thread_id or "—",
                                    f"修訂 {record.thread_revision}",
                                    mono=True,
                                    link_to=source_link("thread", record.thread_id) if record.thread_id else None,
                                )
                            ],
                            key="thread",
                        ),
                        group(
                            "情境快照",
                            [row(record.snapshot_id or "—", "快照", mono=True)],
                            key="snapshot",
                        ),
                    ]
                ),
            ),
        ]
    )
    return _envelope("decision", record.decision_id, record.outcome, sections, _decision_raw(record))


def _decision_raw(record: Any) -> dict[str, Any]:
    return {
        "decision_id": record.decision_id,
        "owner_id": record.owner_id,
        "source_kind": record.source_kind,
        "source_ref": record.source_ref,
        "source_revision": record.source_revision,
        "thread_id": record.thread_id,
        "thread_revision": record.thread_revision,
        "outcome": record.outcome,
        "scheduled": record.scheduled,
        "snapshot_id": record.snapshot_id,
        "created_tick": record.created_tick,
    }


def _beat_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import ScheduledBeat

    record = ScheduledBeat.objects.filter(beat_id=identity).select_related("thread").first()
    if record is None:
        return None
    sections = compute_sections(
        [
            (
                "identity",
                "排程節拍",
                lambda: ledger(
                    [
                        row("節拍識別", record.beat_id, mono=True),
                        row("決策", record.decision_id, mono=True),
                        row("擁有者", record.owner_id, mono=True),
                        row("種類", record.kind, mono=True),
                        row("效果", record.effect, mono=True),
                        row("安排修訂", record.arrangement_revision, mono=True),
                        row("執行參照", record.execution_ref or "—", mono=True),
                        row("建立 tick", record.created_tick, mono=True),
                    ]
                ),
            ),
            (
                "thread",
                "所屬故事線",
                lambda: ledger(
                    [
                        row(
                            record.thread.thread_id,
                            record.thread.origin or "—",
                            mono=True,
                            link_to=source_link("thread", record.thread.thread_id),
                        )
                    ]
                ),
            ),
            ("payload", "節拍內容", lambda: tree(json_value(record.payload))),
        ]
    )
    return _envelope("beat", record.beat_id, record.effect, sections, _beat_raw(record))


def _beat_raw(record: Any) -> dict[str, Any]:
    return {
        "beat_id": record.beat_id,
        "decision_id": record.decision_id,
        "owner_id": record.owner_id,
        "thread_id": record.thread.thread_id if record.thread is not None else "",
        "kind": record.kind,
        "effect": record.effect,
        "arrangement_revision": record.arrangement_revision,
        "execution_ref": record.execution_ref,
        "created_tick": record.created_tick,
        "payload": record.payload,
    }


def _draft_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import AuthoringDraft

    record = AuthoringDraft.objects.filter(draft_id=identity).first()
    if record is None:
        return None

    def requests() -> dict[str, Any]:
        rows = [
            table_row(
                {
                    "submission": cell(
                        entry.submission_key,
                        mono=True,
                        link=source_link("request", entry.submission_key),
                    ),
                    "version": cell(entry.version, mono=True),
                    "validation": cell(entry.validation_status),
                },
                key=str(entry.pk),
            )
            for entry in record.requests.all().order_by("version", "id")
        ]
        return table(
            [
                column("submission", "提交識別", mono=True),
                column("version", "版本", mono=True),
                column("validation", "驗證"),
            ],
            rows,
            empty_note="此草稿沒有已確認的請求。",
        )

    sections = compute_sections(
        [
            (
                "identity",
                "創作草稿",
                lambda: ledger(
                    [
                        row("草稿識別", record.draft_id, mono=True),
                        row("擁有者", record.owner_id, mono=True),
                        row("修訂", record.revision, mono=True),
                        row(
                            "已確認版本",
                            record.confirmed_revision if record.confirmed_revision is not None else "—",
                            mono=True,
                        ),
                        row("建立 tick", record.created_tick, mono=True),
                    ]
                ),
            ),
            ("direction", "創作方向", lambda: tree(json_value(record.direction))),
            (
                "sources",
                "來源",
                lambda: table(
                    [column("kind", "種類", mono=True), column("ref", "參照", mono=True)],
                    [
                        table_row(
                            {
                                "kind": cell(entry.get("kind", "—"), mono=True),
                                "ref": cell(entry.get("ref", "—"), mono=True),
                            },
                            key=str(index),
                        )
                        for index, entry in enumerate(record.sources or [])
                        if isinstance(entry, dict)
                    ],
                    empty_note="此草稿沒有來源。",
                ),
            ),
            ("requests", "確認請求", requests),
        ]
    )
    return _envelope("draft", record.draft_id, record.owner_id, sections, _draft_raw(record))


def _draft_raw(record: Any) -> dict[str, Any]:
    return {
        "draft_id": record.draft_id,
        "owner_id": record.owner_id,
        "revision": record.revision,
        "confirmed_revision": record.confirmed_revision,
        "created_tick": record.created_tick,
        "direction": record.direction,
        "sources": record.sources,
    }


def _request_detail(identity: str) -> dict[str, Any] | None:
    from world.narrative.models import CreativeRequest

    record = CreativeRequest.objects.filter(submission_key=identity).select_related("draft").first()
    if record is None:
        return None
    sections = compute_sections(
        [
            (
                "identity",
                "創作請求",
                lambda: ledger(
                    [
                        row("提交識別", record.submission_key, mono=True),
                        row("擁有者", record.owner_id, mono=True),
                        row("版本", record.version, mono=True),
                        row("驗證", record.validation_status),
                        row("提交 tick", record.submitted_tick, mono=True),
                    ]
                ),
            ),
            (
                "draft",
                "來源草稿",
                lambda: ledger(
                    [
                        row(
                            record.draft.draft_id,
                            f"修訂 {record.draft.revision}",
                            mono=True,
                            link_to=source_link("draft", record.draft.draft_id),
                        )
                    ]
                ),
            ),
            ("direction", "創作方向", lambda: tree(json_value(record.direction))),
            (
                "sources",
                "來源",
                lambda: table(
                    [column("kind", "種類", mono=True), column("ref", "參照", mono=True)],
                    [
                        table_row(
                            {
                                "kind": cell(entry.get("kind", "—"), mono=True),
                                "ref": cell(entry.get("ref", "—"), mono=True),
                            },
                            key=str(index),
                        )
                        for index, entry in enumerate(record.sources or [])
                        if isinstance(entry, dict)
                    ],
                    empty_note="此請求沒有來源。",
                ),
            ),
        ]
    )
    return _envelope("request", record.submission_key, record.owner_id, sections, _request_raw(record))


def _request_raw(record: Any) -> dict[str, Any]:
    return {
        "submission_key": record.submission_key,
        "draft_id": record.draft.draft_id if record.draft is not None else "",
        "owner_id": record.owner_id,
        "version": record.version,
        "validation_status": record.validation_status,
        "submitted_tick": record.submitted_tick,
        "direction": record.direction,
        "sources": record.sources,
    }


__all__ = [
    "KIND",
    "SUBTYPES",
    "SUBTYPE_LABELS",
    "detail",
    "list_items",
    "source_link",
    "split_identity",
]
