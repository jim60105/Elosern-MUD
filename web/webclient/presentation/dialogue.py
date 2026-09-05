"""Version-1 read-only ``dialogue`` presentation panel (webclient-align-10).

The presenter serializes the viewer's live dialogue session (change 07's
character-held state, owned by ``world.rules.dialogue``) into the exact
``{schema_version, available, kind, host, bond_stage, line, choices}`` shape.
The host triple reuses the party-row vocabulary (``identity``,
``display_name``, ``portrait_ref``) so the dialogue surface and the party
islands name the same NPC with the same fields; ``bond_stage`` is the
canonical affinity stage NAME (``null`` when the viewer has no relationship
record with the host) and the raw affinity number never reaches the wire.
``choices`` is the same ``{keyword_id, label}`` keyword-pool vocabulary the
exploration interact descriptor exposes, owned by
``affordances._scripted_keyword_descriptors`` (authored-table order; the panel
truncates to its own ``DIALOGUE_MAX_CHOICES``, independent of the affordance
pool's ``MAX_SCRIPTED_KEYWORDS`` bound — webclient-align-11).

The panel is available EXACTLY when ``live_dialogue_session`` resolves; every
other state — absent, corrupt-at-parse (tightened in the session parser: an
over-bound or lone-surrogate stored line is corrupt), a host dbid that no
longer resolves to a present, talk-interactable NPC, a race-lost re-resolve,
a creation-pending puppet, or a host with no location — degrades through
:class:`PanelUnavailableError` to the registry-owned registered
``dialogue_unavailable`` form. Degrade-before-validate is deliberate: an
available-form validation error would surface as the registry's
internal-presenter payload, not the registered reason.

The presenter is read-only by construction: it opens, refreshes, and clears
nothing; it re-resolves the host from the database identity and never emits a
live object or filesystem reference.
"""

from typing import Any

from web.webclient.presentation.affordances import (
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_KEYWORD_ID_CHARS,
    MAX_KEYWORD_LABEL_CODE_POINTS,
    _scripted_keyword_descriptors,
)
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
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.dialogue import MAX_DIALOGUE_SESSION_LINE_CODE_POINTS

DIALOGUE_SCHEMA_VERSION = 1

# Row-count cap: panel-owned literal (webclient-align-11). Deliberately
# decoupled from ``MAX_SCRIPTED_KEYWORDS`` (16, the interact-target keyword
# pool bound): the dialogue caption stays compact so the narrative line never
# gets pushed out of view, and the table-order prefix the panel shows is the
# same prefix the affordance surface truncates with. The UMD mirror
# ``protocol.js`` tracks this bound; the overflow keywords stay reachable
# through the interact affordance surface.
DIALOGUE_MAX_CHOICES = 4


class DialoguePanelError(ProtocolValidationError):
    """The available dialogue payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points.

    Same contract as the party row: a Python ``str`` can store
    ``U+D800..U+DFFF`` values, but they are not valid JSON text, so corrupt
    stored prose must fail closed as an explicit schema violation (the UMD
    mirror rejects the identical payloads).
    """
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise DialoguePanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _bounded_text(value: str, field: str, maximum: int) -> str:
    if not value or not value.strip():
        raise DialoguePanelError(f"{field} must be non-empty")
    if sum(1 for _ in value) > maximum:
        raise DialoguePanelError(f"{field} must be at most {maximum} code points")
    return _reject_lone_surrogates(value, field)


def _validate_host(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "dialogue host", {"identity", "display_name", "portrait_ref"}, {}
    )
    identity = _require_int(value, "identity", minimum=1, maximum=MAX_SAFE_INTEGER)
    display_name = _bounded_text(
        _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "host display_name",
        MAX_DISPLAY_NAME_CODE_POINTS,
    )
    if value["portrait_ref"] is not None:
        raise DialoguePanelError("portrait_ref must be null in this schema version")
    return {
        "identity": identity,
        "display_name": display_name,
        "portrait_ref": None,
    }


def _validate_bond_stage(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DialoguePanelError("bond_stage must be a stage name string or null")
    return _bounded_text(
        value, "bond_stage", MAX_DISPLAY_NAME_CODE_POINTS
    )


def _validate_choice(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "dialogue choice", {"keyword_id", "label"}, {})
    keyword_id = value["keyword_id"]
    if not isinstance(keyword_id, str) or not keyword_id.strip():
        raise DialoguePanelError("keyword_id must be a non-empty string")
    # Mirror the UMD mirror exactly: an unpaired surrogate never ships.
    _reject_lone_surrogates(keyword_id, "keyword_id")
    # Same bound as the exploration keyword vocabulary: authored keywords are
    # zh-TW words, so the cap is code points, not ASCII characters.
    if sum(1 for _ in keyword_id) > MAX_KEYWORD_ID_CHARS:
        raise DialoguePanelError(
            f"keyword_id must be at most {MAX_KEYWORD_ID_CHARS} code points"
        )
    label = _bounded_text(
        _require_str(value, "label", maximum=MAX_KEYWORD_LABEL_CODE_POINTS),
        "choice label",
        MAX_KEYWORD_LABEL_CODE_POINTS,
    )
    return {"keyword_id": keyword_id, "label": label}


def validate_dialogue(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``dialogue`` payload.

    Returns a normalized payload or raises :class:`DialoguePanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "dialogue panel",
        {
            "schema_version",
            "available",
            "kind",
            "host",
            "bond_stage",
            "line",
            "choices",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != DIALOGUE_SCHEMA_VERSION:
        raise DialoguePanelError("unsupported dialogue schema_version")
    if not _require_bool(payload, "available"):
        raise DialoguePanelError("available must be true for the dialogue form")
    if payload["kind"] != "dialogue":
        raise DialoguePanelError("kind must be dialogue")
    host = _validate_host(payload["host"])
    bond_stage = _validate_bond_stage(payload["bond_stage"])
    # The field-specific bound is the shared accepted-prose bound owned by
    # the session writer (deliberately the 2,000 session constant, never the
    # protocol's generic 2,048 ceiling): a line can only have been authored
    # under it, so an over-bound value is corruption and rejects, never
    # truncates.
    line = _bounded_text(
        _require_str(payload, "line", maximum=MAX_DIALOGUE_SESSION_LINE_CODE_POINTS),
        "line",
        MAX_DIALOGUE_SESSION_LINE_CODE_POINTS,
    )
    choices = payload["choices"]
    if not isinstance(choices, list) or len(choices) > DIALOGUE_MAX_CHOICES:
        raise DialoguePanelError(
            f"choices must be a list of at most {DIALOGUE_MAX_CHOICES} entries"
        )
    rows = [_validate_choice(entry) for entry in choices]
    keyword_ids = [row["keyword_id"] for row in rows]
    if len(set(keyword_ids)) != len(keyword_ids):
        raise DialoguePanelError("dialogue choice keyword ids must be unique")
    result = {
        "schema_version": DIALOGUE_SCHEMA_VERSION,
        "available": True,
        "kind": "dialogue",
        "host": host,
        "bond_stage": bond_stage,
        "line": line,
        "choices": rows,
    }
    # Envelope guarantee (the shared per-panel closing check).
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise DialoguePanelError("dialogue payload exceeds the OOB envelope limit")
    return result


def _resolve_live_host(character: Any) -> Any | None:
    """The session NPC re-resolved as present + talk-interactable, or ``None``.

    Re-runs the same resolution gate ``live_dialogue_session`` applies so the
    presenter can hand the same object to the display/bond/keyword readers
    without a second stale window between liveness check and serialization.
    """
    from evennia.objects.objects import ObjectDB

    from typeclasses.npcs import NPC
    from world.rules.dialogue import live_dialogue_session
    from world.rules.npc_intents import intent_context_ok

    session = live_dialogue_session(character)
    if session is None:
        return None
    obj = ObjectDB.objects.filter(id=session.npc_id).first()
    if obj is None or not isinstance(obj, NPC):
        return None
    if not intent_context_ok(obj, character):
        return None
    return obj


def dialogue_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``dialogue`` panel for the authenticated puppet."""
    from world.rules.dialogue import live_dialogue_session
    from world.rules.npc_identity import npc_display_name

    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    session = live_dialogue_session(actor)
    if session is None:
        raise PanelUnavailableError
    npc = _resolve_live_host(actor)
    if npc is None:  # observability: ignore R2: race between the liveness read and the re-resolve degrades to the registered unavailable form; the next commit re-derives from canonical state
        raise PanelUnavailableError
    bond_stage = (
        npc.relations.stage_for(actor).name
        if npc.relations.has_record(actor)
        else None
    )
    return validate_dialogue(
        {
            "schema_version": DIALOGUE_SCHEMA_VERSION,
            "available": True,
            "kind": "dialogue",
            "host": {
                "identity": int(npc.pk),
                "display_name": npc_display_name(npc)[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "portrait_ref": None,
            },
            "bond_stage": bond_stage,
            "line": session.line,
            # Table-order truncation to the panel's own bound (align-11): the
            # first four authored keywords, matching the digit legend 1-4.
            "choices": _scripted_keyword_descriptors(npc)[:DIALOGUE_MAX_CHOICES],
        }
    )


__all__ = [
    "DIALOGUE_MAX_CHOICES",
    "DIALOGUE_SCHEMA_VERSION",
    "DialoguePanelError",
    "dialogue_presenter",
    "validate_dialogue",
]
