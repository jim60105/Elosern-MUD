"""Explicitly loaded continental geography and its immutable game views.

The authored source is ``content/maps/continent.yaml`` plus
``content/maps/locations.yaml``; ``elosern_map_core`` parses and validates the
documents and owns the deterministic terrain rules, while this module is the
one game-side adapter that

* reads the two canonical documents from an explicit root,
* composes the read-only game views (terrain rules, regions, harbor sites,
  location identity and geography) by joining map-owned fields with the
  untouched Python non-map lore, and
* validates every cross-domain join before it publishes a snapshot.

Publication is atomic: a failed candidate raises :class:`GeographyError` and
leaves the previously published snapshot exactly as it was. Derived state
(terrain column tables, waterway cells, search windows, national borders,
region flavours) belongs to the immutable snapshot's ``TerrainDefinition`` and
its ``cached_property`` values, so two independent worlds or a reload can never
observe each other's derivations.

Nothing here loads or validates at import time: the game composition root (and
tests) call :func:`load_and_publish`, and every read-only consumer goes through
:func:`current`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from elosern_map_core.codec import parse_document
from elosern_map_core.documents import ContinentDocument, LocationsDocument
from elosern_map_core.sources import fingerprint_text, read_source_document
from elosern_map_core.terrain import REGION_KEYS, TerrainDefinition

from world.lore.anchors import ANCHOR_LORE, Anchor, AnchorKind, GeographicAnchor
from world.lore.wilderness_regions import HarborSite, WildernessRegion

#: The repository root the shipped documents are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

CONTINENT_PATH = "content/maps/continent.yaml"
LOCATIONS_PATH = "content/maps/locations.yaml"

#: The only supported wilderness cell span for this continent. The mainland
#: polygon, the cell-centre arithmetic and the settlement anchor transform are
#: all one-kilometre declarations; a different authored scale would silently
#: disagree with them, so the adapter rejects it instead of accepting the
#: authoring schema's broader integer domain.
SUPPORTED_CELL_SIZE_KM = 1


class GeographyError(ValueError):
    """A geography candidate cannot be published.

    ``problems`` names every rejected join or declaration, in a deterministic
    order, so a caller can report the complete candidate failure at once.
    """

    def __init__(self, problems: tuple[str, ...] | list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(
            "invalid geography candidate:\n" + "\n".join(f"- {item}" for item in self.problems)
        )


class GeographyNotLoaded(RuntimeError):
    """A consumer read geography before any candidate was published."""


@dataclass(frozen=True, slots=True)
class GeographySnapshot:
    """One immutable, validated continental geography world.

    The two typed documents are retained because consumers (and the editor's
    external context) need authored identity and provenance; the composed
    mappings are the game-facing views.
    """

    continent: ContinentDocument
    locations: LocationsDocument
    terrain: TerrainDefinition
    regions: Mapping[str, WildernessRegion]
    harbor_sites: Mapping[str, HarborSite]
    anchors: Mapping[str, Anchor]
    anchor_geography: Mapping[str, GeographicAnchor]
    fingerprints: Mapping[str, str] = field(default_factory=dict)
    content_signature: str = ""

    @property
    def identity(self) -> str:
        """A stable digest of the authored source set this snapshot came from."""

        digest = hashlib.sha256()
        digest.update(self.content_signature.encode("utf-8"))
        digest.update(b"\0")
        for path in sorted(self.fingerprints):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(self.fingerprints[path].encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    @property
    def frame_cells(self) -> int:
        return self.terrain.frame_cells

    @property
    def cell_size_km(self) -> int:
        return self.continent.terrain.cell_size_km

    @property
    def mainland_boundary_km(self) -> tuple[tuple[int, int], ...]:
        return self.terrain.mainland_boundary_km

    @property
    def max_x(self) -> int:
        return self.terrain.max_x

    @property
    def max_y(self) -> int:
        return self.terrain.max_y

    @property
    def region_search_boxes(self) -> Mapping[str, tuple[int, int, int, int]]:
        return self.terrain.region_search_boxes


def _plain_data(value: Any) -> Any:
    """A JSON-serializable copy of one typed document's authored data."""

    if isinstance(value, Mapping):
        return {str(key): _plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_data(item) for item in value]
    return value


def _content_signature(
    continent: ContinentDocument, locations: LocationsDocument
) -> str:
    payload = json.dumps(
        [_plain_data(continent.data), _plain_data(locations.data)],
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _terrain_definition(continent: ContinentDocument) -> TerrainDefinition:
    terrain = continent.terrain
    return TerrainDefinition(
        frame_cells=terrain.frame_cells,
        mainland_boundary_km=terrain.mainland_boundary_km,
        forest_edge=terrain.forest_edge,
        waterway_routes={
            key: value.route for key, value in terrain.waterways.items()
        },
        waterway_fords={key: value.fords for key, value in terrain.waterways.items()},
        border_river_key=terrain.border_river_key,
        ridge_base_x=terrain.ridge_base_x,
        ridge_period=terrain.ridge_period,
        ridge_step=terrain.ridge_step,
        ridge_min_x=terrain.ridge_min_x,
        ridge_max_x=terrain.ridge_max_x,
        ridge_north_limit=terrain.ridge_north_limit_y,
        ridge_passes=terrain.ridge_passes,
        coastal_y_max=terrain.coastal_y_max,
        mountain_corridor_half_width=terrain.ridge_corridor_half_width,
        region_flavors={
            key: value.terrain_flavor_zh for key, value in continent.regions.items()
        },
    )


def _compose_regions(
    continent: ContinentDocument, problems: list[str]
) -> Mapping[str, WildernessRegion]:
    from world.lore.nations import NATION_REGISTRY
    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

    missing = sorted(REGION_KEYS - set(continent.regions))
    if missing:
        problems.append(
            f"the continent declares no terrain region for {missing}"
        )
    composed: dict[str, WildernessRegion] = {}
    for key, declaration in continent.regions.items():
        scene = declaration.scene_archetype
        if not scene:
            problems.append(f"region {key!r} declares no scene archetype")
        elif scene not in SCENE_ARCHETYPE_REGISTRY:
            problems.append(
                f"region {key!r} names unregistered scene archetype {scene!r}"
            )
        declared_nations = [
            name
            for name in (declaration.nation_key, *declaration.nominal_nation_keys)
            if name is not None
        ]
        for name in declared_nations:
            if name not in NATION_REGISTRY:
                problems.append(
                    f"region {key!r} names unknown nation {name!r}"
                )
        composed[key] = WildernessRegion(
            key,
            declaration.display_name_zh,
            declaration.nation_key,
            declaration.terrain_flavor_zh,
            declaration.nominal_nation_keys,
            scene,
        )
    return MappingProxyType(composed)


def _compose_locations(
    locations: LocationsDocument, problems: list[str]
) -> tuple[
    Mapping[str, Anchor], Mapping[str, GeographicAnchor]
]:
    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

    anchors: dict[str, Anchor] = {}
    geography: dict[str, GeographicAnchor] = {}
    for key, declaration in locations.locations.items():
        try:
            kind = AnchorKind(declaration.kind)
        except ValueError:
            problems.append(f"location {key!r} has unknown kind {declaration.kind!r}")
            continue
        scene = declaration.scene_archetype
        if scene is not None and scene not in SCENE_ARCHETYPE_REGISTRY:
            problems.append(
                f"location {key!r} names unregistered scene archetype {scene!r}"
            )
        lore = ANCHOR_LORE.get(key)
        anchors[key] = Anchor(
            key,
            kind,
            declaration.display_name_zh,
            lore.nation_key if lore is not None else None,
            lore.population if lore is not None else None,
            lore.floors if lore is not None else None,
            declaration.description,
        )
        geography[key] = GeographicAnchor(
            key, declaration.cell, declaration.geographic_constraint
        )
    for key in sorted(set(ANCHOR_LORE) - set(locations.locations)):
        problems.append(
            f"non-map lore row {key!r} joins no authored geographic location"
        )
    return MappingProxyType(anchors), MappingProxyType(geography)


def _compose_harbor_sites(
    continent: ContinentDocument, problems: list[str]
) -> Mapping[str, HarborSite]:
    sites: dict[str, HarborSite] = {}
    for key, declaration in continent.harbor_sites.items():
        sites[key] = HarborSite(
            key, declaration.display_name, declaration.cell, declaration.role
        )
    return MappingProxyType(sites)


def _validate_cells(snapshot_terrain: TerrainDefinition, **groups: Mapping[str, Any]) -> list[str]:
    from elosern_map_core.terrain import is_land_cell, is_within_frame

    problems: list[str] = []
    for label, entries in groups.items():
        for key, cell in entries.items():
            if not is_within_frame(snapshot_terrain.frame_cells, cell):
                problems.append(f"{label} {key!r} cell {cell!r} is outside the frame")
            elif not is_land_cell(snapshot_terrain, cell):
                problems.append(f"{label} {key!r} cell {cell!r} is not on the mainland")
    return problems


def _validate_game_joins(
    snapshot: GeographySnapshot,
) -> list[str]:
    """Every cross-domain join this geography holds, checked before publication.

    The non-map catalogs keep their own ownership; they are read here only to
    prove their stable keys still resolve against the published geography.
    """

    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    from world.lore.monster_placement import (
        AMBIENT_PLACEMENT_REGISTRY,
        MONSTER_SITE_REGISTRY,
    )
    from world.lore.monster_species import MONSTER_SPECIES_REGISTRY
    from world.lore.nations import NATION_REGISTRY
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.rules.travel_cost import validate_wilderness_region_coverage

    problems: list[str] = []
    regions = set(snapshot.regions)
    anchors = snapshot.anchors
    for key, nation in sorted(NATION_REGISTRY.items()):
        capital_key = getattr(nation, "capital_anchor_key", None)
        anchor = anchors.get(capital_key)
        if anchor is None:
            problems.append(
                f"nation {key!r} capital anchor {capital_key!r} joins no location"
            )
        elif anchor.kind is not AnchorKind.CAPITAL:
            problems.append(
                f"nation {key!r} capital anchor {capital_key!r} is not a capital"
            )
    for key in sorted(SETTLEMENT_REGISTRY):
        if key not in anchors:
            problems.append(f"settlement {key!r} joins no geographic location")
    for key in sorted(ANCHOR_PLACEMENT_REGISTRY):
        if key not in anchors:
            problems.append(f"anchor placement {key!r} joins no geographic location")
    for key, entry in sorted(WILDERNESS_ENTRY_REGISTRY.items()):
        if getattr(entry, "anchor_key", None) not in anchors:
            problems.append(
                f"wilderness entry {key!r} joins no geographic location "
                f"({entry.anchor_key!r})"
            )
    for key, district in sorted(MAP_DISTRICT_REGISTRY.items()):
        region_key = getattr(district, "region_key", None)
        if region_key is not None and region_key not in regions:
            problems.append(
                f"district {key!r} names unknown terrain region {region_key!r}"
            )
    for key, species in sorted(MONSTER_SPECIES_REGISTRY.items()):
        for tag in getattr(species, "habitat_tags", ()):
            if tag not in regions:
                problems.append(
                    f"monster species {key!r} habitat tag {tag!r} is not a terrain region"
                )
    for key, rule in sorted(AMBIENT_PLACEMENT_REGISTRY.items()):
        if getattr(rule, "region_key", None) not in regions:
            problems.append(
                f"ambient placement {key!r} names unknown terrain region {rule.region_key!r}"
            )
    for key, site in sorted(MONSTER_SITE_REGISTRY.items()):
        if getattr(site, "region_key", None) not in regions:
            problems.append(
                f"monster site {key!r} names unknown terrain region {site.region_key!r}"
            )
    try:
        validate_wilderness_region_coverage(regions)
    except ValueError as error:
        problems.append(str(error))
    return problems


def build_geography(
    continent: ContinentDocument,
    locations: LocationsDocument,
    *,
    fingerprints: Mapping[str, str] | None = None,
) -> GeographySnapshot:
    """Validate one candidate and compose its immutable game views.

    Every fallible derivation a published consumer needs (terrain tables,
    national borders, search windows, region flavours, cross-domain joins) is
    completed here; nothing is deferred into the published snapshot.
    """

    problems: list[str] = []
    if continent.terrain.cell_size_km != SUPPORTED_CELL_SIZE_KM:
        problems.append(
            f"{CONTINENT_PATH} declares cell_size_km "
            f"{continent.terrain.cell_size_km}; only "
            f"{SUPPORTED_CELL_SIZE_KM} km cells are supported"
        )
    try:
        terrain = _terrain_definition(continent)
    except (TypeError, ValueError) as error:
        raise GeographyError([f"the authored terrain inputs are inconsistent: {error}"]) from error
    regions = _compose_regions(continent, problems)
    anchors, anchor_geography = _compose_locations(locations, problems)
    harbor_sites = _compose_harbor_sites(continent, problems)
    problems.extend(
        _validate_cells(
            terrain,
            locations={
                key: value.cell for key, value in anchor_geography.items()
            },
            harbor_sites={key: value.cell for key, value in harbor_sites.items()},
        )
    )
    if set(anchors) & set(harbor_sites):
        problems.append(
            "a reserved harbor site and a geographic location share an identity: "
            f"{sorted(set(anchors) & set(harbor_sites))}"
        )
    # Gateway footprints, anchors and approaches are terrain-dependent, so the
    # candidate's own frame and walkability must be checked here: publication
    # must never precede a rejection that a later sync would raise.
    from elosern_map_core.terrain import is_walkable_cell as _core_is_walkable
    from world.lore.wilderness_entry import validate_wilderness_entries

    try:
        validate_wilderness_entries(
            bounds=(terrain.max_x, terrain.max_y),
            walkable=lambda cell: _core_is_walkable(terrain, cell),
        )
    except ValueError as error:
        problems.append(str(error))
    try:
        snapshot = GeographySnapshot(
            continent=continent,
            locations=locations,
            terrain=terrain,
            regions=regions,
            harbor_sites=harbor_sites,
            anchors=anchors,
            anchor_geography=anchor_geography,
            fingerprints=MappingProxyType(dict(fingerprints or {})),
            content_signature=_content_signature(continent, locations),
        )
        # Force the fallible derived views an immutable snapshot must already
        # hold, so publication never defers a rejection to the first reader.
        snapshot.terrain.national_borders
        snapshot.terrain.region_search_boxes
        snapshot.terrain.waterway_cells
    except (TypeError, ValueError) as error:
        raise GeographyError(
            [*problems, f"the authored terrain derivation failed: {error}"]
        ) from error
    problems.extend(_validate_game_joins(snapshot))
    if problems:
        raise GeographyError(problems)
    return snapshot


def parse_geography_documents(
    continent_text: str, locations_text: str
) -> tuple[ContinentDocument, LocationsDocument, dict[str, str]]:
    """Parse both canonical documents from explicit text (no file access)."""

    continent = parse_document(CONTINENT_PATH, continent_text)
    locations = parse_document(LOCATIONS_PATH, locations_text)
    fingerprints = {
        CONTINENT_PATH: fingerprint_text(continent_text),
        LOCATIONS_PATH: fingerprint_text(locations_text),
    }
    return continent.document, locations.document, fingerprints


def load_geography(root: str | Path | None = None) -> GeographySnapshot:
    """Read, validate and compose the shipped geography from ``root``."""

    base = Path(root) if root is not None else REPOSITORY_ROOT
    continent_source = read_source_document(base, CONTINENT_PATH)
    locations_source = read_source_document(base, LOCATIONS_PATH)
    continent = parse_document(continent_source.relative_path, continent_source.text)
    locations = parse_document(locations_source.relative_path, locations_source.text)
    return build_geography(
        continent.document,
        locations.document,
        fingerprints={
            continent_source.relative_path: continent_source.fingerprint,
            locations_source.relative_path: locations_source.fingerprint,
        },
    )


_PUBLISHED: GeographySnapshot | None = None


def publish(snapshot: GeographySnapshot) -> GeographySnapshot:
    """Replace the process geography atomically and return the new snapshot."""

    global _PUBLISHED
    if not isinstance(snapshot, GeographySnapshot):
        raise TypeError("publish() requires a GeographySnapshot")
    _PUBLISHED = snapshot
    return snapshot


def load_and_publish(root: str | Path | None = None) -> GeographySnapshot:
    """Load the shipped geography and publish it; a failure keeps the baseline."""

    return publish(load_geography(root))


def ensure_published(root: str | Path | None = None) -> GeographySnapshot:
    """Publish the shipped geography when a composition root has none yet.

    Only bootstrap/synchronization entry points call this: they are the
    explicit composition roots that establish the world before any consumer
    reads it. Read-only accessors never load implicitly.
    """

    if _PUBLISHED is None:
        return load_and_publish(root)
    return _PUBLISHED


def current() -> GeographySnapshot:
    """The published geography.

    Raises :class:`GeographyNotLoaded` instead of loading implicitly: every
    process entry point publishes explicitly before any read-only consumer
    runs, and a validator must never inspect the published world by accident.
    """

    snapshot = _PUBLISHED
    if snapshot is None:
        raise GeographyNotLoaded(
            "continental geography is not loaded; call "
            "world.maps.geography.load_and_publish() before using map consumers"
        )
    return snapshot


def is_published() -> bool:
    """Whether a geography snapshot has been published in this process."""

    return _PUBLISHED is not None


__all__ = [
    "CONTINENT_PATH",
    "GeographyError",
    "GeographyNotLoaded",
    "GeographySnapshot",
    "LOCATIONS_PATH",
    "REPOSITORY_ROOT",
    "SUPPORTED_CELL_SIZE_KM",
    "build_geography",
    "current",
    "ensure_published",
    "is_published",
    "load_and_publish",
    "load_geography",
    "parse_geography_documents",
    "publish",
]
