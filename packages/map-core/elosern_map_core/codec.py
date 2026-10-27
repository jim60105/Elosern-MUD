"""Restricted, comment-preserving YAML parsing and serialization.

Only data-only YAML 1.2 documents are accepted. The parser rejects, before a
writable authoring model exists:

* duplicate keys (detected on the event stream, before mappings are built),
* custom or explicit tags, anchors, aliases and merge keys,
* timestamps, non-finite numbers and non-decimal integer literals,
* unsupported scalar/object types (sets, binary, byte strings),
* multiple documents, empty documents and non-string mapping keys,
* documents beyond the size, depth and collection bounds.

The round-trip tree keeps comments and scalar styles next to the typed values.
Serialization validates the candidate first, merges it into a copy of the
retained tree (so comments attached to retained stable-ID objects survive),
dumps readable literal blocks for multiline strings, and re-parses its own
output. A candidate that would be lossy or unsupported never produces text.
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time
from io import StringIO
from typing import Any, Mapping

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq, TaggedScalar
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import (
    AliasEvent,
    DocumentStartEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)
from ruamel.yaml.scalarstring import LiteralScalarString
from . import schema as schema_module
from .diagnostics import (
    STRUCTURE,
    AuthoringError,
    Diagnostic,
    SourceLocation,
    sorted_diagnostics,
)
from .schema import (
    MAX_COLLECTION_ITEMS,
    MAX_DOCUMENT_BYTES,
    MAX_DOCUMENT_DEPTH,
)
from .sources import expected_document, fingerprint_text

_REJECTED_SCALAR_TYPES = (bytes, bytearray, set, frozenset)


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """One parsed source: typed document, field provenance and retained tree."""

    relative_path: str
    kind: str
    identity: str
    version: int
    document: Any
    provenance: Mapping[str, SourceLocation]
    round_trip: CommentedMap


def _yaml_loader() -> YAML:
    loader = YAML(typ="rt", pure=True)
    loader.version = (1, 2)
    loader.allow_duplicate_keys = False
    return loader


def _yaml_dumper() -> YAML:
    # ruamel's round-trip dumper defaults to YAML 1.2 and emits no version
    # directive, so the output stays a plain readable document.
    dumper = YAML(typ="rt", pure=True)
    dumper.allow_duplicate_keys = False
    return dumper


def _single(diagnostic: Diagnostic) -> AuthoringError:
    return AuthoringError((diagnostic,))


def _structure(
    code: str,
    message: str,
    *,
    relative_path: str,
    field_path: str = "",
    line: int | None = None,
    column: int | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        category=STRUCTURE,
        message=message,
        relative_path=relative_path,
        field_path=field_path,
        line=line,
        column=column,
    )


def _reject_number_literal(
    event: ScalarEvent,
    relative_path: str,
) -> None:
    if event.style is not None:
        return
    value = event.value
    if not isinstance(value, str):
        return
    stripped = value.strip()
    if re.match(r"^[+-]?0[xXoObB]", stripped) or (
        re.match(r"^[+-]?\d[\d_]*$", stripped) and "_" in stripped
    ) or re.match(r"^[+-]?0\d+$", stripped):
        raise _single(
            _structure(
                "invalid_number_literal",
                f"{value!r} is not a supported decimal integer literal",
                relative_path=relative_path,
                line=event.start_mark.line + 1,
                column=event.start_mark.column + 1,
            )
        )


def _scan_events(text: str, relative_path: str) -> None:
    """Reject unsafe constructs from the event stream before construction."""

    # stack entries are mapping contexts (dict) or ``None`` for sequences.
    stack: list[dict[str, Any] | None] = []
    documents = 0
    saw_content = False

    def complete_value() -> None:
        if stack and isinstance(stack[-1], dict) and not stack[-1]["expect_key"]:
            stack[-1]["expect_key"] = True

    for event in _yaml_loader().parse(text):
        if isinstance(event, DocumentStartEvent):
            documents += 1
            if documents > 1:
                raise _single(
                    _structure(
                        "multiple_documents",
                        "a map source must contain exactly one YAML document",
                        relative_path=relative_path,
                        line=event.start_mark.line + 1,
                        column=event.start_mark.column + 1,
                    )
                )
            continue
        if len(stack) > MAX_DOCUMENT_DEPTH:
            raise _single(
                _structure(
                    "invalid_document_depth",
                    f"document exceeds {MAX_DOCUMENT_DEPTH} nested values",
                    relative_path=relative_path,
                    line=event.start_mark.line + 1,
                    column=event.start_mark.column + 1,
                )
            )
        if isinstance(event, AliasEvent):
            raise _single(
                _structure(
                    "anchor_or_alias",
                    "YAML aliases are not supported",
                    relative_path=relative_path,
                    line=event.start_mark.line + 1,
                    column=event.start_mark.column + 1,
                )
            )
        anchor = getattr(event, "anchor", None)
        if anchor is not None:
            raise _single(
                _structure(
                    "anchor_or_alias",
                    "YAML anchors are not supported",
                    relative_path=relative_path,
                    line=event.start_mark.line + 1,
                    column=event.start_mark.column + 1,
                )
            )
        tag = getattr(event, "tag", None)
        if tag is not None and tag != "":
            raise _single(
                _structure(
                    "unsupported_tag",
                    f"explicit/custom YAML tags are not supported ({tag})",
                    relative_path=relative_path,
                    line=event.start_mark.line + 1,
                    column=event.start_mark.column + 1,
                )
            )
        if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
            saw_content = True
            if stack and isinstance(stack[-1], dict) and stack[-1]["expect_key"]:
                raise _single(
                    _structure(
                        "unsupported_key",
                        "mapping keys must be plain strings",
                        relative_path=relative_path,
                        line=event.start_mark.line + 1,
                        column=event.start_mark.column + 1,
                    )
                )
            if isinstance(event, MappingStartEvent):
                stack.append({"keys": set(), "expect_key": True})
            else:
                stack.append(None)
        elif isinstance(event, MappingEndEvent):
            if not stack or stack[-1] is None:
                continue
            stack.pop()
            complete_value()
        elif isinstance(event, SequenceEndEvent):
            if stack and stack[-1] is None:
                stack.pop()
            complete_value()
        elif isinstance(event, ScalarEvent):
            saw_content = True
            _reject_number_literal(event, relative_path)
            context = stack[-1] if stack else None
            if isinstance(context, dict) and context["expect_key"]:
                key = event.value
                if key == "<<":
                    raise _single(
                        _structure(
                            "merge_key",
                            "YAML merge keys are not supported",
                            relative_path=relative_path,
                            line=event.start_mark.line + 1,
                            column=event.start_mark.column + 1,
                        )
                    )
                if key in context["keys"]:
                    raise _single(
                        _structure(
                            "duplicate_key",
                            f"duplicate mapping key {key!r}",
                            relative_path=relative_path,
                            field_path=str(key),
                            line=event.start_mark.line + 1,
                            column=event.start_mark.column + 1,
                        )
                    )
                context["keys"].add(key)
                context["expect_key"] = False
            elif isinstance(context, dict):
                complete_value()

    if documents == 0 or not saw_content:
        raise _single(
            _structure(
                "empty_document",
                "the document is empty",
                relative_path=relative_path,
            )
        )


def _check_loaded_value(
    value: Any,
    path: str,
    relative_path: str,
    *,
    depth: int = 0,
    seen: set[int] | None = None,
) -> None:
    if seen is None:
        seen = set()
    if depth > MAX_DOCUMENT_DEPTH:
        raise _single(
            _structure(
                "invalid_document_depth",
                f"{path or '<document>'} exceeds {MAX_DOCUMENT_DEPTH} nested values",
                relative_path=relative_path,
                field_path=path,
            )
        )
    if isinstance(value, TaggedScalar):
        raise _single(
            _structure(
                "unsupported_tag",
                f"{path} is a tagged YAML scalar",
                relative_path=relative_path,
                field_path=path,
            )
        )
    if isinstance(value, (date, datetime, time)):
        raise _single(
            _structure(
                "timestamp_value",
                f"{path} is a YAML timestamp; timestamps are not supported",
                relative_path=relative_path,
                field_path=path,
            )
        )
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise _single(
                _structure(
                    "non_finite_number",
                    f"{path} is a non-finite number",
                    relative_path=relative_path,
                    field_path=path,
                )
            )
        return
    if isinstance(value, _REJECTED_SCALAR_TYPES):
        raise _single(
            _structure(
                "unsupported_scalar",
                f"{path} is a {type(value).__name__}; only scalar strings, "
                "integers, booleans, null, mappings and lists are supported",
                relative_path=relative_path,
                field_path=path,
            )
        )
    if isinstance(value, Mapping):
        marker = id(value)
        if marker in seen:
            raise _single(
                _structure(
                    "cyclic_value",
                    f"{path} is cyclic",
                    relative_path=relative_path,
                    field_path=path,
                )
            )
        seen.add(marker)
        if len(value) > MAX_COLLECTION_ITEMS:
            raise _single(
                _structure(
                    "invalid_collection_size",
                    f"{path} has {len(value)} entries",
                    relative_path=relative_path,
                    field_path=path,
                )
            )
        for key, item in value.items():
            if not isinstance(key, str):
                raise _single(
                    _structure(
                        "unsupported_key",
                        f"{path} has a non-string key {key!r}",
                        relative_path=relative_path,
                        field_path=path,
                    )
                )
            _check_loaded_value(
                item,
                f"{path}.{key}" if path else key,
                relative_path,
                depth=depth + 1,
                seen=seen,
            )
        seen.discard(marker)
        return
    if isinstance(value, (list, tuple)):
        marker = id(value)
        if marker in seen:
            raise _single(
                _structure(
                    "cyclic_value",
                    f"{path} is cyclic",
                    relative_path=relative_path,
                    field_path=path,
                )
            )
        seen.add(marker)
        if len(value) > MAX_COLLECTION_ITEMS:
            raise _single(
                _structure(
                    "invalid_collection_size",
                    f"{path} has {len(value)} entries",
                    relative_path=relative_path,
                    field_path=path,
                )
            )
        for index, item in enumerate(value):
            _check_loaded_value(
                item,
                f"{path}[{index}]",
                relative_path,
                depth=depth + 1,
                seen=seen,
            )
        seen.discard(marker)
        return
    if not isinstance(value, (str, int, bool)) and value is not None:
        raise _single(
            _structure(
                "unsupported_scalar",
                f"{path} has unsupported type {type(value).__name__}",
                relative_path=relative_path,
                field_path=path,
            )
        )


def _plain(value: Any) -> Any:
    """Convert a ruamel round-trip value to plain data for typed validation."""

    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, TaggedScalar):
        return str(value)
    return value


def _thaw(value: Any) -> Any:
    """Copy a deep-frozen typed value back to plain mutable data."""

    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value


def _location(value: Any) -> SourceLocation | None:
    if not isinstance(value, tuple) or len(value) < 2:
        return None
    return SourceLocation(line=value[0] + 1, column=value[1] + 1)


def _provenance(tree: Any) -> dict[str, SourceLocation]:
    locations: dict[str, SourceLocation] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            line_collections = getattr(node, "lc", None)
            for key, item in node.items():
                child = f"{path}.{key}" if path else str(key)
                if line_collections is not None:
                    try:
                        location = _location(line_collections.value(key))
                    except Exception:  # observability: ignore R2: lc is optional metadata
                        location = None
                    if location is not None:
                        locations[child] = location
                walk(item, child)
        elif isinstance(node, (list, tuple)):
            line_collections = getattr(node, "lc", None)
            for index, item in enumerate(node):
                child = f"{path}[{index}]"
                if line_collections is not None:
                    try:
                        location = _location(line_collections.item(index))
                    except Exception:  # observability: ignore R2: lc is optional metadata
                        location = None
                    if location is not None:
                        locations[child] = location
                walk(item, child)

    walk(tree, "")
    return locations


def _build_value(value: Any, spec: Mapping[str, Any]) -> Any:
    if isinstance(value, Mapping):
        result = CommentedMap()
        for key, item in value.items():
            child_spec = spec.get("fields", {}).get(key) if spec.get("fields") else spec.get("items")
            result[key] = _build_value(item, child_spec or {})
        return result
    if isinstance(value, (list, tuple)):
        return [_build_value(item, spec.get("items", {})) for item in value]
    if isinstance(value, str) and "\n" in value:
        return LiteralScalarString(value)
    return value


def _remap_sequence_comments(
    new_sequence: CommentedSeq,
    old_sequence: CommentedSeq,
    old_indices: list[int | None],
) -> None:
    old_ca = getattr(old_sequence, "ca", None)
    if old_ca is None:
        return
    new_ca = new_sequence.ca
    new_ca.comment = old_ca.comment
    new_ca.end = old_ca.end
    for new_index, old_index in enumerate(old_indices):
        if old_index is None:
            continue
        comment = old_ca.items.get(old_index)
        if comment is not None:
            new_ca.items[new_index] = comment


def _merge_sequence(
    existing: Any,
    value: Any,
    spec: Mapping[str, Any],
) -> Any:
    identity = spec.get("identity")
    if (
        not identity
        or not isinstance(existing, CommentedSeq)
        or not all(isinstance(item, Mapping) for item in value)
        or not all(isinstance(item, Mapping) for item in existing)
    ):
        return _build_value(value, spec)

    old_index: dict[tuple, int] = {}
    for index, item in enumerate(existing):
        key = tuple(item.get(name) for name in identity)
        old_index.setdefault(key, index)
    used: set[int] = set()
    merged: list[tuple[Any, int | None]] = []
    for item in value:
        key = tuple(item.get(name) for name in identity)
        index = old_index.get(key)
        if index is not None and index not in used:
            used.add(index)
            target = existing[index]
            _merge_mapping(target, item, spec.get("items", {}))
            merged.append((target, index))
        else:
            merged.append((_build_value(item, spec.get("items", {})), None))
    if [index for _, index in merged] == list(range(len(existing))):
        return existing
    new_sequence = CommentedSeq([item for item, _ in merged])
    _remap_sequence_comments(
        new_sequence,
        existing,
        [index for _, index in merged],
    )
    return new_sequence


def _merge_value(existing: Any, value: Any, spec: Mapping[str, Any]) -> Any:
    if spec.get("type") == "mapping" and isinstance(value, Mapping) and isinstance(existing, Mapping):
        _merge_mapping(existing, value, spec)
        return existing
    if spec.get("type") == "list" and isinstance(value, (list, tuple)):
        return _merge_sequence(existing, value, spec)
    return _build_value(value, spec)


def _merge_mapping(
    target: Mapping[str, Any],
    value: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> None:
    fields = spec.get("fields")
    item_spec = spec.get("items")
    for key in list(target.keys()):
        if key not in value:
            del target[key]
    for key, item in value.items():
        child_spec = fields.get(key) if fields else item_spec
        child_spec = child_spec or {}
        if key in target:
            target[key] = _merge_value(target[key], item, child_spec)
        else:
            target[key] = _build_value(item, child_spec)


def parse_document(relative_path: str, text: str) -> ParsedDocument:
    """Parse one supported source into typed values plus its round-trip tree."""

    expected = expected_document(relative_path)
    if expected is None:
        raise _single(
            _structure(
                "unsupported_source_path",
                f"{relative_path!r} is not a supported map source path",
                relative_path=relative_path,
            )
        )
    kind, identity = expected
    if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise _single(
            _structure(
                "invalid_document_size",
                f"{relative_path} exceeds {MAX_DOCUMENT_BYTES} bytes",
                relative_path=relative_path,
            )
        )
    _scan_events(text, relative_path)
    try:
        tree = _yaml_loader().load(text)
    except DuplicateKeyError as error:
        mark = getattr(error, "problem_mark", None) or getattr(error, "context_mark", None)
        raise _single(
            _structure(
                "duplicate_key",
                str(error).splitlines()[0],
                relative_path=relative_path,
                line=(mark.line + 1) if mark else None,
                column=(mark.column + 1) if mark else None,
            )
        ) from error
    except ComposerError as error:
        raise _single(
            _structure(
                "multiple_documents",
                "a map source must contain exactly one YAML document",
                relative_path=relative_path,
            )
        ) from error
    except YAMLError as error:
        mark = getattr(error, "problem_mark", None) or getattr(error, "context_mark", None)
        raise _single(
            _structure(
                "invalid_yaml",
                str(error).splitlines()[0],
                relative_path=relative_path,
                line=(mark.line + 1) if mark else None,
                column=(mark.column + 1) if mark else None,
            )
        ) from error
    if not isinstance(tree, CommentedMap):
        raise _single(
            _structure(
                "invalid_document_type",
                "the document root must be a mapping",
                relative_path=relative_path,
            )
        )
    _check_loaded_value(tree, "", relative_path)
    data = _plain(tree)
    provenance = _provenance(tree)
    diagnostics = schema_module.validate_document(
        kind,
        data,
        relative_path=relative_path,
        expected_identity=identity,
        provenance=provenance,
    )
    if diagnostics:
        raise AuthoringError(diagnostics)
    from .documents import build_document

    document = build_document(
        kind,
        relative_path=_normalise_path(relative_path),
        identity=identity,
        version=int(data["version"]),
        fingerprint=fingerprint_text(text),
        data=data,
        provenance=provenance,
    )
    return ParsedDocument(
        relative_path=_normalise_path(relative_path),
        kind=kind,
        identity=identity,
        version=document.version,
        document=document,
        provenance=provenance,
        round_trip=tree,
    )


def _normalise_path(relative_path: str) -> str:
    return relative_path.replace("\\", "/")


def document_from_data(
    relative_path: str,
    data: Mapping[str, Any],
    *,
    provenance: Mapping[str, SourceLocation] | None = None,
) -> Any:
    """Validate a programmatic candidate and build its typed document."""

    expected = expected_document(relative_path)
    if expected is None:
        raise _single(
            _structure(
                "unsupported_source_path",
                f"{relative_path!r} is not a supported map source path",
                relative_path=relative_path,
            )
        )
    kind, identity = expected
    diagnostics = schema_module.validate_document(
        kind,
        data,
        relative_path=relative_path,
        expected_identity=identity,
        provenance=provenance,
    )
    if diagnostics:
        raise AuthoringError(diagnostics)
    from .documents import build_document

    plain = _thaw(data)
    return build_document(
        kind,
        relative_path=_normalise_path(relative_path),
        identity=identity,
        version=int(data["version"]),
        fingerprint=fingerprint_text(repr(plain)),
        data=plain,
        provenance=provenance or {},
    )


def serialize_document(document: Any, retained_tree: Mapping[str, Any] | None = None) -> str:
    """Serialize a typed document, retaining supported comments when possible.

    ``retained_tree`` is read, never mutated: a failed candidate leaves the
    caller's baseline untouched.
    """

    data = _thaw(document.data)
    diagnostics = schema_module.validate_document(
        document.kind,
        data,
        relative_path=document.relative_path,
        expected_identity=document.identity,
        provenance=document.provenance,
    )
    if diagnostics:
        raise AuthoringError(diagnostics)
    meta = schema_module.document_meta(document.kind)
    if meta is None:
        raise _single(
            _structure(
                "unsupported_kind",
                f"unsupported document kind {document.kind!r}",
                relative_path=document.relative_path,
            )
        )
    root = deepcopy(retained_tree) if retained_tree is not None else CommentedMap()
    if not isinstance(root, MutableMapping):
        raise _single(
            _structure(
                "invalid_retained_tree",
                "the retained tree root must be a mapping",
                relative_path=document.relative_path,
            )
        )
    _merge_mapping(root, data, {"type": "mapping", "fields": meta["fields"]})
    output = StringIO()
    _yaml_dumper().dump(root, output)
    text = output.getvalue()
    try:
        reparsed = parse_document(document.relative_path, text)
    except AuthoringError as error:
        raise AuthoringError(
            tuple(error.diagnostics)
            + (
                _structure(
                    "emitted_document_invalid",
                    "the emitted YAML does not pass the restricted parser",
                    relative_path=document.relative_path,
                ),
            )
        ) from error
    if reparsed.document.data != document.data:
        raise _single(
            _structure(
                "emitted_document_mismatch",
                "the emitted YAML does not round-trip the candidate values",
                relative_path=document.relative_path,
            )
        )
    return text


__all__ = [
    "ParsedDocument",
    "document_from_data",
    "parse_document",
    "serialize_document",
]
