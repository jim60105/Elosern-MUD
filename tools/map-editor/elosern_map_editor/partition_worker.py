"""The partition job's child process: captured sources in, artifact text out.

Run as ``python -m elosern_map_editor.partition_worker`` by
:mod:`elosern_map_editor.partition_job`, in the editor's own environment with
the core ``generation`` extra (NumPy/SciPy). The heavy raster work therefore
never shares the service's interpreter, its event loop or its GIL, and a
cancellation simply ends this process.

Protocol (one JSON document each way):

* stdin: ``{"signature": str, "sources": [{"relative_path": str, "text": str}, ...]}``
  -- the world sources the service captured when it admitted the job, and
  that capture's partition source signature;
* stdout: ``{"ok": true, "text": <artifact text>}`` or
  ``{"ok": false, "code": str, "problems": [str, ...]}``.

The child reads no workspace file and writes none: it partitions exactly the
captured snapshot, through the core's authoring loader and
:func:`elosern_map_core.partition.world_snapshot`. Publication (and every
freshness recheck) belongs to the service.
"""

from __future__ import annotations

import json
import sys

#: Problem lines returned to the service (each is also length-bounded).
MAX_PROBLEMS = 20
MAX_PROBLEM_CHARS = 400


def _bounded(problems) -> list[str]:
    return [str(problem)[:MAX_PROBLEM_CHARS] for problem in list(problems)[:MAX_PROBLEMS]]


def run(request: dict) -> dict:
    from elosern_map_core import AuthoringError, load_authoring_world, make_source_document
    from elosern_map_core.partition import (
        PartitionError,
        generate_partition,
        partition_input,
        world_snapshot,
    )

    sources = [make_source_document(row["relative_path"], row["text"]) for row in request["sources"]]
    try:
        world = load_authoring_world(sources)
    except AuthoringError as error:
        return {"ok": False, "code": "inputs_invalid", "problems": _bounded(d.message for d in error.diagnostics)}
    if world.partition_signature != request["signature"]:
        return {
            "ok": False,
            "code": "inputs_changed",
            "problems": ["the captured sources do not carry the admitted input signature"],
        }
    try:
        text = generate_partition(partition_input(world_snapshot(world)))
    except PartitionError as error:
        return {"ok": False, "code": "generation_failed", "problems": _bounded(error.problems)}
    return {"ok": True, "text": text}


def main() -> int:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    result = run(request)
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
