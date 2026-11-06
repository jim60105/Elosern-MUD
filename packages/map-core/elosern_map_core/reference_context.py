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
* ``monster_spawns`` -- the read-only monster spawn section (:class:`MonsterSpawnSection`):
  ``zones`` (ecology zones with inclusive ``[x_min, x_max, y_min, y_max]`` cell
  rectangles, density and timing values and a weighted ``pool`` of compositions)
  and ``sites`` (manual sites with a kind from :data:`MONSTER_SITE_KINDS`, a
  cell ``coordinates`` pair and one composition). Every member row carries its
  variant and species keys and names, resolved at export; regions are named by
  key only. Rows sort by ``key``; pool and member rows keep their authored order.
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
SCHEMA_VERSION: int = 2

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

#: Closed site-kind vocabulary. Mirrors world.lore.monster_placement.MONSTER_SITE_KINDS;
#: a parity test holds them equal because the core may not import the game.
MONSTER_SITE_KINDS: tuple[str, ...] = ("camp", "nest", "boss_site", "stray", "encounter")

@dataclass(frozen=True, slots=True)
class GuardedExecutionResult:
    """The result of executing a destructive command or undo operation under reference guards."""

    executed: bool
    status: str
    reasons: tuple[str, ...] = ()
    incoming_references: tuple[IncomingReference, ...] = ()


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


def _exact_keys(data: Any, keys: Sequence[str], what: str) -> Mapping[str, Any]:
    """Return ``data`` when it is a mapping holding exactly ``keys``."""
    if not isinstance(data, Mapping):
        raise ReferenceContextError(f"{what} must be a mapping")
    actual = set(data.keys())
    expected = set(keys)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(str(key) for key in actual - expected)
        raise ReferenceContextError(f"{what} keys differ: missing {missing}, unknown {unknown}")
    return data


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReferenceContextError(f"{what} must be an integer")
    return value


def _string(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReferenceContextError(f"{what} must be a non-empty string")
    return value


def _boolean(value: Any, what: str) -> bool:
    if not isinstance(value, bool):
        raise ReferenceContextError(f"{what} must be a boolean")
    return value


def _rows(value: Any, what: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReferenceContextError(f"{what} must be a list")
    return value


_MEMBER_KEYS = ("variant_key", "variant_name_zh", "species_key", "species_name_zh", "minimum", "maximum")
_POOL_KEYS = ("composition_key", "weight", "members")
_ZONE_KEYS = (
    "key", "region_key", "rectangles", "lower_density", "upper_density", "cell_capacity",
    "wave_budget", "recovery_delay", "replenishment_interval", "pool",
)
_SITE_KEYS = (
    "key", "kind", "region_key", "coordinates", "capacity", "one_shot", "recover_after_ticks",
    "individual_name_zh", "composition_key", "members",
)


@dataclass(frozen=True, slots=True)
class MonsterSpawnMember:
    """One composition member: a variant with its species and a count range."""

    variant_key: str
    variant_name_zh: str
    species_key: str
    species_name_zh: str
    minimum: int
    maximum: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_key": self.variant_key,
            "variant_name_zh": self.variant_name_zh,
            "species_key": self.species_key,
            "species_name_zh": self.species_name_zh,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

    @classmethod
    def from_dict(cls, data: Any, what: str) -> MonsterSpawnMember:
        row = _exact_keys(data, _MEMBER_KEYS, what)
        minimum = _integer(row["minimum"], f"{what} minimum")
        maximum = _integer(row["maximum"], f"{what} maximum")
        if minimum > maximum:
            raise ReferenceContextError(f"{what} minimum {minimum} exceeds maximum {maximum}")
        return cls(
            variant_key=_string(row["variant_key"], f"{what} variant_key"),
            variant_name_zh=_string(row["variant_name_zh"], f"{what} variant_name_zh"),
            species_key=_string(row["species_key"], f"{what} species_key"),
            species_name_zh=_string(row["species_name_zh"], f"{what} species_name_zh"),
            minimum=minimum,
            maximum=maximum,
        )


def _members(value: Any, what: str) -> tuple[MonsterSpawnMember, ...]:
    return tuple(
        MonsterSpawnMember.from_dict(row, f"{what} member {index}")
        for index, row in enumerate(_rows(value, f"{what} members"))
    )


@dataclass(frozen=True, slots=True)
class MonsterPoolEntry:
    """One weighted composition in an ecology zone's pool."""

    composition_key: str
    weight: int
    members: tuple[MonsterSpawnMember, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "composition_key": self.composition_key,
            "weight": self.weight,
            "members": [member.to_dict() for member in self.members],
        }

    @classmethod
    def from_dict(cls, data: Any, what: str) -> MonsterPoolEntry:
        row = _exact_keys(data, _POOL_KEYS, what)
        weight = _integer(row["weight"], f"{what} weight")
        if weight <= 0:
            raise ReferenceContextError(f"{what} weight must be positive")
        return cls(
            composition_key=_string(row["composition_key"], f"{what} composition_key"),
            weight=weight,
            members=_members(row["members"], what),
        )


def _rectangle(value: Any, what: str) -> tuple[int, int, int, int]:
    bounds = _rows(value, what)
    if len(bounds) != 4:
        raise ReferenceContextError(f"{what} must hold four integers")
    x_min, x_max, y_min, y_max = (_integer(bound, what) for bound in bounds)
    if x_min > x_max or y_min > y_max:
        raise ReferenceContextError(f"{what} has a minimum above its maximum")
    return (x_min, x_max, y_min, y_max)


@dataclass(frozen=True, slots=True)
class MonsterZoneRow:
    """One ecology zone: inclusive cell rectangles and a weighted pool."""

    key: str
    region_key: str
    rectangles: tuple[tuple[int, int, int, int], ...]  # (x_min, x_max, y_min, y_max)
    lower_density: int
    upper_density: int
    cell_capacity: int
    wave_budget: int
    recovery_delay: int
    replenishment_interval: int
    pool: tuple[MonsterPoolEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "region_key": self.region_key,
            "rectangles": [list(rectangle) for rectangle in self.rectangles],
            "lower_density": self.lower_density,
            "upper_density": self.upper_density,
            "cell_capacity": self.cell_capacity,
            "wave_budget": self.wave_budget,
            "recovery_delay": self.recovery_delay,
            "replenishment_interval": self.replenishment_interval,
            "pool": [entry.to_dict() for entry in self.pool],
        }

    @classmethod
    def from_dict(cls, data: Any) -> MonsterZoneRow:
        row = _exact_keys(data, _ZONE_KEYS, "monster zone")
        key = _string(row["key"], "monster zone key")
        what = f"monster zone {key!r}"
        rectangles = tuple(
            _rectangle(rectangle, f"{what} rectangle {index}")
            for index, rectangle in enumerate(_rows(row["rectangles"], f"{what} rectangles"))
        )
        if not rectangles:
            raise ReferenceContextError(f"{what} has no rectangles")
        return cls(
            key=key,
            region_key=_string(row["region_key"], f"{what} region_key"),
            rectangles=rectangles,
            lower_density=_integer(row["lower_density"], f"{what} lower_density"),
            upper_density=_integer(row["upper_density"], f"{what} upper_density"),
            cell_capacity=_integer(row["cell_capacity"], f"{what} cell_capacity"),
            wave_budget=_integer(row["wave_budget"], f"{what} wave_budget"),
            recovery_delay=_integer(row["recovery_delay"], f"{what} recovery_delay"),
            replenishment_interval=_integer(row["replenishment_interval"], f"{what} replenishment_interval"),
            pool=tuple(
                MonsterPoolEntry.from_dict(entry, f"{what} pool {index}")
                for index, entry in enumerate(_rows(row["pool"], f"{what} pool"))
            ),
        )


@dataclass(frozen=True, slots=True)
class MonsterSiteRow:
    """One manual monster site: a kind, a cell and one composition."""

    key: str
    kind: str
    region_key: str
    coordinates: tuple[int, int]
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None
    individual_name_zh: str | None
    composition_key: str
    members: tuple[MonsterSpawnMember, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind,
            "region_key": self.region_key,
            "coordinates": list(self.coordinates),
            "capacity": self.capacity,
            "one_shot": self.one_shot,
            "recover_after_ticks": self.recover_after_ticks,
            "individual_name_zh": self.individual_name_zh,
            "composition_key": self.composition_key,
            "members": [member.to_dict() for member in self.members],
        }

    @classmethod
    def from_dict(cls, data: Any) -> MonsterSiteRow:
        row = _exact_keys(data, _SITE_KEYS, "monster site")
        key = _string(row["key"], "monster site key")
        what = f"monster site {key!r}"
        kind = _string(row["kind"], f"{what} kind")
        if kind not in MONSTER_SITE_KINDS:
            raise ReferenceContextError(f"{what} kind {kind!r} is outside {MONSTER_SITE_KINDS}")
        coordinates = _rows(row["coordinates"], f"{what} coordinates")
        if len(coordinates) != 2:
            raise ReferenceContextError(f"{what} coordinates must hold two integers")
        x, y = (_integer(value, f"{what} coordinates") for value in coordinates)
        recover = row["recover_after_ticks"]
        name = row["individual_name_zh"]
        return cls(
            key=key,
            kind=kind,
            region_key=_string(row["region_key"], f"{what} region_key"),
            coordinates=(x, y),
            capacity=_integer(row["capacity"], f"{what} capacity"),
            one_shot=_boolean(row["one_shot"], f"{what} one_shot"),
            recover_after_ticks=None if recover is None else _integer(recover, f"{what} recover_after_ticks"),
            individual_name_zh=None if name is None else _string(name, f"{what} individual_name_zh"),
            composition_key=_string(row["composition_key"], f"{what} composition_key"),
            members=_members(row["members"], what),
        )


@dataclass(frozen=True, slots=True)
class MonsterSpawnSection:
    """The read-only monster spawn section: every ecology zone and manual site."""

    zones: tuple[MonsterZoneRow, ...] = ()
    sites: tuple[MonsterSiteRow, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "zones": [zone.to_dict() for zone in sorted(self.zones, key=lambda row: row.key)],
            "sites": [site.to_dict() for site in sorted(self.sites, key=lambda row: row.key)],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MonsterSpawnSection:
        section = _exact_keys(data, ("zones", "sites"), "monster_spawns")
        return cls(
            zones=tuple(MonsterZoneRow.from_dict(row) for row in _rows(section["zones"], "monster_spawns zones")),
            sites=tuple(MonsterSiteRow.from_dict(row) for row in _rows(section["sites"], "monster_spawns sites")),
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
    monster_spawns: MonsterSpawnSection = MonsterSpawnSection()

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
            "monster_spawns": self.monster_spawns.to_dict(),
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
        parsed_rows = []
        for row in rows:
            ref = IncomingReference.from_dict(row)
            actual_key = canonical_target_key(ref.target)
            if actual_key != key:
                raise ReferenceContextError(
                    f"incoming reference target {actual_key!r} disagrees with map key {key!r}"
                )
            parsed_rows.append(ref)
        incoming_references[key] = tuple(parsed_rows)

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

    monster_spawns = MonsterSpawnSection.from_dict(data.get("monster_spawns"))

    return ReferenceContextDocument(
        schema_version=schema_version,
        exporter_version=exporter_version,
        external_identifiers=external_identifiers,
        incoming_references=incoming_references,
        source_manifest=source_manifest,
        discovery_rules=discovery_rules,
        fingerprint=fingerprint,
        monster_spawns=monster_spawns,
    )


def execute_guarded_destructive_operation(
    context: ReferenceContextDocument,
    target: QualifiedRef | str,
    freshness: ReferenceContextFreshness,
    operation: Any,
) -> GuardedExecutionResult:
    """Execute an object-removing command or undo operation only if reference context permits.

    Evaluates execution-time reference context freshness and incoming static references.
    If context is unavailable or target is referenced, refuses execution without calling
    ``operation``, leaving disk and history state untouched.
    """
    decision = context.check_deletion_safety(target, freshness)
    if not decision.allowed:
        return GuardedExecutionResult(
            executed=False,
            status=decision.status,
            reasons=decision.reasons,
            incoming_references=decision.incoming_references,
        )
    operation()
    return GuardedExecutionResult(
        executed=True,
        status=DELETION_ALLOWED,
        reasons=(),
        incoming_references=(),
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
