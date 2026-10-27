"""Deterministic discovery and canonical identity of authored map sources.

The supported world source set is exactly::

    content/maps/continent.yaml
    content/maps/locations.yaml
    content/maps/districts.yaml
    content/maps/settlements/<map_id>.yaml
    content/maps/interiors/<interior_id>.yaml

Editor layout documents under ``content/map-editor-layouts/<interior_id>.yaml``
are recognised by the codec but are never discovered as world snapshot inputs.
Generated artifacts (the district partition, the reference context) live
elsewhere and are never scanned as sources.

Discovery is a pure read: it returns the sorted canonical relative paths and
their text, never writes, caches across calls, or runs at import time.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import AuthoringError, Diagnostic, STRUCTURE
from .schema import MAX_DOCUMENT_BYTES

FIXED_SOURCES: dict[str, tuple[str, str]] = {
    "content/maps/continent.yaml": ("continent", "continent"),
    "content/maps/locations.yaml": ("locations", "locations"),
    "content/maps/districts.yaml": ("districts", "districts"),
}

SOURCE_DIRECTORIES: dict[str, str] = {
    "content/maps/settlements": "settlement",
    "content/maps/interiors": "interior",
}

LAYOUT_DIRECTORY = "content/map-editor-layouts"
LAYOUT_KIND = "layout"


def fingerprint_text(text: str) -> str:
    """The content fingerprint consumers compare before replacing a file."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """One caller-supplied source: canonical path, text and content fingerprint.

    The fingerprint is caller metadata, not trusted input: the authoring loader
    recomputes it and rejects a mismatched pair.
    """

    relative_path: str
    text: str
    fingerprint: str


def make_source_document(
    relative_path: str,
    text: str,
    fingerprint: str | None = None,
) -> SourceDocument:
    """Build a source document, computing the fingerprint when omitted."""

    return SourceDocument(
        relative_path=relative_path,
        text=text,
        fingerprint=fingerprint if fingerprint is not None else fingerprint_text(text),
    )


def _normalise(relative_path: str) -> str | None:
    path = relative_path.replace("\\", "/")
    if path.startswith("/") or path.startswith("./"):
        return None
    parts = path.split("/")
    if not path or any(part in ("", ".", "..") for part in parts):
        return None
    return path


def expected_document(relative_path: str) -> tuple[str, str | None] | None:
    """Return ``(kind, identity)`` for a supported path, else ``None``.

    ``identity`` is the fixed id for the three singleton documents and the file
    stem for settlements, interiors and layouts.
    """

    path = _normalise(relative_path)
    if path is None:
        return None
    fixed = FIXED_SOURCES.get(path)
    if fixed is not None:
        return fixed
    parent, _, filename = path.rpartition("/")
    kind = SOURCE_DIRECTORIES.get(parent)
    if kind is None and parent == LAYOUT_DIRECTORY:
        kind = LAYOUT_KIND
    if kind is None or not filename.endswith(".yaml"):
        return None
    stem = filename[: -len(".yaml")]
    if not stem:
        return None
    return kind, stem


def is_world_source(relative_path: str) -> bool:
    """Whether this path is one of the world snapshot's supported sources."""

    expected = expected_document(relative_path)
    return expected is not None and expected[0] != LAYOUT_KIND


def _ordered(relative_path: str) -> str:
    return _normalise(relative_path) or relative_path


def discover_source_paths(root: str | Path) -> tuple[str, ...]:
    """Return the sorted canonical world source paths under ``root``."""

    root_path = Path(root)
    paths: list[str] = []
    for relative_path in FIXED_SOURCES:
        if (root_path / relative_path).is_file():
            paths.append(relative_path)
    for directory in SOURCE_DIRECTORIES:
        directory_path = root_path / directory
        if not directory_path.is_dir():
            continue
        for child in directory_path.glob("*.yaml"):
            if child.is_file():
                paths.append(f"{directory}/{child.name}")
    return tuple(sorted({_ordered(path) for path in paths}))


def read_source_document(root: str | Path, relative_path: str) -> SourceDocument:
    """Read one world source, rejecting unsupported paths and oversized input."""

    expected = expected_document(relative_path)
    if expected is None or expected[0] == LAYOUT_KIND:
        raise AuthoringError(
            (
                Diagnostic(
                    code="unsupported_source_path",
                    category=STRUCTURE,
                    message=f"{relative_path!r} is not a supported map source path",
                    relative_path=relative_path,
                    field_path="",
                ),
            )
        )
    path = Path(root) / _ordered(relative_path)
    raw = path.read_bytes()
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise AuthoringError(
            (
                Diagnostic(
                    code="invalid_document_size",
                    category=STRUCTURE,
                    message=f"{relative_path} is {len(raw)} bytes, limit "
                    f"{MAX_DOCUMENT_BYTES}",
                    relative_path=relative_path,
                    field_path="",
                ),
            )
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuthoringError(
            (
                Diagnostic(
                    code="invalid_encoding",
                    category=STRUCTURE,
                    message=f"{relative_path} is not valid UTF-8: {error}",
                    relative_path=relative_path,
                    field_path="",
                ),
            )
        ) from error
    return make_source_document(_ordered(relative_path), text)


def discover_source_documents(root: str | Path) -> tuple[SourceDocument, ...]:
    """Read every discovered world source in sorted path order."""

    return tuple(
        read_source_document(root, relative_path)
        for relative_path in discover_source_paths(root)
    )
