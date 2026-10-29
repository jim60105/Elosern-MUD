"""One explicit game load/adopt entry point for the whole authored map world.

Every static map authority is discovered YAML (``content/maps/continent.yaml``,
``locations.yaml``, ``districts.yaml``, ``settlements/*.yaml`` and
``interiors/*.yaml``). This module is the single composition root that

1. reads and structurally validates the complete source set with
   ``elosern_map_core`` (``load_authoring_world``),
2. composes each game-facing snapshot from that *one* candidate set,
3. runs the authoritative game-side checks — settlement/location joins, the
   static-reference closure over the candidate's own bindings, the service
   room joins, the registered scene catalog, the quest destination bindings and
   the district diagnostics — so nothing is approved against the previously
   published world,
4. requires the committed district partition to describe these exact inputs,
   and
5. only then installs one immutable :class:`MapWorld` bundle.

Publication is all-or-nothing: a rejected candidate raises and leaves the
previous bundle, the persistent world and the process caches exactly as they
were. :func:`adopt` keeps the bundle it replaced *pending* until the persistent
interior synchronization (:func:`synchronize`) commits, so a failed
synchronization restores the pre-adoption bundle instead of pairing new
registries with half-converged rooms.

:func:`compose` exposes steps 1-3 alone for an offline producer (the partition
generator) that must read a validated candidate *without* requiring the
artifact it is about to write; it never claims a runtime partition gate and
publishes no runtime snapshot.

Nothing here loads or validates at import time.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from elosern_map_core.authoring import (
    EXTERNAL_RESULT_VERSION,
    AuthoringError,
    AuthoringWorld,
    AuthoritativeExternalResult,
    RuntimeMapSnapshot,
    RuntimeRejection,
    compile_runtime,
    load_authoring_world,
)
from elosern_map_core.documents import QualifiedRef
from elosern_map_core.partition_codec import PartitionFreshness, partition_freshness
from elosern_map_core.sources import SourceDocument, discover_source_documents

from world.maps.interiors import InteriorError, InteriorSnapshot, build_interiors
from world.maps.map_data import SettlementError, SettlementSnapshot, build_settlements

__all__ = [
    "ComposedWorld",
    "MapWorld",
    "MapWorldError",
    "MapWorldNotLoaded",
    "adopt",
    "commit_adoption",
    "clear_published_world",
    "compose",
    "compose_settlements",
    "current",
    "ensure_published",
    "is_published",
    "preview",
    "publish",
    "rollback_adoption",
    "synchronize",
]

#: The repository root the shipped documents are discovered from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class MapWorldError(ValueError):
    """A map candidate cannot be adopted; ``problems`` names every defect."""

    def __init__(self, problems) -> None:
        self.problems = tuple(problems)
        super().__init__("invalid map world:\n" + "\n".join(self.problems))


class MapWorldNotLoaded(RuntimeError):
    """A consumer read the map world before any bundle was published."""


@dataclass(frozen=True, slots=True)
class MapWorld:
    """The complete map world: one immutable bundle of four domain views."""

    geography: Any
    settlements: SettlementSnapshot
    districts: Any
    interiors: InteriorSnapshot
    #: The core runtime surface — present only for an adopted world, whose
    #: external result and partition freshness were both accepted.
    snapshot: RuntimeMapSnapshot | None
    partition: PartitionFreshness | None

    @property
    def identity(self) -> str:
        """A stable digest of the four authored domains this bundle carries."""

        digest = hashlib.sha256()
        for part in (
            self.settlements.identity,
            self.geography.identity,
            self.districts.identity,
            self.interiors.identity,
        ):
            digest.update(part.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ComposedWorld:
    """A fully composed, fully game-checked world that is not yet gated/published."""

    world: AuthoringWorld
    geography: Any
    settlements: SettlementSnapshot
    districts: Any
    interiors: InteriorSnapshot
    #: The candidate's own static declaration families and bindings.
    static: Any

    @property
    def map_world(self) -> MapWorld:
        return MapWorld(
            geography=self.geography,
            settlements=self.settlements,
            districts=self.districts,
            interiors=self.interiors,
            snapshot=None,
            partition=None,
        )


def _read_sources(root: str | Path | None) -> tuple[SourceDocument, ...]:
    base = Path(root) if root is not None else REPOSITORY_ROOT
    return tuple(discover_source_documents(base))


def _service_problems(interiors: InteriorSnapshot) -> list[str]:
    """Every service record must validate and join a room the candidate supplies."""

    from world.lore.settlements.places import PLACE_REGISTRY, validate_place_registry

    problems: list[str] = []
    try:
        validate_place_registry(PLACE_REGISTRY)
    except ValueError as error:
        problems.append(str(error))
    for key, place in PLACE_REGISTRY.items():
        reference: QualifiedRef = place.room
        authored = interiors.rooms.get(key)
        if authored is None:
            problems.append(
                f"place {key}: joins interior room {key!r}, which no interior "
                "document authors"
            )
            continue
        if reference.map_id is not None and reference.map_id != authored.interior_id:
            problems.append(
                f"place {key}: room is authored by interior "
                f"{authored.interior_id!r}, not {reference.map_id!r}"
            )
    return problems


def _quest_problems(settlements: SettlementSnapshot, geography) -> list[str]:
    """Every authored quest destination must resolve in the candidate world."""

    from world.quests.catalog import QUEST_CATALOG
    from world.quests.definitions import (
        QuestDefinitionError,
        QuestLocationBindings,
        validate_definition,
    )

    bindings = QuestLocationBindings(
        anchor_keys=frozenset(settlements.anchor_placements),
        grid_map_keys=frozenset(settlements.graphs),
        region_keys=frozenset(geography.regions),
    )
    problems: list[str] = []
    for definition in QUEST_CATALOG:
        try:
            validate_definition(definition, bindings=bindings)
        except QuestDefinitionError as error:
            problems.append(str(error))
    return problems


def partition_freshness_for(world: AuthoringWorld) -> PartitionFreshness:
    """The committed artifact's freshness against this candidate's inputs."""

    from world.maps import district_partition

    return partition_freshness(
        district_partition.artifact_metadata(), world.partition_signature
    )


def compose_settlements(root: str | Path | None = None) -> SettlementSnapshot:
    """Compose one settlement candidate from an explicit root, publishing nothing.

    This reads only the documents a settlement candidate depends on (its own
    documents, the locations and the continent frame), so a caller can check a
    candidate source directory without supplying the whole world; runtime
    adoption still composes every domain through :func:`compose`.
    """

    from elosern_map_core.codec import parse_document
    from elosern_map_core.sources import discover_source_paths, read_source_document

    base = Path(root) if root is not None else REPOSITORY_ROOT
    paths = tuple(
        path
        for path in discover_source_paths(base)
        if path.startswith("content/maps/settlements/")
    )
    if not paths:
        raise MapWorldError([f"no settlement documents are discoverable under {base}"])
    settlements = [read_source_document(base, path) for path in paths]
    locations_source = read_source_document(base, "content/maps/locations.yaml")
    continent_source = read_source_document(base, "content/maps/continent.yaml")
    continent = parse_document(
        continent_source.relative_path, continent_source.text
    ).document
    locations = parse_document(
        locations_source.relative_path, locations_source.text
    ).document
    documents = {}
    fingerprints = {}
    for source in settlements:
        parsed = parse_document(source.relative_path, source.text)
        documents[parsed.identity] = parsed.document
        fingerprints[source.relative_path] = source.fingerprint
    fingerprints[locations_source.relative_path] = locations_source.fingerprint
    return build_settlements(
        documents,
        locations,
        frame_cells=continent.terrain.frame_cells,
        fingerprints=fingerprints,
    )


def _uninstall() -> None:
    """Forget the published world in every map reader (the not-loaded state)."""

    from world.lore import map_districts
    from world.maps import geography, interiors, map_data

    geography._PUBLISHED = None
    map_data._PUBLISHED = None
    map_districts._PUBLISHED = None
    interiors._PUBLISHED = None
    global _BUNDLE
    _BUNDLE = None


def compose(root: str | Path | None = None) -> ComposedWorld:
    """Read, compose and game-check one complete candidate (nothing published).

    This is steps 1-3 of the adoption: every fallible composition and every
    authoritative game-side check, but no external-result attestation and no
    partition/freshness gate. Runtime adoption must still call :func:`adopt`.
    """

    from world.lore import map_districts
    from world.maps import geography

    sources = _read_sources(root)
    try:
        world = load_authoring_world(sources)
    except AuthoringError as error:
        raise MapWorldError(item.message for item in error.diagnostics) from error

    problems: list[str] = [item.message for item in world.diagnostics]
    settlements: SettlementSnapshot | None = None
    geography_snapshot = None
    interiors: InteriorSnapshot | None = None
    districts = None

    def _fingerprints(*prefixes: str) -> dict[str, str]:
        """The candidate's own source fingerprints for one composed domain."""

        return {
            path: fingerprint
            for path, fingerprint in world.fingerprints.items()
            if path in prefixes or any(path.startswith(prefix) for prefix in prefixes)
        }

    settlement_sources = _fingerprints("content/maps/settlements/")
    settlement_sources["content/maps/locations.yaml"] = world.fingerprints[
        "content/maps/locations.yaml"
    ]
    interior_sources = _fingerprints("content/maps/interiors/")
    district_sources = _fingerprints("content/maps/districts.yaml")

    try:
        settlements = build_settlements(
            world.settlements,
            world.locations,
            frame_cells=world.continent.terrain.frame_cells,
            fingerprints=settlement_sources,
        )
    except SettlementError as error:
        problems.extend(error.problems)
    try:
        interiors = build_interiors(world.interiors, fingerprints=interior_sources)
    except InteriorError as error:
        problems.extend(error.problems)
    if settlements is not None:
        try:
            geography_snapshot = geography.build_geography(
                world.continent,
                world.locations,
                settlements,
                fingerprints=_fingerprints("content/maps/continent.yaml")
                | {"content/maps/locations.yaml": world.fingerprints[
                    "content/maps/locations.yaml"
                ]},
            )
        except geography.GeographyError as error:
            problems.extend(error.problems)
        else:
            try:
                districts = map_districts.build_districts(
                    world.districts,
                    terrain=map_districts.candidate_terrain(
                        geography_snapshot, settlements
                    ),
                    index=world.reference_index,
                    fingerprints=district_sources,
                )
            except map_districts.DistrictError as error:
                problems.extend(item.message for item in error.diagnostics)

    if problems:
        raise MapWorldError(problems)
    assert settlements is not None and interiors is not None
    assert geography_snapshot is not None and districts is not None
    if districts.diagnostics:
        raise MapWorldError(item.message for item in districts.diagnostics)

    from world.maps.static_references import (
        StaticReferenceError,
        static_world_for_candidate,
        validate_static_world,
    )

    static = static_world_for_candidate(
        world=world,
        settlements=settlements,
        interiors=interiors,
        districts=districts,
    )
    try:
        validate_static_world(static)
    except StaticReferenceError as error:
        raise MapWorldError(error.problems) from error
    service_problems = _service_problems(interiors)
    if service_problems:
        raise MapWorldError(service_problems)
    quest_problems = _quest_problems(settlements, geography_snapshot)
    if quest_problems:
        raise MapWorldError(quest_problems)

    return ComposedWorld(
        world=world,
        geography=geography_snapshot,
        settlements=settlements,
        districts=districts,
        interiors=interiors,
        static=static,
    )


def load_candidate(root: str | Path | None = None) -> MapWorld:
    """Compose one candidate and accept it only with external + partition evidence."""

    composed = compose(root)
    world = composed.world
    # ``compose`` already ran every authoritative game-side check against this
    # candidate's own bindings; the attestation records that evidence and binds
    # it to the exact source set it was produced for.
    external = AuthoritativeExternalResult(
        version=EXTERNAL_RESULT_VERSION,
        fingerprint=composed.static.fingerprint,
        world_fingerprint=world.fingerprint,
        valid=True,
    )
    freshness = partition_freshness_for(world)
    try:
        snapshot = compile_runtime(world, external, freshness)
    except RuntimeRejection as error:
        raise MapWorldError(item.message for item in error.diagnostics) from error
    return MapWorld(
        geography=composed.geography,
        settlements=composed.settlements,
        districts=composed.districts,
        interiors=composed.interiors,
        snapshot=snapshot,
        partition=freshness,
    )


_BUNDLE: MapWorld | None = None
#: The bundle an uncommitted adoption replaced; restored when its persistent
#: synchronization fails, and dropped when it commits.
_PENDING: MapWorld | None = None
_PENDING_SETTLED: bool = True


def _install(world: MapWorld) -> None:
    """Point every map reader at one bundle (the single publication step)."""

    from world.lore import map_districts
    from world.maps import geography, interiors, map_data

    geography._install(world.geography)
    map_data._install(world.settlements)
    map_districts._install(world.districts)
    interiors._install(world.interiors)
    global _BUNDLE
    _BUNDLE = world


def publish(world: MapWorld) -> MapWorld:
    """Install one already-composed bundle and settle it (fixtures, offline tools).

    This is the same single-pointer installation :func:`adopt` uses, exposed for
    a deliberate synthetic world or an offline producer; it composes and
    validates nothing, so a caller that has not validated is its own defect.
    Nothing stays pending, because no runtime partition gate was claimed.
    """

    if not isinstance(world, MapWorld):
        raise TypeError("publish() requires a MapWorld")
    _install(world)
    global _PENDING, _PENDING_SETTLED
    _PENDING = None
    _PENDING_SETTLED = True
    return world


def preview(composed: ComposedWorld) -> MapWorld:
    """Install one composed candidate for an offline producer, ungated.

    The partition generator must read a validated candidate *before* the
    artifact it is about to write exists, so this publishes the four domain
    views without an external result or a freshness claim: the installed
    bundle carries no runtime snapshot and can never be mistaken for an
    adopted world.
    """

    if not isinstance(composed, ComposedWorld):
        raise TypeError("preview() requires a ComposedWorld")
    return publish(composed.map_world)


def adopt(root: str | Path | None = None) -> MapWorld:
    """Accept and publish one complete bundle; a rejection changes nothing.

    The replaced bundle stays pending until :func:`synchronize` commits, so a
    failed persistent synchronization restores it.
    """

    from world.maps.static_references import validate_static_references

    global _BUNDLE, _PENDING, _PENDING_SETTLED

    world = load_candidate(root)
    # Two distinct values: the bundle this install replaces (undone verbatim if
    # the installation is rejected) and the last *synchronized* world (the
    # rollback baseline a later synchronization failure restores). A second
    # adoption before synchronization must not replace that baseline.
    previous = _BUNDLE
    baseline = _BUNDLE if _PENDING_SETTLED else _PENDING
    _install(world)
    try:
        # The game-side declaration registries (city gates, anchor placements,
        # wilderness gates, place joins, district landmarks, grid art) are read
        # through the bundle this process now holds: reject a world whose own
        # registries disagree before anything is persisted, and leave the
        # previously published world exactly as it was.
        validate_static_references()
    except BaseException:
        if previous is None:
            _uninstall()
        else:
            _install(previous)
        raise
    _PENDING = baseline
    _PENDING_SETTLED = False
    return world


def synchronize(root: str | Path | None = None) -> MapWorld:
    """Adopt (when needed) and converge the persistent map world.

    The starting room, every settlement graph and every permanent interior
    converge inside ONE transaction: a candidate that moves a node and then
    fails on an interior rolls its coordinate moves back too, so the persistent
    baseline can never disagree with the bundle. A failure also evicts the
    process caches the batch touched and restores the bundle the adoption
    replaced; only a successful run commits the adoption.
    """

    from django.db import transaction

    from world.maps import bootstrap

    world = ensure_published(root)
    try:
        with transaction.atomic():
            bootstrap.sync_limbo()
            bootstrap.sync_grid()
            bootstrap.sync_interiors()
    except BaseException:
        # ``sync_interiors`` already evicted the objects its own batch touched;
        # this second eviction covers a failure inside the grid or limbo step.
        bootstrap._evict_batch_cache()
        rollback_adoption()
        raise
    commit_adoption()
    return world


def commit_adoption() -> None:
    """Mark the published bundle as synchronized (its predecessor is dropped)."""

    global _PENDING, _PENDING_SETTLED
    _PENDING = None
    _PENDING_SETTLED = True


def rollback_adoption() -> bool:
    """Restore the bundle the last uncommitted adoption replaced.

    Returns whether a rollback happened: a direct synchronization call with no
    pending adoption has nothing to restore.
    """

    global _PENDING, _PENDING_SETTLED, _BUNDLE
    if _PENDING_SETTLED:
        return False
    previous = _PENDING
    _PENDING = None
    _PENDING_SETTLED = True
    if previous is None:
        _uninstall()
        return True
    _install(previous)
    return True


def ensure_published(root: str | Path | None = None) -> MapWorld:
    """Publish the shipped world when this process has none yet.

    Only a composition root calls this: it establishes the world before any
    consumer reads it. Read-only accessors never load implicitly.
    """

    if _BUNDLE is None:
        return adopt(root)
    return _BUNDLE


def current() -> MapWorld:
    """The published map world.

    Raises :class:`MapWorldNotLoaded` instead of loading implicitly: every
    process entry point publishes explicitly before any read-only consumer runs.
    """

    world = _BUNDLE
    if world is None:
        raise MapWorldNotLoaded(
            "the map world is not loaded; adopt it with world.maps.runtime "
            "before using map consumers"
        )
    return world


def is_published() -> bool:
    """Whether a complete map bundle has been published in this process."""

    return _BUNDLE is not None


def clear_published_world():
    """Forget the published world and return the bundle it held."""

    previous = _BUNDLE
    global _PENDING, _PENDING_SETTLED
    _PENDING = None
    _PENDING_SETTLED = True
    _uninstall()
    return previous
