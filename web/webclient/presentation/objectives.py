"""Version-1 read-only ``objectives`` panel (webclient-align-06).

The panel discloses exactly the quest records the holder tracks: every stored
record with ``tracked`` true and state ``in_progress``, in quest-log order, at
most ``MAX_TRACKED_QUESTS`` rows (the cap is enforced by the lifecycle
operation; the validator mirrors the bound and FAILS closed on drift instead
of clamping). Row prose is the canonical describe seams — ``describe_objective``
for the current stage line and ``describe_deadline`` for the optional
deadline line — so the tracker and the guild quest board can never disagree.
``reward_copper`` is the registered offer's integer copper (never prose), or
``null`` when the holder has no live offer for the record's definition (no
registration, or the definition is not offered at their branch).

The panel is HOST-INDEPENDENT by design: unlike the guild section of
``services`` (which needs a local ``GuildStaff`` host), tracking truth is
player state, so the tracker island works anywhere the player stands. A
corrupt quest log (any ``QuestDataError`` from the shared strict reader)
degrades the WHOLE panel to the registry-owned common unavailable form —
never a partial row list. The presenter is read-only: it mutates nothing and
accepts no tracking payload itself (tracking rides the ``guild.quest_track``
action through the deterministic core).

The payload shape and bounds are mirrored by the client validator in
``web/static/webclient/js/elosern/protocol.js`` and guarded by the panel
schema-version parity contract.
"""

from typing import Any

from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
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
from world.rules.clock import read_world_clock
from world.rules.guild import GuildDataError, parse_guild_registration
from world.rules.guild_offers import GuildOfferNotFound, get_guild_offer
from world.quests.describe import describe_deadline, describe_objective
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import (
    MAX_TRACKED_QUESTS,
    QuestDataError,
    QuestState,
    read_records,
)

OBJECTIVES_SCHEMA_VERSION = 1

# Mirrors ``world.quests.runtime.MAX_TRACKED_QUESTS`` (imported, so rules and
# wire bounds cannot drift); the row cap is pinned in the spec.
OBJECTIVES_MAX_ROWS = MAX_TRACKED_QUESTS

# Wire bounds shared with the services quest-row surface (the same prose
# producers must never exceed the same ceilings).
MAX_QUEST_ID_CODE_POINTS = 64
MAX_OBJECTIVE_LINE_CODE_POINTS = 128
MAX_DEADLINE_LINE_CODE_POINTS = 64


class ObjectivesPanelError(ProtocolValidationError):
    """The available objectives payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points.

    Same closed-envelope guard as the party panel: a corrupt stored name would
    otherwise escape the byte-size check as a raw ``UnicodeEncodeError``.
    """
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise ObjectivesPanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _bounded_line(value: str, field: str, maximum: int) -> str:
    if not value.strip():
        raise ObjectivesPanelError(f"{field} must be non-empty")
    if len(value) > maximum:
        raise ObjectivesPanelError(f"{field} exceeds {maximum} code points")
    return _reject_lone_surrogates(value, field)


def _validate_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "objective row",
        {
            "quest_id",
            "display_name",
            "objective_line",
            "stage_index",
            "stage_total",
            "stage_progress",
            "objective_quantity",
            "reward_copper",
            "deadline_line",
        },
        {},
    )
    quest_id = _bounded_line(
        _require_str(value, "quest_id", maximum=MAX_QUEST_ID_CODE_POINTS),
        "quest_id",
        MAX_QUEST_ID_CODE_POINTS,
    )
    display_name = _bounded_line(
        _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "objective display_name",
        MAX_DISPLAY_NAME_CODE_POINTS,
    )
    objective_line = _bounded_line(
        _require_str(value, "objective_line", maximum=MAX_OBJECTIVE_LINE_CODE_POINTS),
        "objective_line",
        MAX_OBJECTIVE_LINE_CODE_POINTS,
    )
    stage_index = _require_int(value, "stage_index", minimum=0, maximum=MAX_SAFE_INTEGER)
    stage_total = _require_int(value, "stage_total", minimum=1, maximum=MAX_SAFE_INTEGER)
    stage_progress = _require_int(value, "stage_progress", minimum=0, maximum=MAX_SAFE_INTEGER)
    objective_quantity = _require_int(
        value, "objective_quantity", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    reward_copper = value["reward_copper"]
    if reward_copper is not None:
        reward_copper = _require_int(
            value, "reward_copper", minimum=0, maximum=MAX_SAFE_INTEGER
        )
    deadline_line = value["deadline_line"]
    if deadline_line is not None:
        deadline_line = _bounded_line(
            _require_str(value, "deadline_line", maximum=MAX_DEADLINE_LINE_CODE_POINTS),
            "deadline_line",
            MAX_DEADLINE_LINE_CODE_POINTS,
        )
    return {
        "quest_id": quest_id,
        "display_name": display_name,
        "objective_line": objective_line,
        "stage_index": stage_index,
        "stage_total": stage_total,
        "stage_progress": stage_progress,
        "objective_quantity": objective_quantity,
        "reward_copper": reward_copper,
        "deadline_line": deadline_line,
    }


def validate_objectives(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``objectives`` payload.

    Returns a normalized payload or raises :class:`ObjectivesPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload, "objectives panel", {"schema_version", "available", "rows"}, {}
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != OBJECTIVES_SCHEMA_VERSION:
        raise ObjectivesPanelError("unsupported objectives schema_version")
    if not _require_bool(payload, "available"):
        raise ObjectivesPanelError("available must be true for the objectives form")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) > OBJECTIVES_MAX_ROWS:
        raise ObjectivesPanelError(
            f"rows must be a list of at most {OBJECTIVES_MAX_ROWS} entries"
        )
    validated = [_validate_row(row) for row in rows]
    quest_ids = [row["quest_id"] for row in validated]
    if len(set(quest_ids)) != len(quest_ids):
        raise ObjectivesPanelError("objective quest_ids must be unique")
    result = {
        "schema_version": OBJECTIVES_SCHEMA_VERSION,
        "available": True,
        "rows": validated,
    }
    # Envelope guarantee (the shared per-panel closing check): an over-limit
    # payload can only come from a producer bug and fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ObjectivesPanelError("objectives payload exceeds the OOB envelope limit")
    return result


def _reward_copper_for(definition_key: str, registration: Any) -> int | None:
    """The offer's integer copper reward, or ``None`` with no live offer.

    Identical branch/registration scoping as the services board and quest
    rows (``service_view._offer_for``): no registration or no offer at the
    holder's branch means no live offer — never a guild-host requirement.
    """
    if registration is None:
        return None
    try:
        offer = get_guild_offer(definition_key, registration["branch_key"])
    except GuildOfferNotFound:
        return None
    return int(offer.reward.copper)


def objectives_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``objectives`` panel for the puppet.

    Any puppeted explorer holding quests receives the panel regardless of the
    local room contents; creation-pending puppets and unreadable canonical
    state (absent world clock, corrupt quest log) raise
    :class:`PanelUnavailableError` for the shared unavailable form.
    """
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    quest_source = actor
    if possessed_by is not None:
        from world.rules.possession import _resolve_live_object
        owner = _resolve_live_object(int(possessed_by))
        if owner is not None:
            quest_source = owner
    clock = read_world_clock()
    if clock is None:
        raise PanelUnavailableError
    tick = int(clock.tick)
    try:
        records = read_records(quest_source)
    except QuestDataError:
        raise PanelUnavailableError
    try:
        registration = parse_guild_registration(quest_source)
    except GuildDataError:
        # A malformed registration hides only the reward column, never the
        # tracking truth (degrade-independently, mirroring the surfaces).
        registration = None
    rows: list[dict[str, Any]] = []
    for record in records:
        if not record.tracked or record.state is not QuestState.IN_PROGRESS:
            continue
        definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        if definition is None:  # pragma: no cover — read_records validates this
            raise PanelUnavailableError
        stage = definition.stages[record.stage_index]
        rows.append(
            {
                "quest_id": record.quest_id,
                "display_name": definition.display_name[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "objective_line": describe_objective(stage.objective),
                "stage_index": record.stage_index,
                "stage_total": len(definition.stages),
                "stage_progress": record.stage_progress,
                "objective_quantity": stage.objective.quantity,
                "reward_copper": _reward_copper_for(record.definition_key, registration),
                "deadline_line": describe_deadline(record.deadline_tick, tick),
            }
        )
    return validate_objectives(
        {
            "schema_version": OBJECTIVES_SCHEMA_VERSION,
            "available": True,
            "rows": rows,
        }
    )


__all__ = [
    "OBJECTIVES_MAX_ROWS",
    "OBJECTIVES_SCHEMA_VERSION",
    "ObjectivesPanelError",
    "objectives_presenter",
    "validate_objectives",
]
