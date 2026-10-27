"""Read-only authoring inspection entry point.

``python -m elosern_map_core schema`` prints the complete machine-readable
version-1 domain schema as JSON. ``python -m elosern_map_core inspect <root>``
discovers the supported sources below a workspace root, loads the candidate and
prints the sorted document identities, fingerprints and diagnostics as JSON.
It writes nothing: no file, cache or state is created in the inspected tree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .authoring import diagnose_world, load_authoring_world
from .diagnostics import AuthoringError, RuntimeRejection
from .schema import schema
from .sources import discover_source_documents


def _schema_json() -> str:
    return json.dumps(schema(), ensure_ascii=False, indent=2, sort_keys=True)


def _inspect(root: Path) -> tuple[int, str]:
    sources = discover_source_documents(root)
    try:
        world = load_authoring_world(sources)
    except AuthoringError as error:
        return 1, json.dumps(
            {
                "root": str(root),
                "status": "structure_rejected",
                "documents": [
                    {
                        "relative_path": source.relative_path,
                        "fingerprint": source.fingerprint,
                    }
                    for source in sources
                ],
                "diagnostics": [item.as_dict() for item in error.diagnostics],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    diagnostics = diagnose_world(world)
    return 0, json.dumps(
        {
            "root": str(root),
            "status": "loaded",
            "schema_version": world.documents[0].version if world.documents else None,
            "documents": [
                {
                    "relative_path": document.relative_path,
                    "kind": document.kind,
                    "id": document.identity,
                    "fingerprint": document.fingerprint,
                }
                for document in world.documents
            ],
            "diagnostics": [item.as_dict() for item in diagnostics],
            # Runtime readiness additionally needs the authoritative external
            # result and current partition artifact, which inspection does not
            # receive; it stays explicitly unknown here.
            "semantic_ready": not diagnostics,
            "runtime_ready": None,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="elosern-map-core",
        description="Read-only inspection of authored map documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("schema", help="print the machine-readable domain schema")
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="load the sources under a workspace root and print their state",
    )
    inspect_parser.add_argument("root", type=Path)
    arguments = parser.parse_args(argv)

    if arguments.command == "schema":
        print(_schema_json())
        return 0
    try:
        status, output = _inspect(arguments.root)
    except (AuthoringError, RuntimeRejection) as error:  # pragma: no cover - defensive
        print(
            json.dumps(
                {"status": "rejected", "diagnostics": [item.as_dict() for item in error.diagnostics]},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(output)
    return status


__all__ = ["main"]
