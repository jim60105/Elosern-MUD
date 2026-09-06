"""Version-1 read-only ``quest_log`` panel (quest-issuer-model design §8.1, change 8).

The panel is the player's own quest book, readable anywhere: one row per
stored record in quest-log order — guild and private commissions alike —
capped at the shared ``MAX_QUEST_ROWS`` bound imported from the services
panel so the two surfaces cannot drift. Row identity and progress come from
the record; ``stage_total`` from the definition; all prose from the canonical
describe seams (``describe_objective``, ``describe_deadline``,
``describe_quest_detail``, ``describe_reward``), so the quest book, the
objective tracker, and the guild counter can never disagree. The commission
disclosure rides ``resolve_issuance``: ``issuer`` (kind, key, label) is
derived from the stored issuer key, while ``settlement`` and ``reward_line``
describe the resolved issuance. A record whose issuance can no longer be
resolved (content edits can unregister a generated definition's issuance
while a player holds the quest) still renders every other field with a null
``reward_line`` and a null ``settlement`` — never a fabricated reward.

The panel is HOST-INDEPENDENT by design: unlike the guild section of
``services`` (which needs a local ``GuildStaff`` host), reading one's own
quest log is not a counter service, so no service host, registration,
schedule, or room is consulted. A corrupt quest log (any ``QuestDataError``
from the shared strict reader) degrades the WHOLE panel to the registry-owned
common unavailable form — never a partial row list. The presenter is
read-only: it mutates nothing (the ``track`` descriptor is disclosure only;
tracking rides the ``guild.quest_track`` action through the deterministic
core).

The payload shape and bounds are mirrored by the client validator in
``web/static/webclient/js/elosern/protocol.js`` and guarded by the
repository-wide parity contracts.
"""

from typing import Any

from web.webclient.presentation.affordances import MAX_DISPLAY_NAME_CODE_POINTS
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.objectives import (
    MAX_DEADLINE_LINE_CODE_POINTS,
    MAX_OBJECTIVE_LINE_CODE_POINTS,
    MAX_QUEST_ID_CODE_POINTS,
)
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
from web.webclient.presentation.services import (
    MAX_DETAIL_CODE_POINTS,
    MAX_KEY_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_QUEST_ROWS,
    MAX_SUMMARY_CODE_POINTS,
    QUEST_STATES,
    TRACK_ACTION,
)
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.quests.describe import (
    describe_deadline,
    describe_objective,
    describe_quest_detail,
    describe_reward,
)
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import QuestDataError, read_records
from world.rules.clock import read_world_clock
from world.rules.quest_issuance import (
    MAX_ISSUER_KEY_LENGTH,
    Settlement,
    parse_issuer_key,
    resolve_issuance,
)

QUEST_LOG_SCHEMA_VERSION = 1

# Mirrors ``services.MAX_QUEST_ROWS`` (imported, so the two row caps cannot
# drift); the cap is pinned in the spec.
QUEST_LOG_MAX_ROWS = MAX_QUEST_ROWS

_SETTLEMENT_VALUES = frozenset(item.value for item in Settlement)


class QuestLogPanelError(ProtocolValidationError):
    """The available quest_log payload violates its exact bounded schema."""


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points.

    Same closed-envelope guard as the party and objectives panels: a corrupt
    stored name would otherwise escape the byte-size check as a raw
    ``UnicodeEncodeError``.
    """
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise QuestLogPanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _bounded_line(value: str, field: str, maximum: int) -> str:
    if not value.strip():
        raise QuestLogPanelError(f"{field} must be non-empty")
    if len(value) > maximum:
        raise QuestLogPanelError(f"{field} exceeds {maximum} code points")
    return _reject_lone_surrogates(value, field)


def _issuer_label(parsed: Any) -> str:
    """Resolve the commission display label for one parsed issuer key.

    A ``guild:`` key labels from the branch registry's display name; an
    ``npc:#<pk>`` key labels from the live commissioner's entity key (a
    database read, bounded to at most twelve rows per panel build); an
    authored ``npc:<key>`` key labels from the remainder directly, because
    the authored name is the entity key. Anything unresolvable falls back to
    the key's remainder rather than inventing a name.
    """
    fallback = parsed.remainder[:MAX_DISPLAY_NAME_CODE_POINTS]
    if parsed.namespace == "guild":
        branch = GUILD_BRANCH_REGISTRY.get(parsed.remainder)
        if branch is not None:
            return branch.display_name_zh[:MAX_DISPLAY_NAME_CODE_POINTS]
        return fallback
    if parsed.entity_pk is not None:
        from world.rules.possession import _resolve_live_object

        host = _resolve_live_object(parsed.entity_pk)
        if host is not None:
            return str(host.key)[:MAX_DISPLAY_NAME_CODE_POINTS]
    return fallback


def _track_descriptor() -> dict[str, Any]:
    """Build the always-enabled ``guild.quest_track`` action descriptor.

    Tracking is host-independent by contract, so the descriptor is always
    enabled and carries no disabled reason and no quantity bounds. The wire
    shape matches the services action descriptor exactly.
    """
    return {
        "action_id": TRACK_ACTION,
        "label": "追蹤",
        "enabled": True,
        "disabled_reason": None,
        "quantity": None,
    }


def _validate_issuer(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "quest_log issuer", {"kind", "key", "label"}, {})
    kind = value["kind"]
    if kind not in ("guild", "npc"):
        raise QuestLogPanelError("issuer kind must be guild or npc")
    key = _bounded_line(
        _require_str(value, "key", maximum=MAX_ISSUER_KEY_LENGTH),
        "issuer key",
        MAX_ISSUER_KEY_LENGTH,
    )
    label = _bounded_line(
        _require_str(value, "label", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "issuer label",
        MAX_DISPLAY_NAME_CODE_POINTS,
    )
    return {"kind": kind, "key": key, "label": label}


def _validate_track(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "quest_log track descriptor",
        {"action_id", "label", "enabled", "disabled_reason", "quantity"},
        {},
    )
    if value["action_id"] != TRACK_ACTION:
        raise QuestLogPanelError("quest_log track must be guild.quest_track")
    label = _bounded_line(
        _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS),
        "track label",
        MAX_LABEL_CODE_POINTS,
    )
    if not _require_bool(value, "enabled"):
        raise QuestLogPanelError("quest_log track is always enabled")
    if value["disabled_reason"] is not None:
        raise QuestLogPanelError("an enabled track must not carry a disabled_reason")
    if value["quantity"] is not None:
        raise QuestLogPanelError("quest_log track must not carry quantity bounds")
    return {
        "action_id": TRACK_ACTION,
        "label": label,
        "enabled": True,
        "disabled_reason": None,
        "quantity": None,
    }


def _validate_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "quest_log row",
        {
            "quest_id",
            "definition_key",
            "display_name",
            "state",
            "stage_index",
            "stage_total",
            "stage_progress",
            "objective_quantity",
            "objective_line",
            "deadline_line",
            "detail",
            "tracked",
            "issuer",
            "settlement",
            "reward_line",
            "track",
        },
        {},
    )
    quest_id = _bounded_line(
        _require_str(value, "quest_id", maximum=MAX_QUEST_ID_CODE_POINTS),
        "quest_id",
        MAX_QUEST_ID_CODE_POINTS,
    )
    definition_key = _bounded_line(
        _require_str(value, "definition_key", maximum=MAX_KEY_CODE_POINTS),
        "definition_key",
        MAX_KEY_CODE_POINTS,
    )
    display_name = _bounded_line(
        _require_str(value, "display_name", maximum=MAX_DISPLAY_NAME_CODE_POINTS),
        "quest_log display_name",
        MAX_DISPLAY_NAME_CODE_POINTS,
    )
    state = value["state"]
    if state not in QUEST_STATES:
        raise QuestLogPanelError("quest state is not a stable value")
    stage_index = _require_int(value, "stage_index", minimum=0, maximum=MAX_SAFE_INTEGER)
    stage_total = _require_int(value, "stage_total", minimum=1, maximum=MAX_SAFE_INTEGER)
    stage_progress = _require_int(value, "stage_progress", minimum=0, maximum=MAX_SAFE_INTEGER)
    objective_quantity = _require_int(
        value, "objective_quantity", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    objective_line = _bounded_line(
        _require_str(value, "objective_line", maximum=MAX_OBJECTIVE_LINE_CODE_POINTS),
        "objective_line",
        MAX_OBJECTIVE_LINE_CODE_POINTS,
    )
    deadline_line = value["deadline_line"]
    if deadline_line is not None:
        deadline_line = _bounded_line(
            _require_str(value, "deadline_line", maximum=MAX_DEADLINE_LINE_CODE_POINTS),
            "deadline_line",
            MAX_DEADLINE_LINE_CODE_POINTS,
        )
    detail = _bounded_line(
        _require_str(value, "detail", maximum=MAX_DETAIL_CODE_POINTS),
        "detail",
        MAX_DETAIL_CODE_POINTS,
    )
    tracked = _require_bool(value, "tracked")
    issuer = _validate_issuer(value["issuer"])
    settlement = value["settlement"]
    if settlement is not None and settlement not in _SETTLEMENT_VALUES:
        raise QuestLogPanelError("settlement is not a stable value")
    reward_line = value["reward_line"]
    if reward_line is not None:
        reward_line = _bounded_line(
            _require_str(value, "reward_line", maximum=MAX_SUMMARY_CODE_POINTS),
            "reward_line",
            MAX_SUMMARY_CODE_POINTS,
        )
    track = _validate_track(value["track"])
    return {
        "quest_id": quest_id,
        "definition_key": definition_key,
        "display_name": display_name,
        "state": state,
        "stage_index": stage_index,
        "stage_total": stage_total,
        "stage_progress": stage_progress,
        "objective_quantity": objective_quantity,
        "objective_line": objective_line,
        "deadline_line": deadline_line,
        "detail": detail,
        "tracked": tracked,
        "issuer": issuer,
        "settlement": settlement,
        "reward_line": reward_line,
        "track": track,
    }


def validate_quest_log(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``quest_log`` payload.

    Returns a normalized payload or raises :class:`QuestLogPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload, "quest_log panel", {"schema_version", "available", "rows"}, {}
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != QUEST_LOG_SCHEMA_VERSION:
        raise QuestLogPanelError("unsupported quest_log schema_version")
    if not _require_bool(payload, "available"):
        raise QuestLogPanelError("available must be true for the quest_log form")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) > QUEST_LOG_MAX_ROWS:
        raise QuestLogPanelError(
            f"rows must be a list of at most {QUEST_LOG_MAX_ROWS} entries"
        )
    validated = [_validate_row(row) for row in rows]
    quest_ids = [row["quest_id"] for row in validated]
    if len(set(quest_ids)) != len(quest_ids):
        raise QuestLogPanelError("quest_log quest_ids must be unique")
    result = {
        "schema_version": QUEST_LOG_SCHEMA_VERSION,
        "available": True,
        "rows": validated,
    }
    # Envelope guarantee (the shared per-panel closing check): an over-limit
    # payload can only come from a producer bug and fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise QuestLogPanelError("quest_log payload exceeds the OOB envelope limit")
    return result


def quest_log_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``quest_log`` panel for the puppet.

    Any puppeted explorer receives the panel regardless of the local room
    contents — the player's own quest book is readable anywhere, for
    exploration and combat puppets alike. Creation-pending puppets and
    unreadable canonical state (absent world clock, corrupt quest log) raise
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
    rows: list[dict[str, Any]] = []
    for record in records:
        if len(rows) >= QUEST_LOG_MAX_ROWS:
            # Stored-order truncation at the shared row cap (the services
            # quest-row precedent); the validator still rejects an over-cap
            # producer payload.
            break
        definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        if definition is None:  # pragma: no cover — read_records validates this
            raise PanelUnavailableError
        stage = definition.stages[record.stage_index]
        parsed = parse_issuer_key(record.issuer_key)
        issuance = resolve_issuance(record.definition_key, record.issuer_key)
        if issuance is not None:
            settlement: str | None = issuance.settlement.value
            reward_line: str | None = describe_reward(issuance)
        else:
            # An unresolvable issuance degrades the row's commission
            # disclosure, never the panel: the quest is still real and still
            # completable, so no reward or settlement may be invented.
            settlement = None
            reward_line = None
        rows.append(
            {
                "quest_id": record.quest_id,
                "definition_key": record.definition_key,
                "display_name": definition.display_name[
                    :MAX_DISPLAY_NAME_CODE_POINTS
                ],
                "state": record.state.value,
                "stage_index": record.stage_index,
                "stage_total": len(definition.stages),
                "stage_progress": record.stage_progress,
                "objective_quantity": stage.objective.quantity,
                "objective_line": describe_objective(stage.objective),
                "deadline_line": describe_deadline(record.deadline_tick, tick),
                "detail": describe_quest_detail(record, definition, issuance, tick),
                "tracked": record.tracked,
                "issuer": {
                    "kind": parsed.namespace,
                    "key": record.issuer_key,
                    "label": _issuer_label(parsed),
                },
                "settlement": settlement,
                "reward_line": reward_line,
                "track": _track_descriptor(),
            }
        )
    return validate_quest_log(
        {
            "schema_version": QUEST_LOG_SCHEMA_VERSION,
            "available": True,
            "rows": rows,
        }
    )


__all__ = [
    "QUEST_LOG_MAX_ROWS",
    "QUEST_LOG_SCHEMA_VERSION",
    "QuestLogPanelError",
    "quest_log_presenter",
    "validate_quest_log",
]
