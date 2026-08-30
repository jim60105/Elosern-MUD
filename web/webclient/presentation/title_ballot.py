"""Exact schema-version-1 ``title_ballot`` panel and presenter (title-epithet-nomination).

The presenter serializes the pending epithet nomination ballot owned by
``world.rules.titles`` through the safe read (``safe_pending_ballot``) and
validates its own output against the exact bounded schema before returning it
to the presentation registry. The ballot never expires and there is no
time-based transition on this face: the panel is a pure current-state render,
so it is always available — a missing or None actor and malformed stored
ballot state both render the zero-candidate payload (the menu simply does not
appear), never a raise. The registry still owns the panel's stable
unavailable pair for genuinely unexpected presenter failures.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol.js``. The bounds are
owned by ``world.rules.titles`` (the ballot writer validates storage against
them); this module mirrors them, and the JS validator mirrors these numbers
in the parity contract.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from world.rules.titles import (
    BALLOT_BASIS_MAX_CHARS,
    MAX_BALLOT_CANDIDATES,
    MAX_EPITHET_DISPLAY_CODE_POINTS,
    safe_pending_ballot,
)

TITLE_BALLOT_SCHEMA_VERSION = 1

# Exact shared bounds -- must stay equal in the JS validator. The values are
# owned by the rules ballot writer; the panel only mirrors them.
TITLE_BALLOT_MAX_CANDIDATES = MAX_BALLOT_CANDIDATES
TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS = MAX_EPITHET_DISPLAY_CODE_POINTS
TITLE_BALLOT_MAX_BASIS_CODE_POINTS = BALLOT_BASIS_MAX_CHARS

# The display-only 1-based choice number; the answer actions address
# candidates by this index (``title.accept`` payload ``{"index": ...}``).
TITLE_BALLOT_MIN_INDEX = 1


class TitleBallotPanelError(ProtocolValidationError):
    """The available title_ballot payload violates its exact bounded schema."""


def _validate_candidate(value: Any, position: int) -> dict[str, Any]:
    _require_exact_fields(
        value,
        f"title ballot candidate[{position}]",
        {"index", "display", "basis"},
        {},
    )
    index = _require_int(
        value,
        "index",
        minimum=TITLE_BALLOT_MIN_INDEX,
        maximum=TITLE_BALLOT_MAX_CANDIDATES,
    )
    if index != position:
        raise TitleBallotPanelError(
            "candidate indices must be strictly 1..n ascending"
        )
    display = _require_str(
        value, "display", maximum=TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS
    )
    if not display:
        raise TitleBallotPanelError("candidate display must be non-empty")
    basis = _require_str(
        value, "basis", maximum=TITLE_BALLOT_MAX_BASIS_CODE_POINTS
    )
    if not basis:
        raise TitleBallotPanelError("candidate basis must be non-empty")
    return {"index": index, "display": display, "basis": basis}


def validate_title_ballot(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``title_ballot`` payload.

    Returns a normalized payload or raises :class:`TitleBallotPanelError`.
    The common unavailable form is NOT accepted here; the registry handles
    it. Zero candidates is the legitimate empty-ballot form.
    """
    _require_exact_fields(
        payload,
        "title_ballot panel",
        {"schema_version", "available", "kind", "candidates"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != TITLE_BALLOT_SCHEMA_VERSION:
        raise TitleBallotPanelError("unsupported title_ballot schema_version")
    if not _require_bool(payload, "available"):
        raise TitleBallotPanelError(
            "available must be true for the title_ballot form"
        )
    if payload["kind"] != "title_ballot":
        raise TitleBallotPanelError("title_ballot panel kind must be title_ballot")

    candidates = payload["candidates"]
    if not isinstance(candidates, list):
        raise TitleBallotPanelError("candidates must be a list")
    if len(candidates) > TITLE_BALLOT_MAX_CANDIDATES:
        raise TitleBallotPanelError(
            f"candidates must hold at most {TITLE_BALLOT_MAX_CANDIDATES} entries"
        )
    normalized = [
        _validate_candidate(entry, position)
        for position, entry in enumerate(candidates, start=1)
    ]

    result = {
        "schema_version": TITLE_BALLOT_SCHEMA_VERSION,
        "available": True,
        "kind": "title_ballot",
        "candidates": normalized,
    }
    # Envelope guarantee (mirrors the services discipline): a conforming
    # payload must serialize within the OOB envelope limit; the per-field
    # ceilings keep any legal ballot far below it, so an over-limit payload
    # can only come from a producer bug and fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise TitleBallotPanelError(
            "title_ballot payload exceeds the OOB envelope limit"
        )
    return result


def title_ballot_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``title_ballot`` panel for the puppet.

    The ballot renders solely from persisted state through the rules safe
    read: a missing/None actor, an absent ballot, and present-but-malformed
    ballot state all render the zero-candidate payload (never a raise).
    Basis text is server-authored within its storage cap — this surface
    never truncates.
    """
    actor = context.actor
    ballot = () if actor is None else safe_pending_ballot(actor)
    candidates = [
        {
            "index": index,
            "display": entry["display"],
            "basis": entry["basis"],
        }
        for index, entry in enumerate(ballot, start=1)
    ]
    return validate_title_ballot(
        {
            "schema_version": TITLE_BALLOT_SCHEMA_VERSION,
            "available": True,
            "kind": "title_ballot",
            "candidates": candidates,
        }
    )


__all__ = [
    "TITLE_BALLOT_MAX_BASIS_CODE_POINTS",
    "TITLE_BALLOT_MAX_CANDIDATES",
    "TITLE_BALLOT_MAX_DISPLAY_CODE_POINTS",
    "TITLE_BALLOT_MIN_INDEX",
    "TITLE_BALLOT_SCHEMA_VERSION",
    "TitleBallotPanelError",
    "title_ballot_presenter",
    "validate_title_ballot",
]
