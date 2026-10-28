"""Authoritative static reference-context exporter.

Reads authoritative static declarations and registries (scene archetypes, quests,
service hosts, nations, titles, places, etc.) without querying or serializing
live database state, and generates content/map-reference-context.json deterministically.

Regenerate after adding, removing, or changing any external static registry entry,
quest definition, service host, or reference declaration::

    uv run --locked python -m tools.map_reference_context

``--check`` regenerates in memory and exits non-zero when the committed file
differs byte for byte.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from typing import Any, Sequence

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.reference_context import (
    EXPORTER_VERSION,
    SCHEMA_VERSION,
    IncomingReference,
    ReferenceContextDocument,
    compute_dependency_fingerprint,
    discover_external_sources,
    encode_reference_context,
)

#: Repository root directory.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: Default output path for the reference context artifact.
DEFAULT_OUTPUT_PATH = REPOSITORY_ROOT / "content" / "map-reference-context.json"

#: Standard discovery rules for discovering the external static source set.
DISCOVERY_RULES: tuple[str, ...] = (
    "world/lore/**/*.py",
    "world/quests/**/*.py",
    "world/rules/**/*.py",
    "world/rules/**/*.yaml",
    "tools/map_reference_context.py",
    "packages/map-core/elosern_map_core/reference_context.py",
)


def _bootstrap() -> None:
    """Initialize Django and Evennia environment in memory without database queries."""
    root = REPOSITORY_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    import evennia

    # portal_mode=True initializes Evennia API without starting the ServerSessionHandler
    # or launching the server database listener.
    evennia._init(portal_mode=True)
    from world.maps import runtime

    # Preview published world in memory so geography and settlement views resolve
    runtime.preview(runtime.compose())


def _find_place_source_file(place_key: str, repo_root: Path) -> str:
    """Identify the specific Python source file that authors a given place."""
    from world.lore.settlements import (
        places_altoria_lower,
        places_altoria_middle,
        places_altoria_upper,
        places_ciaran,
    )

    module_map = (
        (places_altoria_lower, "world/lore/settlements/places_altoria_lower.py"),
        (places_altoria_middle, "world/lore/settlements/places_altoria_middle.py"),
        (places_altoria_upper, "world/lore/settlements/places_altoria_upper.py"),
        (places_ciaran, "world/lore/settlements/places_ciaran.py"),
    )
    for mod, rel_path in module_map:
        if any(row.key == place_key for row in getattr(mod, "ROWS", ())):
            return rel_path
    return "world/lore/settlements/places.py"


def build_reference_context_document(repo_root: Path | None = None) -> ReferenceContextDocument:
    """Build the complete, deterministic reference-context document."""
    root = (repo_root or REPOSITORY_ROOT).resolve()

    from world.lore.elements import ELEMENT_REGISTRY
    from world.lore.magic import MAGIC_TIER_REGISTRY
    from world.lore.monsters import MONSTER_TIER_REGISTRY
    from world.lore.monster_species import MONSTER_SPECIES_REGISTRY
    from world.lore.nations import NATION_REGISTRY
    from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
    from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.lore.settlements.settlements import SETTLEMENT_REGISTRY
    from world.lore.settlements.shops import SHOP_REGISTRY
    from world.lore.titles import FIXED_TITLE_REGISTRY
    from world.lore.wilderness_regions import regions
    from world.quests.catalog import QUEST_CATALOG
    from world.rules.guild_config import validate_service_hosts

    # 1. External identifier sets
    external_identifiers: dict[str, tuple[str, ...]] = {
        "assortments": tuple(sorted(ASSORTMENT_REGISTRY.keys())),
        "elements": tuple(sorted(ELEMENT_REGISTRY.keys())),
        "magic_tiers": tuple(sorted(MAGIC_TIER_REGISTRY.keys())),
        "monster_species": tuple(sorted(MONSTER_SPECIES_REGISTRY.keys())),
        "monster_tiers": tuple(sorted(MONSTER_TIER_REGISTRY.keys())),
        "nations": tuple(sorted(NATION_REGISTRY.keys())),
        "quest_definitions": tuple(sorted(defn.key for defn in QUEST_CATALOG)),
        "races": tuple(sorted(RACE_REGISTRY.keys())),
        "scene_archetypes": tuple(sorted(SCENE_ARCHETYPE_REGISTRY.keys())),
        "service_hosts": tuple(sorted(host.host_key for host in validate_service_hosts())),
        "settlements": tuple(sorted(SETTLEMENT_REGISTRY.keys())),
        "shops": tuple(sorted(SHOP_REGISTRY.keys())),
        "subraces": tuple(sorted(SUBRACE_REGISTRY.keys())),
        "titles": tuple(sorted(FIXED_TITLE_REGISTRY.keys())),
        "wilderness_regions": tuple(sorted(regions().keys())),
    }

    # 2. External incoming static references pointing to map objects
    incoming_map: dict[str, list[IncomingReference]] = {}

    def add_incoming(ref: IncomingReference) -> None:
        from elosern_map_core.reference_context import canonical_target_key
        key = canonical_target_key(ref.target)
        incoming_map.setdefault(key, []).append(ref)

    # 2a. Places (places author the room join to permanent interior rooms)
    for place_key, place in sorted(PLACE_REGISTRY.items()):
        source_file = _find_place_source_file(place_key, root)
        add_incoming(
            IncomingReference(
                source=f"place:{place_key}",
                source_file=source_file,
                source_domain="places",
                target=place.room,
            )
        )

    # 2b. Service hosts (service hosts spawn in a place's interior room)
    for host in validate_service_hosts():
        spawn_room = getattr(host, "spawn_room", None)
        if spawn_room and spawn_room in PLACE_REGISTRY:
            place = PLACE_REGISTRY[spawn_room]
            add_incoming(
                IncomingReference(
                    source=f"service_host:{host.host_key}",
                    source_file="world/rules/guild_config/_hosts.py",
                    source_domain="service_hosts",
                    target=place.room,
                )
            )

    sorted_incoming = {
        key: tuple(
            sorted(
                rows,
                key=lambda r: (r.source_domain, r.source, r.source_file),
            )
        )
        for key, rows in sorted(incoming_map.items())
    }

    # 3. Transitive source closure and membership manifest
    discovered = set(discover_external_sources(root, DISCOVERY_RULES))

    # Also capture all repo-relative modules imported in sys.modules during export
    # that belong to the external static closure (world/lore, world/quests, world/rules, packages/map-core)
    for mod in list(sys.modules.values()):
        if mod and hasattr(mod, "__file__") and mod.__file__:
            try:
                mod_path = Path(mod.__file__).resolve().relative_to(root).as_posix()
            except (ValueError, RuntimeError):
                continue
            if (
                mod_path.startswith(("world/lore/", "world/quests/", "world/rules/", "packages/map-core/"))
                and "/tests/" not in mod_path
                and not mod_path.endswith((".pyc", ".pyo"))
                and not mod_path.startswith("content/maps/")
            ):
                if (root / mod_path).is_file():
                    discovered.add(mod_path)

    # Compute sha256 for all files in the source closure
    source_manifest: dict[str, str] = {}
    for rel_path in sorted(discovered):
        full_path = root / rel_path
        if full_path.is_file():
            hasher = hashlib.sha256()
            hasher.update(full_path.read_bytes())
            source_manifest[rel_path] = hasher.hexdigest()

    fingerprint = compute_dependency_fingerprint(
        source_manifest,
        SCHEMA_VERSION,
        EXPORTER_VERSION,
        DISCOVERY_RULES,
    )

    return ReferenceContextDocument(
        schema_version=SCHEMA_VERSION,
        exporter_version=EXPORTER_VERSION,
        external_identifiers=external_identifiers,
        incoming_references=sorted_incoming,
        source_manifest=source_manifest,
        discovery_rules=DISCOVERY_RULES,
        fingerprint=fingerprint,
    )


def export_reference_context_text(repo_root: Path | None = None) -> str:
    """Generate the deterministic reference-context JSON text."""
    doc = build_reference_context_document(repo_root)
    return encode_reference_context(doc)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the deterministic map reference-context index."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed file is stale or missing without writing",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="destination path for the generated index",
    )
    args = parser.parse_args(argv)

    _bootstrap()
    text = export_reference_context_text(REPOSITORY_ROOT)

    current_text = (
        args.output.read_text(encoding="utf-8") if args.output.exists() else None
    )

    if args.check:
        if current_text is None:
            print(
                f"{args.output} is missing; run: uv run --locked python -m tools.map_reference_context",
                file=sys.stderr,
            )
            return 1
        if current_text != text:
            print(
                f"{args.output} is stale; run: uv run --locked python -m tools.map_reference_context",
                file=sys.stderr,
            )
            return 1
        print(f"{args.output} is up to date")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
