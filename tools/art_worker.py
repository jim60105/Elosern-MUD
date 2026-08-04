"""Deterministic default art worker (the design's external swap point).

The engine hands validated jobs to an external command and validates the
results; the worker implementation itself is deliberately external. This
module is the shipped *default* worker so the engine is verifiable and fully
offline out of the box: it deterministically writes the exact expected output
file for every job (a fixed placeholder payload) and reports success, or
reports ``failed`` for a job carrying the ``ART_DEFAULT_FAIL`` marker.

Deployments that call a real image service (local Stable Diffusion, a
prompt-writing agent, etc.) override ``ART_WORKER_CMD`` to their own command;
the protocol is the same: JSON-lines jobs on stdin, JSON-lines results on
stdout, output written under ``ART_STORE_ROOT``.

Reads JSON-lines jobs from stdin and writes JSON-lines results to stdout.
``ART_DEFAULT_FAIL`` is a comma-separated list of full job keys that must
report ``failed`` without writing a file (used by tests to exercise the
offline degraded path).
"""

import base64
import json
import os
import sys

# A deterministic 1x1 transparent PNG so the offline placeholder is a real,
# servable image rather than a mislabelled text file.
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _main() -> int:
    game_dir = os.environ.get("ART_GAME_DIR")
    if game_dir:
        sys.path.insert(0, os.path.join(game_dir, "tools"))
        sys.path.insert(0, game_dir)
    store_root = os.path.abspath(
        os.environ.get("ART_DEFAULT_STORE_ROOT", os.getcwd())
    )
    fail_keys = set(
        key for key in os.environ.get("ART_DEFAULT_FAIL", "").split(",") if key
    )
    results: list[str] = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        job = json.loads(line)
        key = job["key"]
        if key in fail_keys:
            results.append(
                json.dumps(
                    {
                        "key": key,
                        "status": "failed",
                        "output_identity": None,
                        "error": "offline_placeholder",
                    },
                    ensure_ascii=False,
                )
            )
            continue
        out_path = os.path.join(store_root, job["out_path"])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as handle:
            handle.write(_PLACEHOLDER_PNG)
        results.append(
            json.dumps(
                {
                    "key": key,
                    "status": "success",
                    "output_identity": job["out_path"],
                    "error": None,
                },
                ensure_ascii=False,
            )
        )
    sys.stdout.write("\n".join(results) + ("\n" if results else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
