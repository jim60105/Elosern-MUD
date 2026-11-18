"""Browser-harness art control channel (creation-draft-portrait journeys).

A managed browser server has no in-process hook a test can call: the pending
creation account runs behind the creation command gate (no ``@py``), the
scheduler is off and ``@art run`` needs a Developer puppet. Journeys that
must drive the REAL request -> queue -> worker -> publication path therefore
use this file-based channel, opted in per runtime with
``ELOSERN_BROWSER_SD_CONTROL=<path>`` (and ``ELOSERN_BROWSER_SD_CLIENT``
pointed at :class:`~web.tests.browser.fake_sd_client.ControlledSDWebUIClient`).

Three files share the ``<path>`` stem, each written atomically
(``os.replace``):

``<path>``
    The client mode, read by the controlled fake client on every call:
    ``{"probe": "ok"|"fail", "generate": "ok"|"fail"|"hold"}``.
``<path>.cmd``
    One numbered command from the test, ``{"seq": n, "op": ...}``.
``<path>.ack``
    The server's answer to the newest command, ``{"seq": n, "result": ...}``.

Operations, executed on the reactor thread by a harness-only poll:

``drain``
    ``world.art.worker.drain`` once; the result is the number of jobs it
    claimed (generation itself runs on the worker's background thread, so a
    held generation never blocks this poll).
``drain_sync``
    ``world.art.worker.drain_synchronous`` until the queue is empty; every
    claimed job has settled and published when the ack arrives. Only for
    non-held modes (a held generation would block the reactor).
``in_flight``
    Whether the creation character's portrait subject has a pending or
    running gallery job.
``reset_probe_cache``
    Clear the connectivity verdict cache (its test seam), so the next read
    is "unknown" and the next admission probes the client afresh.
``probe``
    Run one forced connectivity probe, replacing the cached verdict with the
    current client mode's answer.
``cards``
    The image ids on the creation account's character's named portrait
    subject.

Nothing here exists outside the browser harness, and no test asserts time:
the test side waits for the acknowledged sequence number.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

CONTROL_ENV = "ELOSERN_BROWSER_SD_CONTROL"

_POLL_SECONDS = 0.1
_loop = None
_last_seq = 0


# -- shared file helpers ---------------------------------------------------------


def write_json(path: Path | str, value: dict) -> None:
    """Write ``value`` atomically, so a reader never sees a partial file."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value), encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path | str) -> dict | None:
    """The file's JSON object, or ``None`` when absent or not (yet) valid."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):  # observability: ignore R2: absent or mid-write; the caller polls again
        return None
    return value if isinstance(value, dict) else None


def read_mode(key: str, default: str) -> str:
    """One mode value from the configured control file (server side)."""
    control = os.environ.get(CONTROL_ENV)
    if not control:
        return default
    value = (read_json(control) or {}).get(key)
    return value if isinstance(value, str) else default


# -- server side --------------------------------------------------------------


def _creation_character():
    from evennia.accounts.models import AccountDB

    from web.tests.browser.seed.identity import CREATION_ACCOUNT_USERNAME

    account = AccountDB.objects.get(username=CREATION_ACCOUNT_USERNAME)
    characters = list(account.characters)
    if len(characters) != 1:
        raise RuntimeError(f"expected one creation character, found {len(characters)}")
    return characters[0]


def _run(op: str) -> dict:
    if op == "drain":
        from world.art.worker import drain

        return {"dispatched": drain(4)}
    if op == "drain_sync":
        from world.art.worker import drain_synchronous

        total = 0
        for _ in range(50):
            claimed = drain_synchronous(4)
            if not claimed:
                return {"dispatched": total}
            total += claimed
        raise RuntimeError("the art queue never emptied")
    if op == "in_flight":
        from world.art.queue import gallery_job_in_flight
        from world.art.subjects import named_character_subject

        return {"in_flight": gallery_job_in_flight(named_character_subject(_creation_character()))}
    if op == "reset_probe_cache":
        from world.art import connectivity

        connectivity._reset_for_testing()
        return {}
    if op == "probe":
        from world.art import connectivity

        return {"ok": connectivity.probe(force=True).ok}
    if op == "cards":
        from world.art.gallery import cards_for
        from world.art.subjects import named_character_subject

        from world.art.gallery import record_for

        subject = named_character_subject(_creation_character())
        record = record_for(subject)
        return {
            "image_ids": sorted(str(card.get("image_id")) for card in cards_for(subject)),
            # The bounded last error code, for a failing journey's diagnosis.
            "last_error_code": None if record is None else record.db.last_error_code,
        }
    raise ValueError(f"unknown control op {op!r}")


def _poll(control: str) -> None:
    global _last_seq
    command = read_json(control + ".cmd")
    if not command:
        return
    seq = command.get("seq")
    if not isinstance(seq, int) or seq <= _last_seq:
        return
    _last_seq = seq
    try:
        answer = {"seq": seq, "result": _run(str(command.get("op")))}
    except Exception as error:  # observability: ignore R2: harness-only; the failure travels to the test in the ack
        answer = {"seq": seq, "error": f"{type(error).__name__}: {error}"}
    write_json(control + ".ack", answer)


def install_if_configured() -> None:
    """Start the reactor-thread command poll when the runtime opted in.

    A restarted server process resumes after the last acknowledged command,
    so a reload never re-executes one.
    """
    global _loop, _last_seq
    control = os.environ.get(CONTROL_ENV)
    if not control or _loop is not None:
        return
    from twisted.internet import task

    ack = read_json(control + ".ack") or {}
    _last_seq = ack.get("seq") if isinstance(ack.get("seq"), int) else 0
    _loop = task.LoopingCall(_poll, control)
    _loop.start(_POLL_SECONDS, now=False)


def uninstall() -> None:
    """Stop the poll (server stop or reload)."""
    global _loop
    if _loop is not None and _loop.running:
        _loop.stop()
    _loop = None


# -- test side ------------------------------------------------------------------


class SDControl:
    """The test's handle on one runtime's control files."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._seq = 0
        self.set(probe="ok", generate="ok")

    def set(self, **mode: str) -> None:
        """Merge ``mode`` into the client mode file."""
        current = read_json(self.path) or {}
        current.update(mode)
        write_json(self.path, current)

    def run(self, op: str, timeout: float = 30.0) -> dict:
        """Send one command and wait for its acknowledgement."""
        self._seq += 1
        seq = self._seq
        write_json(Path(str(self.path) + ".cmd"), {"seq": seq, "op": op})
        deadline = time.monotonic() + timeout
        ack_path = Path(str(self.path) + ".ack")
        while time.monotonic() < deadline:
            ack = read_json(ack_path)
            if ack and ack.get("seq") == seq:
                if "error" in ack:
                    raise AssertionError(f"control op {op!r} failed: {ack['error']}")
                return ack.get("result") or {}
            time.sleep(0.05)
        raise AssertionError(f"control op {op!r} (seq {seq}) was never acknowledged")
