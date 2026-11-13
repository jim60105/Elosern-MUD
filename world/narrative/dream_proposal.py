"""Apply edit commands to a dream proposal, purely.

Implements the edit contract of the dream proposal co-editing design
(`docs/superpowers/specs/2026-11-13-dream-proposal-coediting-design.md`,
"Edit Contract"): one proposal plus an ordered edit set in, the edited
proposal plus its change report, or one concrete error, out. The module is
pure - no database, no session, no Evennia, no logging - so every later stage
depends on one tested contract.

A proposal is a plain dict with `summary: str`, the five tag lists as
`list[str]` and `requirements: list[dict]` whose rows are exactly
`{"kind": str, "text": str}`. Each field is edited as text: one tag item or one
requirement row per line, a requirement row written `kind: text`.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
import json
from typing import Any

LIST_FIELDS = ("themes", "atmosphere", "participants", "emphasis", "exclusions")
PATHS = ("summary", *LIST_FIELDS, "requirements")
COMMANDS = ("str_replace", "insert", "create")
REQUIREMENT_KINDS = ("place", "new_character", "private_commission")
MAX_SUMMARY_CHARACTERS = 2000
MAX_LIST_ITEMS = 32
MAX_ITEM_CHARACTERS = 200
MAX_REQUIREMENTS = 8
MAX_REQUIREMENT_TEXT = 200
MAX_EDITS = 16
# The largest legal field text: 32 items of 200 characters plus separators.
MAX_EDIT_TEXT_CHARACTERS = 6500
# Aggregate budgets on the canonical JSON, so the proposal and its change
# report fit the draft store and the panel envelope that carry them. The
# report budget is 7,680 (not 8,192) because the schema-4 dream panel
# publishes the report beside the proposal AND repeats the proposal's summary
# and requirement rows in its projection keys: with both aggregates at their
# former ceilings that payload is 239 bytes over the 65,536-byte envelope, so
# the report half reserves one bounded list item's worth of room. The envelope
# test in web/webclient/presentation/tests/test_dream_artwork.py pins it.
MAX_PROPOSAL_BYTES = 16384
MAX_CHANGES_BYTES = 7680

ERROR_CODES = (
    "malformed_proposal",
    "malformed_edit",
    "too_many_edits",
    "unknown_command",
    "unknown_path",
    "no_match",
    "multiple_matches",
    "insert_out_of_range",
    "malformed_requirement",
    "summary_too_long",
    "too_many_items",
    "item_too_long",
    "too_many_requirements",
    "requirement_too_long",
    "proposal_too_large",
    "changes_too_large",
)

_REQUIREMENT_KEYS = frozenset({"kind", "text"})
_EDIT_KEYS = {
    "str_replace": frozenset({"command", "path", "old_str", "new_str"}),
    "insert": frozenset({"command", "path", "insert_line", "insert_text"}),
    "create": frozenset({"command", "path", "file_text"}),
}
_REQUIREMENT_COLONS = (":", "：")


class ProposalEditError(ValueError):
    """One refused edit set: a stable code and the failing edit's position."""

    def __init__(self, code: str, index: int | None = None):
        self.code = code
        self.index = index
        super().__init__(f"{code} at edit {index}" if index is not None else code)


def empty_proposal() -> dict:
    """Return the canonical empty proposal."""
    proposal: dict[str, Any] = {"summary": ""}
    proposal.update({field: [] for field in LIST_FIELDS})
    proposal["requirements"] = []
    return proposal


def normalize_proposal(value: Any) -> dict:
    """Return a canonical detached copy of `value`, or raise its first defect."""
    if not isinstance(value, Mapping):
        raise ProposalEditError("malformed_proposal")
    normalized = empty_proposal()
    summary = value.get("summary", "")
    if not isinstance(summary, str):
        raise ProposalEditError("malformed_proposal")
    normalized["summary"] = summary.strip()
    if len(normalized["summary"]) > MAX_SUMMARY_CHARACTERS:
        raise ProposalEditError("summary_too_long")
    for field in LIST_FIELDS:
        normalized[field] = _typed_items(value.get(field, []))
    normalized["requirements"] = _typed_requirements(value.get("requirements", []))
    _check_proposal_bytes(normalized)
    return normalized


def is_empty(proposal: Any) -> bool:
    """True when the proposal holds no summary and no collection entry."""
    normalized = normalize_proposal(proposal)
    return not any(normalized[path] for path in PATHS)


def field_text(proposal: Any, path: str) -> str:
    """Render one field as the text an edit command operates on."""
    if path not in PATHS:
        raise ProposalEditError("unknown_path")
    return _render(normalize_proposal(proposal), path)


def numbered_lines(proposal: Any, path: str) -> list[dict]:
    """Render one field as one entry per line, numbered from 1."""
    text = field_text(proposal, path)
    if not text:
        return []
    return [
        {"line": number, "text": line}
        for number, line in enumerate(text.split("\n"), start=1)
    ]


def apply_edits(proposal: Any, edits: Any) -> dict:
    """Apply `edits` in order to a copy of `proposal`, all or nothing."""
    if not isinstance(edits, (list, tuple)):
        raise ProposalEditError("malformed_edit")
    if len(edits) > MAX_EDITS:
        raise ProposalEditError("too_many_edits")
    before = normalize_proposal(proposal)
    working = copy.deepcopy(before)
    for index, edit in enumerate(edits):
        try:
            _apply_one(working, edit)
        except ProposalEditError as error:
            raise ProposalEditError(error.code, index) from None
    if _canonical_bytes(_report(before, working)) > MAX_CHANGES_BYTES:
        raise ProposalEditError("changes_too_large")
    return working


def diff(before: Any, after: Any) -> dict:
    """Return the change report from `before` to `after`."""
    return _report(normalize_proposal(before), normalize_proposal(after))


def _render(proposal: Mapping[str, Any], path: str) -> str:
    if path == "summary":
        return proposal["summary"]
    if path == "requirements":
        return "\n".join(
            f"{row['kind']}: {row['text']}" for row in proposal["requirements"]
        )
    return "\n".join(proposal[path])


def _normalize_items(raw: list[str]) -> list[str]:
    items: list[str] = []
    for entry in raw:
        item = entry.strip()
        if not item or item in items:
            continue
        if len(item) > MAX_ITEM_CHARACTERS:
            raise ProposalEditError("item_too_long")
        items.append(item)
    if len(items) > MAX_LIST_ITEMS:
        raise ProposalEditError("too_many_items")
    return items


def _typed_items(raw: Any) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(entry, str) for entry in raw):
        raise ProposalEditError("malformed_proposal")
    return _normalize_items(raw)


def _append_requirement(rows: list[dict[str, str]], kind: str, text: str) -> None:
    clean = text.strip()
    if len(clean) > MAX_REQUIREMENT_TEXT:
        raise ProposalEditError("requirement_too_long")
    row = {"kind": kind, "text": clean}
    if row not in rows:
        rows.append(row)


def _typed_requirements(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        raise ProposalEditError("malformed_proposal")
    rows: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, Mapping) or set(entry.keys()) != _REQUIREMENT_KEYS:
            raise ProposalEditError("malformed_proposal")
        kind = entry["kind"]
        text = entry["text"]
        if not isinstance(kind, str) or not isinstance(text, str):
            raise ProposalEditError("malformed_proposal")
        if kind not in REQUIREMENT_KINDS or not text.strip():
            raise ProposalEditError("malformed_proposal")
        _append_requirement(rows, kind, text)
    if len(rows) > MAX_REQUIREMENTS:
        raise ProposalEditError("too_many_requirements")
    return rows


def _split_requirement_line(line: str) -> tuple[str, str]:
    """Split one `kind: text` line at its first colon of either width."""
    found = [
        position
        for position in (line.find(colon) for colon in _REQUIREMENT_COLONS)
        if position >= 0
    ]
    if not found:
        raise ProposalEditError("malformed_requirement")
    at = min(found)
    kind = line[:at].strip()
    text = line[at + 1 :].strip()
    if kind not in REQUIREMENT_KINDS or not text:
        raise ProposalEditError("malformed_requirement")
    return kind, text


def _requirement_rows_from_text(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        kind, requirement_text = _split_requirement_line(line)
        _append_requirement(rows, kind, requirement_text)
    if len(rows) > MAX_REQUIREMENTS:
        raise ProposalEditError("too_many_requirements")
    return rows


def _store_field(proposal: dict, path: str, text: str) -> None:
    if path == "summary":
        summary = text.strip()
        if len(summary) > MAX_SUMMARY_CHARACTERS:
            raise ProposalEditError("summary_too_long")
        proposal["summary"] = summary
    elif path == "requirements":
        proposal["requirements"] = _requirement_rows_from_text(text)
    else:
        proposal[path] = _normalize_items(text.split("\n"))
    _check_proposal_bytes(proposal)


def _check_proposal_bytes(proposal: dict) -> None:
    if _canonical_bytes(proposal) > MAX_PROPOSAL_BYTES:
        raise ProposalEditError("proposal_too_large")


def _canonical_bytes(value: Any) -> int:
    serialized = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return len(serialized.encode("utf-8"))


def _require_edit_text(value: Any) -> None:
    if not isinstance(value, str) or len(value) > MAX_EDIT_TEXT_CHARACTERS:
        raise ProposalEditError("malformed_edit")


def _apply_one(proposal: dict, edit: Any) -> None:
    if not isinstance(edit, Mapping):
        raise ProposalEditError("malformed_edit")
    command = edit.get("command")
    if not isinstance(command, str) or command not in COMMANDS:
        raise ProposalEditError("unknown_command")
    path = edit.get("path")
    if not isinstance(path, str) or path not in PATHS:
        raise ProposalEditError("unknown_path")
    if set(edit.keys()) != _EDIT_KEYS[command]:
        raise ProposalEditError("malformed_edit")
    text = _render(proposal, path)
    if command == "create":
        file_text = edit["file_text"]
        _require_edit_text(file_text)
        text = file_text
    elif command == "str_replace":
        old_str = edit["old_str"]
        new_str = edit["new_str"]
        _require_edit_text(old_str)
        _require_edit_text(new_str)
        if not old_str:
            raise ProposalEditError("malformed_edit")
        matches = text.count(old_str)
        if matches == 0:
            raise ProposalEditError("no_match")
        if matches > 1:
            raise ProposalEditError("multiple_matches")
        text = text.replace(old_str, new_str, 1)
    else:
        insert_line = edit["insert_line"]
        insert_text = edit["insert_text"]
        if isinstance(insert_line, bool) or not isinstance(insert_line, int):
            raise ProposalEditError("malformed_edit")
        _require_edit_text(insert_text)
        lines = text.split("\n") if text else []
        if not 0 <= insert_line <= len(lines):
            raise ProposalEditError("insert_out_of_range")
        lines.insert(insert_line, insert_text)
        text = "\n".join(lines)
    _store_field(proposal, path, text)


def _report(before: dict, after: dict) -> dict:
    if before["summary"] == after["summary"]:
        summary = None
    elif not before["summary"] and after["summary"]:
        summary = "formed"
    else:
        summary = "changed"
    lists = {
        field: {
            "added": [item for item in after[field] if item not in before[field]],
            "removed": [item for item in before[field] if item not in after[field]],
        }
        for field in LIST_FIELDS
    }
    return {
        "summary": summary,
        "lists": lists,
        "requirements": {
            "added": [
                dict(row)
                for row in after["requirements"]
                if row not in before["requirements"]
            ],
            "removed": [
                dict(row)
                for row in before["requirements"]
                if row not in after["requirements"]
            ],
        },
    }
