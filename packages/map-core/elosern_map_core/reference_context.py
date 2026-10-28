"""Pure deterministic reference-context codec, freshness checker and deletion guard.

This module is the core half of the external static reference contract. It reads
and validates the committed reference-context document, checks freshness
against file hashes and source closure membership, and evaluates deletion
safety without importing any game modules, Evennia, or Django.

Format layout:
* ``schema_version`` -- schema version of the reference-context format (:data:`SCHEMA_VERSION`).
* ``exporter_version`` -- version of the exporter that generated it (:data:`EXPORTER_VERSION`).
* ``external_identifiers`` -- mapping of identifier family name to sorted tuple of strings.
* ``incoming_references`` -- mapping of qualified target canonical string to incoming reference rows.
* ``source_manifest`` -- mapping of workspace-relative file paths to SHA-256 digests.
* ``discovery_rules`` -- allowlisted root directories / glob patterns for discovering external sources.
* ``fingerprint`` -- aggregate SHA-256 digest over schema/exporter versions, source manifest, and discovery rules.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from .documents import QualifiedRef
from .references import _describe

#: Supported reference-context document schema version.
SCHEMA_VERSION: int = 1

#: Current exporter implementation version.
EXPORTER_VERSION: int = 1

#: Status codes for reference context freshness.
STATUS_CURRENT = "current"
STATUS_MISSING = "missing"
STATUS_CHANGED = "changed"
STATUS_MEMBERSHIP_MISMATCH = "membership_mismatch"
STATUS_INCOMPATIBLE = "incompatible"

#: Status codes for deletion safety.
DELETION_ALLOWED = "allowed"
DELETION_REFUSED_UNAVAILABLE = "unavailable"
DELETION_REFUSED_REFERENCED = "referenced"


class ReferenceContextError(ValueError):
    """The reference-context document is malformed or invalid."""


@dataclass(frozen=True, slots=True)
class IncomingReference:
    """One static external incoming reference pointing to a map object."""

    source: str
    source_file: str
    source_domain: str
    target: QualifiedRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_file": self.source_file,
            "source_domain": self.source_domain,
            "target": {
                "domain": self.target.domain,
                "map_id": self.target.map_id,
                "object_id": self.target.object_id,
                "cell": list(self.target.cell) if self.target.cell is not None else None,
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> IncomingReference:
        if not isinstance(data, Mapping):
            raise ReferenceContextError("incoming reference entry must be a mapping")
        source = data.get("source")
        source_file = data.get("source_file")
        source_domain = data.get("source_domain")
        target_raw = data.get("target")
        if not isinstance(source, str) or not source:
            raise ReferenceContextError("incoming reference source must be a non-empty string")
        if not isinstance(source_file, str) or not source_file:
            raise ReferenceContextError("incoming reference source_file must be a non-empty string")
        if not isinstance(source_domain, str) or not source_domain:
            raise ReferenceContextError("incoming reference source_domain must be a non-empty string")
        if not isinstance(target_raw, Mapping):
            raise ReferenceContextError("incoming reference target must be a mapping")

        domain = target_raw.get("domain")
        if not isinstance(domain, str) or not domain:
            raise ReferenceContextError("target domain must be a non-empty string")
        map_id = target_raw.get("map_id")
        object_id = target_raw.get("object_id")
        cell_raw = target_raw.get("cell")
        cell = tuple(cell_raw) if isinstance(cell_raw, (list, tuple)) else None

        target = QualifiedRef(
            domain=domain,
            map_id=map_id if isinstance(map_id, str) else None,
            object_id=object_id if isinstance(object_id, str) else None,
            cell=cell,
        )
        return cls(
            source=source,
            source_file=source_file,
            source_domain=source_domain,
            target=target,
        )


@dataclass(frozen=True, slots=True)
class ReferenceContextFreshness:
    """The result of evaluating reference-context freshness against current sources."""

    current: bool
    status: str
    reasons: tuple[str, ...]

    def __bool__(self) -> bool:
        return self.current


@dataclass(frozen=True, slots=True)
class DeletionSafetyDecision:
    """The result of checking whether deleting an authored map object is safe."""

    allowed: bool
    status: str
    incoming_references: tuple[IncomingReference, ...] = ()
    reasons: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return self.allowed


def canonical_target_key(target: QualifiedRef | str) -> str:
    """Return the deterministic canonical key for a qualified map target."""
    if isinstance(target, str):
        return target
    if not isinstance(target, QualifiedRef):
        raise ReferenceContextError(f"expected QualifiedRef or canonical str, got {type(target)!r}")
    return _describe(target)


def compute_dependency_fingerprint(
    manifest: Mapping[str, str],
    schema_version: int,
    exporter_version: int,
    discovery_rules: Sequence[str] = (),
) -> str:
    """Compute a deterministic aggregate SHA-256 fingerprint."""
    digest = hashlib.sha256()
    digest.update(f"schema_version={schema_version}\n".encode("utf-8"))
    digest.update(f"exporter_version={exporter_version}\n".encode("utf-8"))
    for rule in sorted(discovery_rules):
        digest.update(f"rule:{rule}\n".encode("utf-8"))
    for path, file_hash in sorted(manifest.items()):
        digest.update(f"{path}:{file_hash}\n".encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ReferenceContextDocument:
    """The decoded reference context document."""

    schema_version: int
    exporter_version: int
    external_identifiers: Mapping[str, tuple[str, ...]]
    incoming_references: Mapping[str, tuple[IncomingReference, ...]]
    source_manifest: Mapping[str, str]
    discovery_rules: tuple[str, ...]
    fingerprint: str

    def incoming_references_for(self, target: QualifiedRef | str) -> tuple[IncomingReference, ...]:
        """Return incoming static external references pointing to ``target``."""
        key = canonical_target_key(target)
        return self.incoming_references.get(key, ())

    def has_incoming_references(self, target: QualifiedRef | str) -> bool:
        """Return True if any incoming static external reference points to ``target``."""
        return bool(self.incoming_references_for(target))

    def identifier_set(self, set_name: str) -> frozenset[str]:
        """Return the frozenset of external identifiers for ``set_name``."""
        return frozenset(self.external_identifiers.get(set_name, ()))

    def is_valid_identifier(self, set_name: str, identifier: str) -> bool:
        """Return True if ``identifier`` is a known member of external set ``set_name``."""
        return identifier in self.identifier_set(set_name)

    def check_deletion_safety(
        self,
        target: QualifiedRef | str,
        freshness: ReferenceContextFreshness,
    ) -> DeletionSafetyDecision:
        """Evaluate if deleting ``target`` is safe given ``freshness``.

        Deletion requires:
        1. Current, fresh external reference context (unknown or stale context
           can never prove absence of references).
        2. No incoming external static references to ``target``.
        """
        if not freshness.current:
            return DeletionSafetyDecision(
                allowed=False,
                status=DELETION_REFUSED_UNAVAILABLE,
                incoming_references=(),
                reasons=(
                    f"external reference context is unavailable ({freshness.status}): "
                    + "; ".join(freshness.reasons),
                ),
            )
        refs = self.incoming_references_for(target)
        if refs:
            target_str = canonical_target_key(target)
            reasons = tuple(
                f"{ref.source} ({ref.source_file})" for ref in refs
            )
            return DeletionSafetyDecision(
                allowed=False,
                status=DELETION_REFUSED_REFERENCED,
                incoming_references=refs,
                reasons=(
                    f"target {target_str} has {len(refs)} incoming static external reference(s): "
                    + ", ".join(reasons),
                ),
            )
        return DeletionSafetyDecision(
            allowed=True,
            status=DELETION_ALLOWED,
            incoming_references=(),
            reasons=(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this document to a JSON-compatible dictionary."""
        sorted_identifiers = {
            k: sorted(v) for k, v in sorted(self.external_identifiers.items())
        }
        sorted_incoming: dict[str, list[dict[str, Any]]] = {}
        for key in sorted(self.incoming_references.keys()):
            sorted_incoming[key] = [
                ref.to_dict()
                for ref in sorted(
                    self.incoming_references[key],
                    key=lambda r: (r.source_domain, r.source, r.source_file),
                )
            ]
        sorted_manifest = {
            path: self.source_manifest[path]
            for path in sorted(self.source_manifest.keys())
        }
        return {
            "schema_version": self.schema_version,
            "exporter_version": self.exporter_version,
            "external_identifiers": sorted_identifiers,
            "incoming_references": sorted_incoming,
            "source_manifest": sorted_manifest,
            "discovery_rules": list(self.discovery_rules),
            "fingerprint": self.fingerprint,
        }


def encode_reference_context(document: ReferenceContextDocument) -> str:
    """Serialize a reference-context document to deterministic JSON text."""
    payload = document.to_dict()
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def decode_reference_context(source: str | Mapping[str, Any]) -> ReferenceContextDocument:
    """Decode and validate a reference-context document."""
    if isinstance(source, str):
        try:
            data = json.loads(source)
        except json.JSONDecodeError as exc:
            raise ReferenceContextError(f"invalid reference-context JSON: {exc}") from exc
    elif isinstance(source, Mapping):
        data = source
    else:
        raise ReferenceContextError(f"expected str or Mapping, got {type(source)!r}")

    if not isinstance(data, Mapping):
        raise ReferenceContextError("reference context root must be a JSON object")

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ReferenceContextError("schema_version must be an integer")
    if schema_version != SCHEMA_VERSION:
        raise ReferenceContextError(f"unsupported schema_version {schema_version!r} (expected {SCHEMA_VERSION})")

    exporter_version = data.get("exporter_version")
    if not isinstance(exporter_version, int) or isinstance(exporter_version, bool):
        raise ReferenceContextError("exporter_version must be an integer")

    external_identifiers_raw = data.get("external_identifiers")
    if not isinstance(external_identifiers_raw, Mapping):
        raise ReferenceContextError("external_identifiers must be a mapping")
    external_identifiers: dict[str, tuple[str, ...]] = {}
    for key, values in external_identifiers_raw.items():
        if not isinstance(key, str) or not isinstance(values, (list, tuple)):
            raise ReferenceContextError(f"external identifier set {key!r} must be a list of strings")
        external_identifiers[key] = tuple(str(v) for v in values)

    incoming_raw = data.get("incoming_references")
    if not isinstance(incoming_raw, Mapping):
        raise ReferenceContextError("incoming_references must be a mapping")
    incoming_references: dict[str, tuple[IncomingReference, ...]] = {}
    for key, rows in incoming_raw.items():
        if not isinstance(key, str) or not isinstance(rows, (list, tuple)):
            raise ReferenceContextError(f"incoming references for {key!r} must be a list")
        incoming_references[key] = tuple(IncomingReference.from_dict(row) for row in rows)

    manifest_raw = data.get("source_manifest")
    if not isinstance(manifest_raw, Mapping):
        raise ReferenceContextError("source_manifest must be a mapping")
    source_manifest = {
        str(k): str(v) for k, v in manifest_raw.items()
    }

    rules_raw = data.get("discovery_rules", ())
    if not isinstance(rules_raw, (list, tuple)):
        raise ReferenceContextError("discovery_rules must be a list of strings")
    discovery_rules = tuple(str(r) for r in rules_raw)

    fingerprint = data.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ReferenceContextError("fingerprint must be a non-empty string")

    return ReferenceContextDocument(
        schema_version=schema_version,
        exporter_version=exporter_version,
        external_identifiers=external_identifiers,
        incoming_references=incoming_references,
        source_manifest=source_manifest,
        discovery_rules=discovery_rules,
        fingerprint=fingerprint,
    )


def check_reference_context_freshness(
    context: ReferenceContextDocument,
    file_hashes: Mapping[str, str],
    *,
    discovered_files: Iterable[str] | None = None,
) -> ReferenceContextFreshness:
    """Evaluate whether ``context`` matches the current filesystem state.

    Parameters
    ----------
    context : ReferenceContextDocument
        The decoded reference-context document.
    file_hashes : Mapping[str, str]
        Workspace-relative file path -> SHA-256 hex digest for currently present files.
    discovered_files : Iterable[str] | None
        All files currently discovered by allowlisted discovery rules in the workspace.
        If provided, membership additions/removals are detected.
    """
    reasons: list[str] = []

    # 1. Version compatibility
    if context.schema_version != SCHEMA_VERSION:
        return ReferenceContextFreshness(
            current=False,
            status=STATUS_INCOMPATIBLE,
            reasons=(f"schema_version {context.schema_version} differs from supported {SCHEMA_VERSION}",),
        )
    if context.exporter_version != EXPORTER_VERSION:
        return ReferenceContextFreshness(
            current=False,
            status=STATUS_INCOMPATIBLE,
            reasons=(f"exporter_version {context.exporter_version} differs from supported {EXPORTER_VERSION}",),
        )

    # 2. Check if any manifest file is missing
    missing_files = [path for path in context.source_manifest if path not in file_hashes]
    if missing_files:
        return ReferenceContextFreshness(
            current=False,
            status=STATUS_MISSING,
            reasons=tuple(f"manifest file missing: {path}" for path in sorted(missing_files)),
        )

    # 3. Check membership mismatch if discovered files are supplied
    if discovered_files is not None:
        discovered_set = frozenset(discovered_files)
        manifest_set = frozenset(context.source_manifest.keys())
        added = sorted(discovered_set - manifest_set)
        removed = sorted(manifest_set - discovered_set)
        if added or removed:
            membership_reasons = []
            if added:
                membership_reasons.append(f"new untracked source file(s) added: {', '.join(added)}")
            if removed:
                membership_reasons.append(f"tracked source file(s) removed: {', '.join(removed)}")
            return ReferenceContextFreshness(
                current=False,
                status=STATUS_MEMBERSHIP_MISMATCH,
                reasons=tuple(membership_reasons),
            )

    # 4. Check per-file content hashes
    changed_files = [
        path for path, expected in context.source_manifest.items()
        if file_hashes.get(path) != expected
    ]
    if changed_files:
        return ReferenceContextFreshness(
            current=False,
            status=STATUS_CHANGED,
            reasons=tuple(f"source file modified: {path}" for path in sorted(changed_files)),
        )

    # 5. Check aggregate dependency fingerprint
    expected_fingerprint = compute_dependency_fingerprint(
        context.source_manifest,
        context.schema_version,
        context.exporter_version,
        context.discovery_rules,
    )
    if context.fingerprint != expected_fingerprint:
        return ReferenceContextFreshness(
            current=False,
            status=STATUS_CHANGED,
            reasons=(f"fingerprint mismatch: document has {context.fingerprint[:16]}..., expected {expected_fingerprint[:16]}...",),
        )

    return ReferenceContextFreshness(
        current=True,
        status=STATUS_CURRENT,
        reasons=(),
    )


def match_discovery_rule(path_str: str, pattern: str) -> bool:
    """Match a normalized relative path against a discovery rule pattern."""
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/") + "/"
        return path_str.startswith(prefix)
    return fnmatch.fnmatch(path_str, pattern)


def discover_external_sources(
    workspace_root: Path | str,
    discovery_rules: Iterable[str],
) -> list[str]:
    """Discover all external static source files in workspace according to discovery rules."""
    root = Path(workspace_root).resolve()
    discovered: set[str] = set()

    # Paths and patterns to explicitly exclude
    exclude_prefixes = (
        "content/maps/",
        "world/maps/data/",
        ".git/",
        ".worktrees/",
        ".venv/",
        ".codegraph/",
        "packages/map-core/tests/",
        "tests/",
    )

    def is_excluded(rel_str: str) -> bool:
        if any(rel_str.startswith(ex) for ex in exclude_prefixes):
            return True
        if "/tests/" in rel_str or rel_str.endswith(".pyc") or "/__pycache__/" in rel_str:
            return True
        if rel_str == "content/map-reference-context.json":
            return True
        return False

    for rule in discovery_rules:
        # Check if rule is a direct file
        rule_path = root / rule
        if rule_path.is_file():
            rel_str = rule.replace("\\", "/")
            if not is_excluded(rel_str):
                discovered.add(rel_str)
            continue

        # If rule contains glob wildcards
        matched = False
        for p in root.glob(rule):
            if p.is_file():
                rel_str = p.relative_to(root).as_posix()
                if not is_excluded(rel_str):
                    discovered.add(rel_str)
                    matched = True

        # If rule is a directory
        if not matched and rule_path.is_dir():
            for p in rule_path.rglob("*"):
                if p.is_file():
                    rel_str = p.relative_to(root).as_posix()
                    if not is_excluded(rel_str):
                        discovered.add(rel_str)

    return sorted(discovered)


def check_workspace_freshness(
    context: ReferenceContextDocument,
    workspace_root: Path | str,
) -> ReferenceContextFreshness:
    """Discover files, hash them from disk, and evaluate freshness without game imports."""
    root = Path(workspace_root).resolve()
    discovered = discover_external_sources(root, context.discovery_rules)

    file_hashes: dict[str, str] = {}
    for rel_path in discovered:
        p = root / rel_path
        if p.is_file():
            hasher = hashlib.sha256()
            hasher.update(p.read_bytes())
            file_hashes[rel_path] = hasher.hexdigest()

    # Also check if any manifest file exists on disk even if not discovered
    for manifest_path in context.source_manifest:
        if manifest_path not in file_hashes:
            p = root / manifest_path
            if p.is_file():
                hasher = hashlib.sha256()
                hasher.update(p.read_bytes())
                file_hashes[manifest_path] = hasher.hexdigest()

    return check_reference_context_freshness(
        context,
        file_hashes,
        discovered_files=discovered,
    )
