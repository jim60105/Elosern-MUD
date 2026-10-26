"""Shared helpers for the presentation publication tests.

A publication always returns a ``Deferred``; when the coordinator drains inline
(no running reactor, as under the test runner) that Deferred is already
resolved when the call returns. These helpers read it without guessing, so a
test asserts on the receipt or on the real failure instead of on a returned
envelope.
"""

from typing import Any

from twisted.python.failure import Failure

from web.webclient.presentation.publication import PublicationReceipt


def publication_result(deferred: Any) -> Any:
    """Return a resolved publication's value, re-raising its failure."""
    if not getattr(deferred, "called", False):
        raise AssertionError("publication did not resolve")
    result = getattr(deferred, "result", None)
    if isinstance(result, Failure):
        publication_failure(deferred).raiseException()
    return result


def publication_failure(deferred: Any) -> Failure:
    """Return a resolved publication's ``Failure``, or fail the test."""
    result = getattr(deferred, "result", None)
    if not isinstance(result, Failure):
        raise AssertionError(f"publication did not fail: {result!r}")
    # Consume the failure so Twisted does not report it as unhandled at
    # collection time; the caller keeps the ``Failure`` for fault checks.
    deferred.addErrback(lambda _failure: None)
    return result


def publication_receipt(deferred: Any) -> PublicationReceipt:
    """Return the resolved :class:`PublicationReceipt`, or fail the test."""
    receipt = publication_result(deferred)
    if not isinstance(receipt, PublicationReceipt):
        raise AssertionError(f"publication produced no receipt: {receipt!r}")
    return receipt


def publication_frames(session: Any, message: str | None = None) -> list[dict[str, Any]]:
    """Return the envelopes a fake session received, oldest first."""
    frames: list[dict[str, Any]] = []
    for call in getattr(session, "sent", ()):
        for name, payload in call.items():
            if message is None or name == message:
                frames.append(payload[0][0])
    return frames


def last_frame(session: Any, message: str) -> dict[str, Any]:
    """Return the newest envelope of ``message`` a fake session received."""
    frames = publication_frames(session, message)
    if not frames:
        raise AssertionError(f"no {message} frame was sent")
    return frames[-1]


def recorded_frames(calls: Any) -> list[dict[str, Any]]:
    """Return the presentation envelopes in recorded ``session.msg`` kwargs."""
    frames: list[dict[str, Any]] = []
    for call in calls:
        for name in ("ui_snapshot", "ui_update"):
            if name in call:
                frames.append(call[name][0][0])
    return frames


def committed_view(calls: Any, base_panels: Any = None) -> dict[str, Any]:
    """Replay recorded frames into the client-visible committed view.

    Applies each envelope in revision order exactly as a conforming reducer
    would: a snapshot replaces the eager membership, a delta replaces the
    panels it carries and deletes its ``removed_panels``. Assertions can then
    target the state the browser holds instead of one particular wire frame,
    which is what "the client sees the reply" actually means now that an
    unchanged panel is not retransmitted.

    ``base_panels`` seeds the replay when the recording starts after the
    initial snapshot (a fixture that cleared its transport between the sync and
    the publication under test).
    """
    view: dict[str, Any] = {
        "mode": None,
        "revision": 0,
        "panels": dict(base_panels) if base_panels is not None else {},
    }
    for frame in sorted(recorded_frames(calls), key=lambda item: item["revision"]):
        if "base_revision" in frame:
            panels = dict(view["panels"])
            panels.update(frame["panels"])
            for name in frame["removed_panels"]:
                panels.pop(name, None)
            view["panels"] = panels
        else:
            view["panels"] = dict(frame["panels"])
        view["mode"] = frame["mode"]
        view["revision"] = frame["revision"]
    return view
