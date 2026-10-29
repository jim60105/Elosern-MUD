"""One-shot confined read of the workspace for offline map capture.

The capture command never starts the editor service. This module owns only the
capture policy on top of the shared source/layout/core load in
:mod:`elosern_map_editor.snapshot`:

* it refuses source and layout structure failures that the interactive editor
  reports but keeps (a partial layout projection is editor leniency);
* it resolves the requested map identity against the loaded world instead of
  silently rendering another map;
* it admits partition outlines only for a continent view that shows the
  ``partition`` layer, decoding them through the shared core codec and checking
  their freshness against the world this invocation loaded.

Nothing here writes a source, layout, generated artifact, reference index or
fallback position, and nothing here runs a generator or starts the game.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from elosern_map_core import (
    PartitionDocumentError,
    decode_partition,
    diagnose_world,
    is_land_cell,
    partition_freshness,
    read_partition_metadata,
    terrain_definition,
)
from elosern_map_core.diagnostics import (
    EXTERNAL,
    WARNING,
    Diagnostic,
    sorted_diagnostics,
)

from .config import Limits
from .confinement import (
    PARTITION_ARTIFACT,
    REFERENCE_CONTEXT_ARTIFACT,
    ConfinedWorkspace,
    ConfinementError,
)
from .snapshot import load_sources, read_external_context

#: The map views a capture may request.
VIEWS = ("continent", "settlement", "interior")
#: The layer whose visibility decides whether partition output is required.
PARTITION_LAYER = "partition"
#: How a caller recovers from refused partition output. Capture never acts on it.
REGENERATE_GUIDANCE = (
    "regenerate the partition with `uv run --locked --project tools/map-editor python "
    ".agents/skills/map-data-authoring/scripts/regenerate_partition.py`, or hide the layer "
    "with `--hide partition`"
)


class CaptureSnapshotError(ValueError):
    """A capture snapshot was refused; ``code`` is the stable machine reason."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        diagnostics: Iterable[dict[str, Any]] = (),
        guidance: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        #: A finer machine reason inside ``code`` (the partition refusal kind).
        self.reason = reason
        self.guidance = guidance
        self.diagnostics = tuple(diagnostics)
        super().__init__(f"{code}: {message}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "reason": self.reason,
            "message": self.message,
            "guidance": self.guidance,
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


def _partition_error(reason: str, message: str) -> CaptureSnapshotError:
    return CaptureSnapshotError(
        "partition_unavailable", message, guidance=REGENERATE_GUIDANCE, reason=reason
    )


def _requested_identity(view: str, map_id: object) -> str | None:
    """The requested document id, checked against the view's argument shape."""

    if view == "continent":
        if map_id is not None:
            raise CaptureSnapshotError(
                "invalid_map_id", "a continent capture names no map document"
            )
        return None
    if not isinstance(map_id, str) or not map_id:
        raise CaptureSnapshotError(
            "invalid_map_id", f"a {view} capture requires the id of one authored document"
        )
    return map_id


def _normalised_layers(hidden_layers: Iterable[str]) -> tuple[str, ...]:
    """The hidden layer names as one sorted, de-duplicated tuple."""

    try:
        names = tuple(hidden_layers)
    except TypeError:
        raise CaptureSnapshotError(
            "invalid_hidden_layers", "hidden layers must be an iterable of layer names"
        ) from None
    for name in names:
        if not isinstance(name, str) or not name:
            raise CaptureSnapshotError(
                "invalid_hidden_layers", "a hidden layer name must be a non-empty string"
            )
    return tuple(sorted(set(names)))


def _resolve_identity(world, view: str, map_id: str | None) -> None:
    """Refuse an identity the loaded world does not hold under ``view``."""

    if view == "continent":
        return
    assert map_id is not None
    members = world.settlements if view == "settlement" else world.interiors
    others = world.interiors if view == "settlement" else world.settlements
    if map_id in members:
        return
    if map_id in others:
        actual = "interior" if view == "settlement" else "settlement"
        raise CaptureSnapshotError(
            "wrong_view", f"{map_id!r} is an {actual} document, not a {view} one"
        )
    raise CaptureSnapshotError(
        "unknown_map", f"no {view} document {map_id!r} is authored in this workspace"
    )


def _context_diagnostic(status: Mapping[str, Any]) -> Diagnostic:
    """The advisory diagnostic of a reference context that is not current.

    It never gates the capture: a missing or stale index cannot prove that a
    target is unreferenced, and it authorizes no edit or deletion either.
    """

    return Diagnostic(
        code="reference_context_missing"
        if status.get("status") == "missing"
        else "reference_context_not_current",
        category=EXTERNAL,
        message=(
            f"the external reference context is {status.get('status')}: "
            f"{'; '.join(status.get('reasons') or ()) or 'no reason reported'}; "
            "capture does not depend on it and it authorizes no edit or deletion"
        ),
        relative_path=REFERENCE_CONTEXT_ARTIFACT,
        severity=WARNING,
    )


def _admit_partition(workspace: ConfinedWorkspace, limits: Limits, world) -> dict[str, Any]:
    """Decode and freshness-check the artifact against the loaded world."""

    try:
        raw = workspace.read_document(PARTITION_ARTIFACT, limits.max_artifact_bytes)
    except ConfinementError as error:
        raise _partition_error(
            "missing" if error.code == "missing" else "malformed",
            f"the partition artifact cannot be read ({error.code}: {error})",
        ) from None
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise _partition_error(
            "malformed", f"the partition artifact is not decodable JSON: {error}"
        ) from None
    if not isinstance(document, Mapping):
        raise _partition_error(
            "malformed", "the partition artifact is not a JSON object"
        )
    terrain = terrain_definition(world.continent)
    try:
        metadata = read_partition_metadata(document)
        partition = decode_partition(
            document, is_land=lambda cell: is_land_cell(terrain, cell)
        )
    except PartitionDocumentError as error:
        raise _partition_error(
            "malformed", f"the partition artifact is malformed: {error}"
        ) from None
    except (AttributeError, TypeError) as error:
        # The frozen codec trusts more of a JSON object's shape than it checks,
        # so a structurally impossible body surfaces as a plain Python error.
        raise _partition_error(
            "malformed", f"the partition artifact is malformed: {error}"
        ) from None
    if not partition_freshness(metadata, world.partition_signature).current:
        raise _partition_error(
            "stale",
            "the partition artifact does not describe the map sources this invocation loaded",
        )
    return {
        "outlines": {
            key: [list(ring) for ring in rings]
            for key, rings in partition.outlines.items()
        }
    }


def load_capture_snapshot(
    root,
    *,
    view: str,
    map_id: str | None = None,
    hidden_layers: Iterable[str] = (),
) -> dict[str, Any]:
    """One current, read-only snapshot for one capture request.

    Returns ``{world, partition, diagnostics}``: the JSON-ready world
    projection, the admitted partition outlines (``{"outlines": {...}}`` in
    scene metres) or ``None``, and the sorted structured diagnostics. Raises
    :class:`CaptureSnapshotError` instead of returning partial data.
    """

    if view not in VIEWS:
        raise CaptureSnapshotError(
            "invalid_view", f"view must be one of {', '.join(VIEWS)}"
        )
    hidden = _normalised_layers(hidden_layers)
    requested = _requested_identity(view, map_id)
    workspace = ConfinedWorkspace(root)
    limits = Limits()
    load = load_sources(workspace, limits)
    if load.world is None or load.structure:
        raise CaptureSnapshotError(
            "structure",
            "the map sources or editor layouts are structurally invalid",
            diagnostics=tuple(item.as_dict() for item in load.structure),
        )
    world = load.world
    _resolve_identity(world, view, requested)
    diagnostics: list[Diagnostic] = [
        *diagnose_world(world),
        *load.layout_diagnostics,
    ]
    context = read_external_context(workspace, limits)
    if not context.status["current"]:
        diagnostics.append(_context_diagnostic(context.status))
    partition = (
        _admit_partition(workspace, limits, world)
        if view == "continent" and PARTITION_LAYER not in hidden
        else None
    )
    return {
        "world": load.projection,
        "partition": partition,
        "diagnostics": [item.as_dict() for item in sorted_diagnostics(diagnostics)],
    }


__all__ = [
    "CaptureSnapshotError",
    "PARTITION_LAYER",
    "REGENERATE_GUIDANCE",
    "VIEWS",
    "load_capture_snapshot",
]
