"""Filesystem discovery and snapshot loading for authored static dialogue YAML."""

from __future__ import annotations

import os
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml
from yaml.composer import ComposerError
from yaml.constructor import ConstructorError
from yaml.scanner import ScannerError

from world.lore.dialogue.codec import StaticDialogueIdentity, parse_dialogue
from world.lore.dialogue.conditions import DialogueReferences
from world.lore.dialogue.shape import AuthoredDialogue

MAX_DIALOGUE_FILE_BYTES = 262144  # 256 KiB


class DialogueSourceError(ValueError):
    """Raised when an authored dialogue source file or collection fails validation."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | str | None = None,
        profile_key: str | None = None,
        dialogue_key: str | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.profile_key = profile_key
        self.dialogue_key = dialogue_key


class StrictDialogueYamlLoader(yaml.SafeLoader):
    """YAML safe loader enforcing no aliases, no anchors, no merge keys, and no duplicate keys."""

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.events.AliasEvent):
            event = self.peek_event()
            anchor_name = getattr(event, "anchor", "")
            raise DialogueSourceError(f"YAML aliases are forbidden: *{anchor_name}")
        event = self.peek_event()
        if getattr(event, "anchor", None) is not None:
            raise DialogueSourceError(f"YAML anchors are forbidden: &{event.anchor}")
        return super().compose_node(parent, index)

    def construct_mapping(self, node: yaml.nodes.MappingNode, deep: bool = False) -> dict[str, Any]:
        if not isinstance(node, yaml.nodes.MappingNode):
            raise DialogueSourceError(f"Expected a mapping node, got {type(node).__name__}")
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise DialogueSourceError("YAML merge keys (<<) are forbidden")
            key = self.construct_object(key_node, deep=False)
            if not isinstance(key, str):
                raise DialogueSourceError(
                    f"Mapping keys must be strings, got {type(key).__name__}: {key!r}"
                )
            if key in mapping:
                raise DialogueSourceError(f"Duplicate mapping key: {key!r}")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


# Restrict YAML constructors to pure standard primitive JSON-compatible types
StrictDialogueYamlLoader.yaml_constructors = dict(yaml.SafeLoader.yaml_constructors)
for forbidden_tag in (
    "tag:yaml.org,2002:binary",
    "tag:yaml.org,2002:timestamp",
    "tag:yaml.org,2002:omap",
    "tag:yaml.org,2002:pairs",
    "tag:yaml.org,2002:set",
):
    StrictDialogueYamlLoader.yaml_constructors.pop(forbidden_tag, None)


def _safe_read_file(path: Path) -> str:
    """Read a regular file under size limit rejecting symlinks, returning decoded UTF-8 text."""
    # Check if entry itself is a symlink
    if path.is_symlink():
        raise DialogueSourceError(f"File {path.name!r} is a symlink", path=path)

    # Use O_NOFOLLOW where available to prevent symlink races
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise DialogueSourceError(f"Cannot open file {path.name!r}: {exc}", path=path) from exc

    try:
        stat_info = os.fstat(fd)
        import stat
        if not stat.S_ISREG(stat_info.st_mode):
            raise DialogueSourceError(f"File {path.name!r} is not a regular file", path=path)
        if stat_info.st_size > MAX_DIALOGUE_FILE_BYTES:
            raise DialogueSourceError(
                f"File {path.name!r} size {stat_info.st_size} exceeds maximum {MAX_DIALOGUE_FILE_BYTES} bytes",
                path=path,
            )

        # Read up to MAX_DIALOGUE_FILE_BYTES + 1 to verify actual byte size
        raw_bytes = os.read(fd, MAX_DIALOGUE_FILE_BYTES + 1)
        if len(raw_bytes) > MAX_DIALOGUE_FILE_BYTES:
            raise DialogueSourceError(
                f"File {path.name!r} content exceeds maximum {MAX_DIALOGUE_FILE_BYTES} bytes",
                path=path,
            )
    finally:
        os.close(fd)

    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DialogueSourceError(f"File {path.name!r} is not valid UTF-8: {exc}", path=path) from exc


def _parse_yaml_text(text: str, *, path: Path) -> Any:
    """Parse YAML text using StrictDialogueYamlLoader, ensuring single document."""
    try:
        loader = StrictDialogueYamlLoader(text)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()
    except (ComposerError, ConstructorError, ScannerError, yaml.YAMLError) as exc:
        raise DialogueSourceError(
            f"YAML parse error in file {path.name!r}: {exc}", path=path
        ) from exc
    except DialogueSourceError as exc:
        exc.path = path
        raise


def load_dialogue_snapshot(
    content_dir: Path | str,
    *,
    profiles: frozenset[str],
    bindings: Mapping[str, str],
    references: DialogueReferences,
) -> Mapping[str, AuthoredDialogue]:
    """Scan and parse authored dialogue YAML files into an immutable snapshot.

    Args:
        content_dir: Directory containing per-profile ``<profile_key>.yaml`` files.
        profiles: Frozenset of registered ``NpcProfile.key`` identifiers.
        bindings: Canonical mapping from ``dialogue_key`` to ``profile_key``.
        references: Permission catalog for validating condition references.

    Returns:
        A read-only ``MappingProxyType[str, AuthoredDialogue]`` keyed by ``dialogue_key``.

    Raises:
        FileNotFoundError: If ``content_dir`` does not exist.
        NotADirectoryError: If ``content_dir`` is not a directory.
        DialogueSourceError: If any file fails discovery, size, YAML syntax, schema,
            reference validation, or if bindings / discovered profiles do not match.
    """
    root_path = Path(content_dir)
    if not root_path.exists():
        raise FileNotFoundError(f"Content directory does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Content path is not a directory: {root_path}")

    # Validate bindings structure: dialogue_key -> profile_key must be unique per profile_key
    profile_to_dialogue: dict[str, str] = {}
    for diag_key, prof_key in bindings.items():
        if prof_key in profile_to_dialogue:
            raise DialogueSourceError(
                f"Duplicate canonical binding for profile {prof_key!r}: bound to {profile_to_dialogue[prof_key]!r} and {diag_key!r}",
                profile_key=prof_key,
                dialogue_key=diag_key,
            )
        profile_to_dialogue[prof_key] = diag_key

    # Scan direct directory entries
    discovered_entries: list[Path] = []
    try:
        for entry in os.scandir(root_path):
            if entry.name.endswith(".yaml"):
                discovered_entries.append(root_path / entry.name)
    except OSError as exc:
        raise DialogueSourceError(f"Failed to scan directory {root_path}: {exc}") from exc

    # Sort discovered files stably by filename
    discovered_entries.sort(key=lambda p: p.name)

    # Validate discovered entries and stems
    discovered_profiles: set[str] = set()
    file_by_profile: dict[str, Path] = {}

    for path in discovered_entries:
        stem = path.stem
        if stem not in profiles:
            raise DialogueSourceError(
                f"Discovered file {path.name!r} stem {stem!r} is not a registered profile key",
                path=path,
                profile_key=stem,
            )
        if stem not in profile_to_dialogue:
            raise DialogueSourceError(
                f"Discovered file {path.name!r} has registered profile {stem!r} but no canonical dialogue binding",
                path=path,
                profile_key=stem,
            )
        if stem in discovered_profiles:
            raise DialogueSourceError(
                f"Duplicate file discovered for profile {stem!r}: {path.name!r}",
                path=path,
                profile_key=stem,
            )
        discovered_profiles.add(stem)
        file_by_profile[stem] = path

    # Completeness check: every binding must resolve to exactly one discovered file
    for diag_key, prof_key in bindings.items():
        if prof_key not in discovered_profiles:
            raise DialogueSourceError(
                f"Canonical dialogue binding {diag_key!r} for profile {prof_key!r} has no discovered file ({prof_key}.yaml)",
                profile_key=prof_key,
                dialogue_key=diag_key,
            )

    # Parse and validate every discovered file in sorted order
    candidate_snapshot: dict[str, AuthoredDialogue] = {}

    for path in discovered_entries:
        stem = path.stem
        diag_key = profile_to_dialogue[stem]

        # Read raw content safely
        text = _safe_read_file(path)

        # Parse strict YAML
        payload = _parse_yaml_text(text, path=path)

        if not isinstance(payload, dict):
            raise DialogueSourceError(
                f"File {path.name!r} root must be a mapping, got {type(payload).__name__}",
                path=path,
                profile_key=stem,
                dialogue_key=diag_key,
            )

        # Enforce exact type for schema_version (reject bool/float like true or 1.0)
        schema_version = payload.get("schema_version")
        if type(schema_version) is not int or schema_version != 1:
            raise DialogueSourceError(
                f"File {path.name!r} schema_version must be integer 1, got {schema_version!r} ({type(schema_version).__name__})",
                path=path,
                profile_key=stem,
                dialogue_key=diag_key,
            )

        # Check for explicit owner fields which are forbidden
        for owner_field in ("npc_id", "profile_key", "owner", "dialogue_key"):
            if owner_field in payload:
                raise DialogueSourceError(
                    f"File {path.name!r} contains forbidden explicit owner field: {owner_field!r}",
                    path=path,
                    profile_key=stem,
                    dialogue_key=diag_key,
                )

        identity = StaticDialogueIdentity(profile_key=stem, dialogue_key=diag_key)
        try:
            authored = parse_dialogue(payload, identity=identity, references=references)
        except (ValueError, TypeError) as exc:
            raise DialogueSourceError(
                f"Dialogue validation failed for {path.name!r} ({diag_key}): {exc}",
                path=path,
                profile_key=stem,
                dialogue_key=diag_key,
            ) from exc

        candidate_snapshot[diag_key] = authored

    return MappingProxyType(candidate_snapshot)
