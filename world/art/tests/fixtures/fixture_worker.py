"""Deterministic fixture worker command for art-backend tests.

Reads JSON-lines jobs on stdin (one object per line) and writes JSON-lines
results on stdout, exactly the external worker protocol ``world.art.worker``
implements. It writes the exact expected output file under the store root for
a matching job and never touches the network.

Behavior is driven entirely by fixed inputs so tests stay deterministic:

- ``ART_FIXTURE_WRITE`` -- set to ``1`` (default) to write the expected file.
- ``ART_FIXTURE_FAIL`` -- a comma-separated list of full job keys that must be
  reported ``failed`` without writing a file (the "fails on a marker" path).
- ``ART_FIXTURE_COUNT_FILE`` -- when set, append one line ``<job key>`` per
  received job so tests can assert exactly which subjects reached the worker.
- ``ART_FIXTURE_WRONG_KEY`` -- a comma-separated list of job keys whose result
  is reported under a fabricated different key (mismatched-key rejection).
- ``ART_FIXTURE_WRONG_IDENTITY`` -- when ``1``, report success with an
  output identity that differs from the job's expected identity.
- ``ART_FIXTURE_EMIT_NONE`` -- when ``1``, emit no result lines at all
  (crash/truncated batch).
- ``ART_FIXTURE_MALFORMED`` -- when ``1``, emit one non-JSON line.
- ``ART_FIXTURE_NON_OBJECT`` -- when ``1``, emit a valid JSON value that is not
  an object (e.g. ``null``) so the protocol rejects it without crashing.
- ``ART_FIXTURE_SLEEP`` -- seconds to sleep before writing (timeout tests).
"""

import json
import os
import sys
import time


def _main() -> int:
    store_root = os.path.abspath(os.environ.get("ART_FIXTURE_STORE_ROOT", "."))
    write_enabled = os.environ.get("ART_FIXTURE_WRITE", "1") == "1"
    fail_keys = set(
        key for key in os.environ.get("ART_FIXTURE_FAIL", "").split(",") if key
    )
    wrong_key_jobs = set(
        key
        for key in os.environ.get("ART_FIXTURE_WRONG_KEY", "").split(",")
        if key
    )
    wrong_identity = os.environ.get("ART_FIXTURE_WRONG_IDENTITY", "0") == "1"
    emit_none = os.environ.get("ART_FIXTURE_EMIT_NONE", "0") == "1"
    malformed = os.environ.get("ART_FIXTURE_MALFORMED", "0") == "1"
    non_object = os.environ.get("ART_FIXTURE_NON_OBJECT", "0") == "1"
    sleep_seconds = float(os.environ.get("ART_FIXTURE_SLEEP", "0") or "0")
    count_file = os.environ.get("ART_FIXTURE_COUNT_FILE")
    if count_file:
        count_file = os.path.abspath(count_file)
        os.makedirs(os.path.dirname(count_file), exist_ok=True)

    jobs = []
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        jobs.append(json.loads(line))

    if sleep_seconds:
        time.sleep(sleep_seconds)

    for job in jobs:
        key = job["key"]
        if count_file:
            with open(count_file, "a", encoding="utf-8") as handle:
                handle.write(f"{key}\n")
        if key in fail_keys:
            print(
                json.dumps(
                    {
                        "key": key,
                        "status": "failed",
                        "output_identity": None,
                        "error": "fixture_fail",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue
        if emit_none:
            continue
        if malformed:
            print("not-json{{{", flush=True)
            continue
        if non_object:
            print("null", flush=True)
            continue
        if write_enabled:
            out_path = os.path.join(store_root, job["out_path"])
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as handle:
                handle.write(f"fixture asset for {key}\n")
        result = {
            "key": f"scene:not-an-input" if key in wrong_key_jobs else key,
            "status": "success",
            "output_identity": (
                "scene/other.png" if wrong_identity else job["out_path"]
            ),
            "error": None,
        }
        print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
