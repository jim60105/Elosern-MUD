"""Strict validation of the authored landmark rite document.

The single document (``world/lore/rites/content/landmark_rites.yaml``) holds the
ritual archetypes, their options and scenes, and the assignment of every map
district to one archetype. It is the only source of rite content: the rules
layer reads the installed snapshot and never parses YAML.

This loader is pure and deterministic -- text in, immutable snapshot or one
:class:`RiteContentError` carrying every fault out. Each fault names its field
path from the document root and one stable code:

``document_shape``
    The document, a mapping or a key is absent or of the wrong type. Every
    YAML-layer fault reports this code too: the strict dialogue YAML loader
    rejects duplicate mapping keys, anchors, aliases and merge keys before this
    module sees a value, so the whole document is unusable and no deeper field
    path exists.
``unknown_field``
    A mapping carries a key the document does not define.
``archetype_count``
    The archetype mapping holds fewer than one or more than sixteen entries.
``key_format``
    An archetype or option key does not match :data:`KEY_PATTERN`.
``text_bound``
    An authored text is not a string or is outside its code-point bound.
``option_count``
    An archetype declares fewer than two or more than three options.
``duplicate_option``
    Two options of one archetype share a key.
``seconds_bound``
    An option duration is not an integer in 120..900 seconds.
``level_bound``
    A shame or exposure step is not an integer in 0..2.
``scene_invalid``
    A scene document is malformed, an identity or the line model rejects it, or
    an option omits the required ``watch`` key.
``scene_no_narration``
    A scene declares no narration line.
``duplicate_scene_id``
    Two scenes share one scene identifier.
``district_unknown``
    The assignment names a district the caller did not supply.
``district_unassigned``
    A supplied district is absent from the assignment.
``archetype_unknown``
    The assignment names an archetype the document does not declare.
``archetype_unused``
    A validly declared archetype is assigned to no district.

A rite scene deliberately differs from a formal dialogue scene: it may open with
narration (the dialogue rule that a formal scene starts with an actor utterance
is not applied). Its speakers stay restricted to ``actor`` and ``host`` and it
holds at least one narration line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from world.lore.dialogue.loader import DialogueSourceError, StrictDialogueYamlLoader
from world.lore.rites.shape import RiteArchetype, RiteOption, RiteSnapshot
from world.lore.scenes import (
    REVISION_PATTERN,
    STATIC_SCENE_ID_PATTERN,
    Narration,
    Scene,
    SceneLine,
    Speech,
)

__all__ = [
    "KEY_PATTERN",
    "MAX_ARCHETYPES",
    "MAX_GUARDIAN_FORM_CODE_POINTS",
    "MAX_GUARDIAN_NAME_CODE_POINTS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_LEVEL",
    "MAX_OPTIONS",
    "MAX_RITES_FILE_BYTES",
    "MAX_SECONDS",
    "MIN_ARCHETYPES",
    "MIN_OPTIONS",
    "MIN_SECONDS",
    "RiteContentError",
    "RiteDiagnostic",
    "load_rites",
    "parse_rites_document",
]

#: The largest rite document the loader reads; a larger file is rejected whole.
MAX_RITES_FILE_BYTES = 1_048_576

#: Archetype and option keys.
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,31}\Z")

MIN_ARCHETYPES = 1
MAX_ARCHETYPES = 16
MIN_OPTIONS = 2
MAX_OPTIONS = 3
MIN_SECONDS = 120
MAX_SECONDS = 900
MAX_LEVEL = 2
MAX_GUARDIAN_NAME_CODE_POINTS = 32
MAX_GUARDIAN_FORM_CODE_POINTS = 200
MAX_LABEL_CODE_POINTS = 32

_DOCUMENT_KIND = "landmark_rites"
_DOCUMENT_VERSION = 1

_TOP_LEVEL_FIELDS = ("version", "kind", "id", "archetypes", "districts")
_ARCHETYPE_FIELDS = ("guardian_name_zh", "guardian_form_zh", "options")
_OPTION_FIELDS = ("key", "label_zh", "seconds", "shame", "exposure", "self", "watch")
_REQUIRED_OPTION_FIELDS = ("key", "label_zh", "seconds", "shame", "exposure", "self")
_SCENE_FIELDS = ("scene_id", "revision", "lines")
_LINE_FIELDS = {
    "narration": ("kind", "text"),
    "speech": ("kind", "speaker", "text"),
}
_SPEAKERS = ("actor", "host")

_DOCUMENT_SHAPE = "document_shape"
_UNKNOWN_FIELD = "unknown_field"
_ARCHETYPE_COUNT = "archetype_count"
_KEY_FORMAT = "key_format"
_TEXT_BOUND = "text_bound"
_OPTION_COUNT = "option_count"
_DUPLICATE_OPTION = "duplicate_option"
_SECONDS_BOUND = "seconds_bound"
_LEVEL_BOUND = "level_bound"
_SCENE_INVALID = "scene_invalid"
_SCENE_NO_NARRATION = "scene_no_narration"
_DUPLICATE_SCENE_ID = "duplicate_scene_id"
_DISTRICT_UNKNOWN = "district_unknown"
_DISTRICT_UNASSIGNED = "district_unassigned"
_ARCHETYPE_UNKNOWN = "archetype_unknown"
_ARCHETYPE_UNUSED = "archetype_unused"


@dataclass(frozen=True, slots=True)
class RiteDiagnostic:
    """One rejected field of a rite document."""

    field_path: str
    code: str
    message: str


class RiteContentError(ValueError):
    """A rite document was rejected; ``diagnostics`` names every fault."""

    def __init__(self, diagnostics: tuple[RiteDiagnostic, ...]) -> None:
        self.diagnostics = tuple(
            sorted(diagnostics, key=lambda item: (item.field_path, item.code))
        )
        super().__init__(
            "invalid landmark rite content:\n"
            + "\n".join(
                f"{item.field_path or '<document>'}: {item.code}: {item.message}"
                for item in self.diagnostics
            )
        )


def _fault(
    problems: list[RiteDiagnostic], field_path: str, code: str, message: str
) -> None:
    problems.append(RiteDiagnostic(field_path=field_path, code=code, message=message))


def _is_text(value: object, minimum: int, maximum: int) -> bool:
    return isinstance(value, str) and minimum <= len(value) <= maximum


def _is_step(value: object, minimum: int, maximum: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def _check_fields(
    node: dict[str, Any],
    allowed: tuple[str, ...],
    field_path: str,
    problems: list[RiteDiagnostic],
    required: tuple[str, ...] | None = None,
) -> list[str]:
    """Report unknown and missing keys of one mapping; return the missing names."""

    unknown = [key for key in node if key not in allowed]
    for key in unknown:
        _fault(
            problems,
            f"{field_path}.{key}" if field_path else key,
            _UNKNOWN_FIELD,
            f"unknown field {key!r}",
        )
    needed = allowed if required is None else required
    absent = [field for field in needed if field not in node]
    for field in absent:
        _fault(
            problems,
            f"{field_path}.{field}" if field_path else field,
            _DOCUMENT_SHAPE,
            f"missing field {field!r}",
        )
    return absent


def _file_error(message: str) -> RiteContentError:
    """One whole-document rejection raised by the file reader."""

    return RiteContentError(
        (RiteDiagnostic(field_path="", code=_DOCUMENT_SHAPE, message=message),)
    )


def _parse_yaml(text: str, problems: list[RiteDiagnostic]) -> Any:
    """Parse one YAML document with the strict loader; a fault leaves the document unusable."""

    try:
        loader = StrictDialogueYamlLoader(text)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
    except (DialogueSourceError, yaml.YAMLError) as exc:
        _fault(
            problems,
            "",
            _DOCUMENT_SHAPE,
            f"the rite document is not a valid strict YAML document: {exc}",
        )
        return None


def _line(node: Any, field_path: str, problems: list[RiteDiagnostic]) -> SceneLine | None:
    """Build one scene line from its document, or return ``None`` after reporting."""

    before = len(problems)
    if not isinstance(node, dict):
        _fault(problems, field_path, _DOCUMENT_SHAPE, "a scene line must be a mapping")
        return None

    kind = node.get("kind")
    if not isinstance(kind, str) or kind not in _LINE_FIELDS:
        _fault(
            problems,
            f"{field_path}.kind",
            _SCENE_INVALID,
            f"a scene line kind must be 'narration' or 'speech', got {kind!r}",
        )
        return None

    absent = _check_fields(node, _LINE_FIELDS[kind], field_path, problems)
    speaker = node.get("speaker")
    if "speaker" in _LINE_FIELDS[kind] and "speaker" not in absent:
        if not isinstance(speaker, str) or speaker not in _SPEAKERS:
            _fault(
                problems,
                f"{field_path}.speaker",
                _SCENE_INVALID,
                f"a speech speaker must be 'actor' or 'host', got {speaker!r}",
            )
    if len(problems) != before:
        return None

    try:
        if kind == "narration":
            return Narration(text=node["text"])
        return Speech(speaker=speaker, text=node["text"])
    except (TypeError, ValueError) as exc:
        _fault(problems, field_path, _SCENE_INVALID, str(exc))
        return None


def _scene(
    node: Any, field_path: str, seen_scene_ids: set[str], problems: list[RiteDiagnostic]
) -> Scene | None:
    """Build one scene from its document, or return ``None`` after reporting."""

    before = len(problems)
    if not isinstance(node, dict):
        _fault(problems, field_path, _DOCUMENT_SHAPE, "a scene must be a mapping")
        return None

    absent = _check_fields(node, _SCENE_FIELDS, field_path, problems)

    if "scene_id" not in absent:
        scene_id = node["scene_id"]
        if isinstance(scene_id, str):
            if scene_id in seen_scene_ids:
                _fault(
                    problems,
                    f"{field_path}.scene_id",
                    _DUPLICATE_SCENE_ID,
                    f"scene identifier {scene_id!r} is already used in this document",
                )
            else:
                seen_scene_ids.add(scene_id)
        if not isinstance(scene_id, str) or not STATIC_SCENE_ID_PATTERN.match(scene_id):
            _fault(
                problems,
                f"{field_path}.scene_id",
                _SCENE_INVALID,
                f"a scene identifier must match {STATIC_SCENE_ID_PATTERN.pattern}",
            )

    if "revision" not in absent:
        revision = node["revision"]
        if not isinstance(revision, str) or not REVISION_PATTERN.match(revision):
            _fault(
                problems,
                f"{field_path}.revision",
                _SCENE_INVALID,
                f"a scene revision must match {REVISION_PATTERN.pattern}",
            )

    lines: list[SceneLine] = []
    if "lines" not in absent and not isinstance(node["lines"], list):
        _fault(problems, f"{field_path}.lines", _DOCUMENT_SHAPE, "scene lines must be a sequence")
    elif "lines" not in absent:
        declared = [
            line.get("kind") if isinstance(line, dict) else None for line in node["lines"]
        ]
        if all(isinstance(kind, str) and kind in _LINE_FIELDS for kind in declared):
            if "narration" not in declared:
                _fault(
                    problems,
                    field_path,
                    _SCENE_NO_NARRATION,
                    "a rite scene must contain at least one narration line",
                )
        for index, line_node in enumerate(node["lines"]):
            built = _line(line_node, f"{field_path}.lines[{index}]", problems)
            if built is not None:
                lines.append(built)

    if len(problems) != before:
        return None

    try:
        return Scene(scene_id=node["scene_id"], revision=node["revision"], lines=tuple(lines))
    except (TypeError, ValueError) as exc:
        _fault(problems, field_path, _SCENE_INVALID, str(exc))
        return None


def _option(
    node: Any, field_path: str, seen_scene_ids: set[str], problems: list[RiteDiagnostic]
) -> RiteOption | None:
    """Build one option from its document, or return ``None`` after reporting."""

    before = len(problems)
    if not isinstance(node, dict):
        _fault(problems, field_path, _DOCUMENT_SHAPE, "an option must be a mapping")
        return None

    absent = _check_fields(
        node, _OPTION_FIELDS, field_path, problems, required=_REQUIRED_OPTION_FIELDS
    )
    if "watch" not in node:
        _fault(
            problems,
            f"{field_path}.watch",
            _SCENE_INVALID,
            "an option must declare its watch perspective as a scene or as null",
        )

    if "key" not in absent:
        key = node["key"]
        if not isinstance(key, str) or not KEY_PATTERN.match(key):
            _fault(
                problems,
                f"{field_path}.key",
                _KEY_FORMAT,
                f"an option key must match {KEY_PATTERN.pattern}, got {key!r}",
            )

    if "label_zh" not in absent:
        if not _is_text(node["label_zh"], 1, MAX_LABEL_CODE_POINTS):
            _fault(
                problems,
                f"{field_path}.label_zh",
                _TEXT_BOUND,
                f"label_zh must be a string of 1..{MAX_LABEL_CODE_POINTS} code points",
            )

    if "seconds" not in absent:
        if not _is_step(node["seconds"], MIN_SECONDS, MAX_SECONDS):
            _fault(
                problems,
                f"{field_path}.seconds",
                _SECONDS_BOUND,
                f"seconds must be an integer of {MIN_SECONDS}..{MAX_SECONDS}",
            )

    for field in ("shame", "exposure"):
        if field not in absent:
            if not _is_step(node[field], 0, MAX_LEVEL):
                _fault(
                    problems,
                    f"{field_path}.{field}",
                    _LEVEL_BOUND,
                    f"{field} must be an integer of 0..{MAX_LEVEL}",
                )

    self_scene = None
    if "self" not in absent:
        self_scene = _scene(node["self"], f"{field_path}.self", seen_scene_ids, problems)

    watch_scene = None
    if "watch" in node and node["watch"] is not None:
        watch_scene = _scene(node["watch"], f"{field_path}.watch", seen_scene_ids, problems)

    if len(problems) != before:
        return None

    return RiteOption(
        key=node["key"],
        label_zh=node["label_zh"],
        seconds=node["seconds"],
        shame=node["shame"],
        exposure=node["exposure"],
        self_scene=self_scene,
        watch_scene=watch_scene,
    )


def _archetype(
    key: str, node: Any, field_path: str, seen_scene_ids: set[str], problems: list[RiteDiagnostic]
) -> RiteArchetype | None:
    """Build one archetype from its document, or return ``None`` after reporting."""

    before = len(problems)
    if not isinstance(key, str) or KEY_PATTERN.match(key) is None:
        _fault(
            problems,
            field_path,
            _KEY_FORMAT,
            f"an archetype key must match {KEY_PATTERN.pattern}, got {key!r}",
        )
    if not isinstance(node, dict):
        _fault(problems, field_path, _DOCUMENT_SHAPE, "an archetype must be a mapping")
        return None

    absent = _check_fields(node, _ARCHETYPE_FIELDS, field_path, problems)

    if "guardian_name_zh" not in absent:
        if not _is_text(node["guardian_name_zh"], 1, MAX_GUARDIAN_NAME_CODE_POINTS):
            _fault(
                problems,
                f"{field_path}.guardian_name_zh",
                _TEXT_BOUND,
                "guardian_name_zh must be a string of "
                f"1..{MAX_GUARDIAN_NAME_CODE_POINTS} code points",
            )
    if "guardian_form_zh" not in absent:
        if not _is_text(node["guardian_form_zh"], 1, MAX_GUARDIAN_FORM_CODE_POINTS):
            _fault(
                problems,
                f"{field_path}.guardian_form_zh",
                _TEXT_BOUND,
                "guardian_form_zh must be a string of "
                f"1..{MAX_GUARDIAN_FORM_CODE_POINTS} code points",
            )

    options: list[RiteOption] = []
    if "options" not in absent:
        if not isinstance(node["options"], list):
            _fault(
                problems,
                f"{field_path}.options",
                _DOCUMENT_SHAPE,
                "options must be a sequence",
            )
        else:
            option_nodes = node["options"]
            if not (MIN_OPTIONS <= len(option_nodes) <= MAX_OPTIONS):
                _fault(
                    problems,
                    f"{field_path}.options",
                    _OPTION_COUNT,
                    f"an archetype must declare {MIN_OPTIONS}..{MAX_OPTIONS} options, "
                    f"got {len(option_nodes)}",
                )
            seen_option_keys: set[str] = set()
            for index, option_node in enumerate(option_nodes):
                option_path = f"{field_path}.options[{index}]"
                raw_key = option_node.get("key") if isinstance(option_node, dict) else None
                if isinstance(raw_key, str):
                    if raw_key in seen_option_keys:
                        _fault(
                            problems,
                            f"{option_path}.key",
                            _DUPLICATE_OPTION,
                            f"option key {raw_key!r} is already used in this archetype",
                        )
                    else:
                        seen_option_keys.add(raw_key)
                option = _option(option_node, option_path, seen_scene_ids, problems)
                if option is not None:
                    options.append(option)

    if len(problems) != before:
        return None

    return RiteArchetype(
        key=key,
        guardian_name_zh=node["guardian_name_zh"],
        guardian_form_zh=node["guardian_form_zh"],
        options=tuple(options),
    )


def parse_rites_document(text: str, *, district_keys: frozenset[str]) -> RiteSnapshot:
    """Validate one rite document from explicit text (no file access).

    Collects every fault and raises :class:`RiteContentError` once; returns the
    immutable snapshot only when the document carries no fault.
    """

    problems: list[RiteDiagnostic] = []
    seen_scene_ids: set[str] = set()

    document = _parse_yaml(text, problems)
    if document is None:
        if not problems:
            _fault(problems, "", _DOCUMENT_SHAPE, "the rite document is empty")
        raise RiteContentError(tuple(problems))
    if not isinstance(document, dict):
        _fault(problems, "", _DOCUMENT_SHAPE, "the rite document must be a mapping")
        raise RiteContentError(tuple(problems))

    _check_fields(document, _TOP_LEVEL_FIELDS, "", problems)

    if "version" in document:
        if not _is_step(document["version"], _DOCUMENT_VERSION, _DOCUMENT_VERSION):
            _fault(
                problems,
                "version",
                _DOCUMENT_SHAPE,
                f"version must be the integer {_DOCUMENT_VERSION}",
            )
    for field in ("kind", "id"):
        if field in document and document[field] != _DOCUMENT_KIND:
            _fault(
                problems,
                field,
                _DOCUMENT_SHAPE,
                f"{field} must be {_DOCUMENT_KIND!r}",
            )

    archetype_nodes = document.get("archetypes")
    archetypes: dict[str, RiteArchetype] = {}
    declared: set[str] = set()
    usable: set[str] = set()
    archetypes_usable = isinstance(archetype_nodes, dict) and bool(archetype_nodes)
    if "archetypes" in document:
        if not isinstance(archetype_nodes, dict):
            _fault(problems, "archetypes", _DOCUMENT_SHAPE, "archetypes must be a mapping")
        else:
            declared = set(archetype_nodes)
            if not (MIN_ARCHETYPES <= len(archetype_nodes) <= MAX_ARCHETYPES):
                _fault(
                    problems,
                    "archetypes",
                    _ARCHETYPE_COUNT,
                    f"the document must declare {MIN_ARCHETYPES}..{MAX_ARCHETYPES} "
                    f"archetypes, got {len(archetype_nodes)}",
                )
            for key, node in archetype_nodes.items():
                field_path = f"archetypes.{key}"
                archetype = _archetype(key, node, field_path, seen_scene_ids, problems)
                if isinstance(key, str) and KEY_PATTERN.match(key) and isinstance(node, dict):
                    usable.add(key)
                if archetype is not None:
                    archetypes[key] = archetype

    assignment: dict[str, str] = {}
    district_nodes = document.get("districts")
    if "districts" in document:
        if not isinstance(district_nodes, dict):
            _fault(problems, "districts", _DOCUMENT_SHAPE, "districts must be a mapping")
        else:
            for key, value in district_nodes.items():
                field_path = f"districts.{key}"
                if not isinstance(value, str):
                    _fault(
                        problems,
                        field_path,
                        _DOCUMENT_SHAPE,
                        "a district assignment must name an archetype key",
                    )
                    continue
                assignment[key] = value
                if key not in district_keys:
                    _fault(
                        problems,
                        field_path,
                        _DISTRICT_UNKNOWN,
                        f"district {key!r} is not a supplied district",
                    )
            for key in sorted(district_keys):
                if key not in district_nodes:
                    _fault(
                        problems,
                        f"districts.{key}",
                        _DISTRICT_UNASSIGNED,
                        f"supplied district {key!r} is not assigned to an archetype",
                    )
            if archetypes_usable:
                assigned = set(assignment.values())
                for key, archetype_key in assignment.items():
                    if archetype_key not in declared:
                        _fault(
                            problems,
                            f"districts.{key}",
                            _ARCHETYPE_UNKNOWN,
                            f"archetype {archetype_key!r} is not declared",
                        )
                for key in archetype_nodes:
                    if key in usable and key not in assigned:
                        _fault(
                            problems,
                            f"archetypes.{key}",
                            _ARCHETYPE_UNUSED,
                            f"archetype {key!r} is assigned to no district",
                        )

    if problems:
        raise RiteContentError(tuple(problems))

    return RiteSnapshot(archetypes=archetypes, districts=assignment)


def load_rites(path: Path, *, district_keys: frozenset[str]) -> RiteSnapshot:
    """Read at most :data:`MAX_RITES_FILE_BYTES` of ``path`` and validate it."""

    source = Path(path)
    try:
        with source.open("rb") as handle:
            raw = handle.read(MAX_RITES_FILE_BYTES + 1)
    except OSError as exc:
        raise _file_error(f"cannot read {source.name!r}: {exc}") from exc
    if len(raw) > MAX_RITES_FILE_BYTES:
        raise _file_error(f"{source.name!r} exceeds {MAX_RITES_FILE_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _file_error(f"{source.name!r} is not valid UTF-8: {exc}") from exc
    return parse_rites_document(text, district_keys=district_keys)