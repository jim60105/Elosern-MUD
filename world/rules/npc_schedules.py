"""NPC schedule data model: rulebook templates, per-NPC storage, assignment.

This module owns the deterministic NPC schedule *data contract* only
(OpenSpec change ``npc-schedule-model``): the ``rulebook/npc_schedules.yaml``
template table, the two validated storage shapes of ``npc.db.schedule``, the
sole assignment API, the consumer-side parser, and the idempotent startup
synchronization. Nothing here settles schedules, moves NPCs, or gates
interactions -- the companion ``npc-schedule-runtime`` change consumes this
model.

Storage contract
----------------
``npc.db.schedule`` holds exactly one of:

- ``None`` -- no schedule (the default for every NPC);
- a template reference ``{"schema_version": 1, "template": <key>,
  "overrides": {...}}`` (``overrides`` optional, keyed by string-form entry
  index); or
- a full custom list ``{"schema_version": 1, "entries": [...]}``.

``set_npc_schedule`` is the sole writer of the attribute: it validates the
schedule, records ``npc.db.schedule_effective_from_tick`` (the assignment
world tick, so a mid-day assignment never replays already-passed
occurrences), and maintains a persistent ``schedule`` tag so settlement finds
every schedule-bearing NPC regardless of spawn time. Consumers read through
``parse_stored_schedule``; a malformed stored value resolves to "no schedule"
with a bounded diagnostic, never an exception.

Runtime-state contract
----------------------
``npc.db.schedule_state`` is the single runtime-state attribute holding the
NPC's current schedule state value or ``None`` when no state is active. This
module declares the contract and never writes it; every write belongs to the
``npc-schedule-runtime`` change.
"""

from collections.abc import Mapping, MutableSequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from evennia.utils.logger import log_err, log_warn

from typeclasses.npcs import NPC
from world.rules.clock import CLOCK_YAML, get_world_clock

SCHEMA_VERSION = 1
SCHEDULE_TAG = "schedule"
MAX_ENTRIES = 48
_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
_ENTRY_FIELDS = frozenset({"tick_offset", "kind", "target", "state"})
_KINDS = ("move", "state")


class ScheduleError(ValueError):
    """Base class for every NPC-schedule model violation."""


class ScheduleRulebookError(ScheduleError):
    """The shipped schedule rulebook violates the data contract."""


class ScheduleShapeError(ScheduleError):
    """A per-NPC schedule storage shape is malformed."""


class ScheduleEntryError(ScheduleError):
    """An individual schedule entry violates the entry shape rules."""


class ScheduleTemplateError(ScheduleError):
    """A template reference or override cannot be resolved."""


@dataclass(frozen=True)
class ScheduleEntry:
    """One scheduled occurrence: a movement or a state change.

    ``kind`` is ``move`` or ``state``; a ``move`` entry carries ``target``
    (resolved through the lore registries by the runtime) and a ``state``
    entry carries a ``state`` value from the rulebook vocabulary. Entries
    repeat every world day at ``tick_offset`` seconds after the day start.
    """

    tick_offset: int
    kind: str
    target: str | None = None
    state: str | None = None


@dataclass(frozen=True)
class ScheduleTemplate:
    """One immutable role template from the schedule rulebook."""

    key: str
    entries: tuple[ScheduleEntry, ...]
    default_state: str | None = None


@dataclass(frozen=True)
class ScheduleRulebook:
    """The validated schedule rulebook singleton."""

    schema_version: int
    states: tuple[str, ...]
    templates: tuple[ScheduleTemplate, ...]

    def template_by_key(self, key: str) -> ScheduleTemplate | None:
        """Return the template carrying ``key``, or ``None``."""
        for template in self.templates:
            if template.key == key:
                return template
        return None


@dataclass(frozen=True)
class ParsedSchedule:
    """One NPC's validated, resolved schedule.

    ``entries`` are concrete; a template reference is already merged with its
    overrides. ``default_state`` is the referenced template's default state
    (``None`` for full custom lists). ``effective_from_tick`` is the world
    tick recorded at assignment; occurrences due before it never settle.
    """

    entries: tuple[ScheduleEntry, ...]
    default_state: str | None = None
    effective_from_tick: int | None = None


def _rulebook_error(message: str) -> ScheduleRulebookError:
    return ScheduleRulebookError(f"npc_schedules.yaml: {message}")


def _validate_entry(raw: Any, *, context: str) -> ScheduleEntry:
    """Validate one entry's shape and return it as a frozen record.

    Raises :class:`ScheduleEntryError` on any shape violation. Vocabulary
    membership of a ``state`` value is checked by the caller, which knows the
    rulebook's declared states.
    """
    if not isinstance(raw, Mapping):
        raise ScheduleEntryError(f"{context}: entry must be a mapping")
    raw = dict(raw)
    unknown = set(raw) - _ENTRY_FIELDS
    if unknown:
        raise ScheduleEntryError(f"{context}: unknown entry fields {sorted(unknown)}")
    missing = {"tick_offset", "kind"} - set(raw)
    if missing:
        raise ScheduleEntryError(f"{context}: missing entry fields {sorted(missing)}")
    tick_offset = raw["tick_offset"]
    if isinstance(tick_offset, bool) or not isinstance(tick_offset, int):
        raise ScheduleEntryError(f"{context}: tick_offset must be an integer")
    if not 0 <= tick_offset < _DAY_SECONDS:
        raise ScheduleEntryError(
            f"{context}: tick_offset must be in [0, {_DAY_SECONDS}), got {tick_offset!r}"
        )
    kind = raw["kind"]
    if kind not in _KINDS:
        raise ScheduleEntryError(
            f"{context}: kind must be one of {list(_KINDS)}, got {kind!r}"
        )
    if kind == "move":
        if "state" in raw:
            raise ScheduleEntryError(f"{context}: a move entry must not carry a state field")
        target = raw.get("target")
        if not isinstance(target, str) or not target.strip():
            raise ScheduleEntryError(f"{context}: a move entry requires a non-empty target")
        return ScheduleEntry(tick_offset=int(tick_offset), kind=kind, target=target)
    if "target" in raw:
        raise ScheduleEntryError(f"{context}: a state entry must not carry a target field")
    state = raw.get("state")
    if not isinstance(state, str) or not state.strip():
        raise ScheduleEntryError(f"{context}: a state entry requires a non-empty state")
    return ScheduleEntry(tick_offset=int(tick_offset), kind=kind, state=state)


def _check_state_vocabulary(
    entries: tuple[ScheduleEntry, ...], states: tuple[str, ...], *, context: str
) -> None:
    """Reject any state-entry value outside the declared vocabulary."""
    for entry in entries:
        if entry.kind == "state" and entry.state not in states:
            raise ScheduleEntryError(
                f"{context}: state {entry.state!r} is not in the state vocabulary"
            )


def _load_states(raw_states: Any) -> tuple[str, ...]:
    if not isinstance(raw_states, list):
        raise _rulebook_error("states must be a list")
    if not raw_states:
        raise _rulebook_error("states must not be empty")
    states: list[str] = []
    for position, value in enumerate(raw_states, start=1):
        if not isinstance(value, str) or not value.strip():
            raise _rulebook_error(f"states[{position}] must be a non-empty string")
        if value in states:
            raise _rulebook_error(f"duplicate state {value!r}")
        states.append(value)
    return tuple(states)


def _load_templates(
    raw_templates: Any, states: tuple[str, ...]
) -> tuple[ScheduleTemplate, ...]:
    if not isinstance(raw_templates, Mapping):
        raise _rulebook_error("templates must be a mapping")
    templates: list[ScheduleTemplate] = []
    for key, value in raw_templates.items():
        if not isinstance(key, str) or not key.strip():
            raise _rulebook_error("template keys must be non-empty strings")
        if not isinstance(value, Mapping):
            raise _rulebook_error(f"template {key!r} must be a mapping")
        value = dict(value)
        unknown = set(value) - {"default_state", "entries"}
        if unknown:
            raise _rulebook_error(f"template {key!r} has unknown fields {sorted(unknown)}")
        entries_raw = value.get("entries")
        if not isinstance(entries_raw, list):
            raise _rulebook_error(f"template {key!r} requires an entries list")
        if not entries_raw:
            raise _rulebook_error(f"template {key!r} entries must not be empty")
        if len(entries_raw) > MAX_ENTRIES:
            raise _rulebook_error(f"template {key!r} exceeds {MAX_ENTRIES} entries")
        entries = tuple(
            _validate_entry(entry, context=f"templates.{key}") for entry in entries_raw
        )
        _check_state_vocabulary(entries, states, context=f"templates.{key}")
        default_state = value.get("default_state")
        if default_state is not None:
            if not isinstance(default_state, str) or not default_state.strip():
                raise _rulebook_error(
                    f"template {key!r} default_state must be a non-empty string"
                )
            if default_state not in states:
                raise _rulebook_error(
                    f"template {key!r} default_state {default_state!r} is not in "
                    "the state vocabulary"
                )
        templates.append(
            ScheduleTemplate(key=key, entries=entries, default_state=default_state)
        )
    return tuple(templates)


def load_rulebook(path: Path | None = None) -> ScheduleRulebook:
    """Load and validate the schedule rulebook, failing closed on deviation.

    Every load failure -- unreadable or invalid-YAML file, unknown schema,
    malformed vocabulary or template, or a rulebook entry violating the entry
    shape rules -- raises :class:`ScheduleRulebookError` with a bounded
    message, never any other exception type. ``path`` overrides the canonical
    rulebook location; tests exercise deviant rulebooks through a temporary
    copy so the shared source file is never rewritten, which keeps parallel
    workers from racing on the file.
    """
    rulebook_path = (
        Path(__file__).parent / "rulebook" / "npc_schedules.yaml"
        if path is None
        else path
    )
    try:
        text = rulebook_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _rulebook_error(f"cannot read {rulebook_path}: {exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise _rulebook_error(f"invalid YAML: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise _rulebook_error("rulebook must be a mapping")
    raw = dict(raw)
    top_level_fields = {"schema_version", "states", "templates"}
    unknown = set(raw) - top_level_fields
    if unknown:
        raise _rulebook_error(f"unknown top-level fields {sorted(unknown)}")
    missing = top_level_fields - set(raw)
    if missing:
        raise _rulebook_error(f"missing top-level fields {sorted(missing)}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise _rulebook_error(
            f"schema_version must be {SCHEMA_VERSION}, got {raw['schema_version']!r}"
        )
    try:
        states = _load_states(raw["states"])
        templates = _load_templates(raw["templates"], states)
    except ScheduleEntryError as exc:
        raise _rulebook_error(str(exc)) from exc
    if not templates:
        raise _rulebook_error("templates must contain at least one template")
    return ScheduleRulebook(
        schema_version=SCHEMA_VERSION,
        states=states,
        templates=templates,
    )


_RULEBOOK: ScheduleRulebook | None = None


def get_rulebook() -> ScheduleRulebook:
    """Return the validated schedule rulebook singleton."""
    global _RULEBOOK
    if _RULEBOOK is None:
        _RULEBOOK = load_rulebook()
    return _RULEBOOK


def _entry_as_dict(entry: ScheduleEntry) -> dict[str, Any]:
    fields: dict[str, Any] = {"tick_offset": entry.tick_offset, "kind": entry.kind}
    if entry.target is not None:
        fields["target"] = entry.target
    if entry.state is not None:
        fields["state"] = entry.state
    return fields


def _apply_overrides(
    template: ScheduleTemplate,
    overrides: Any,
    states: tuple[str, ...],
) -> tuple[ScheduleEntry, ...]:
    """Merge a shallow per-entry override mapping into a template.

    Override keys are string-form entry indices into the template's list;
    fields not mentioned in an override keep template values, and the merged
    entry is re-validated under the same entry rules. A key that does not
    correspond to an entry index rejects with a named error.
    """
    if overrides is None:
        return template.entries
    if not isinstance(overrides, Mapping):
        raise ScheduleShapeError("overrides must be a mapping")
    if not overrides:
        return template.entries
    valid_indices = {str(index) for index in range(len(template.entries))}
    for key in overrides:
        if key not in valid_indices:
            raise ScheduleTemplateError(
                f"override references missing entry index {key!r}"
            )
    merged: list[ScheduleEntry] = []
    for index, base_entry in enumerate(template.entries):
        fields = _entry_as_dict(base_entry)
        if str(index) in overrides:
            override = overrides[str(index)]
            if not isinstance(override, Mapping):
                raise ScheduleTemplateError(f"override {index!r} must be a mapping")
            fields.update(dict(override))
        merged.append(_validate_entry(fields, context=f"overrides.{index}"))
    _check_state_vocabulary(tuple(merged), states, context="overrides")
    return tuple(merged)


def _load_custom_entries(
    raw_entries: Any, states: tuple[str, ...], *, context: str
) -> tuple[ScheduleEntry, ...]:
    if not isinstance(raw_entries, MutableSequence):
        raise ScheduleShapeError(f"{context} must be a list")
    if not raw_entries:
        raise ScheduleShapeError(f"{context} must not be empty")
    if len(raw_entries) > MAX_ENTRIES:
        raise ScheduleShapeError(f"{context} exceeds {MAX_ENTRIES} entries")
    entries = tuple(_validate_entry(entry, context=context) for entry in raw_entries)
    _check_state_vocabulary(entries, states, context=context)
    return entries


def resolve_schedule(
    raw: Any, *, effective_from_tick: int | None = None
) -> ParsedSchedule:
    """Validate one per-NPC schedule and resolve it to concrete entries.

    Accepts exactly the two documented storage shapes (template reference
    with optional overrides, or a full custom entry list) and raises a named
    :class:`ScheduleError` subclass on any deviation. The consumer-side
    parser and the startup sync convert those exceptions into a no-schedule
    degradation.
    """
    if not isinstance(raw, Mapping):
        raise ScheduleShapeError("schedule must be a mapping or None")
    raw = dict(raw)
    unknown = set(raw) - {"schema_version", "template", "overrides", "entries"}
    if unknown:
        raise ScheduleShapeError(f"unknown schedule fields {sorted(unknown)}")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ScheduleShapeError(
            f"schema_version must be {SCHEMA_VERSION}, got {raw.get('schema_version')!r}"
        )
    has_template = "template" in raw
    has_entries = "entries" in raw
    if has_template and has_entries:
        raise ScheduleShapeError("schedule must not carry both template and entries")
    if not has_template and "overrides" in raw:
        raise ScheduleShapeError("overrides require a template reference")
    rulebook = get_rulebook()
    if has_template:
        template_key = raw["template"]
        if not isinstance(template_key, str) or not template_key.strip():
            raise ScheduleShapeError("template must be a non-empty string key")
        template = rulebook.template_by_key(template_key)
        if template is None:
            raise ScheduleTemplateError(f"unknown template key {template_key!r}")
        entries = _apply_overrides(template, raw.get("overrides"), rulebook.states)
        return ParsedSchedule(
            entries=entries,
            default_state=template.default_state,
            effective_from_tick=effective_from_tick,
        )
    if has_entries:
        entries = _load_custom_entries(raw["entries"], rulebook.states, context="entries")
        return ParsedSchedule(
            entries=entries, effective_from_tick=effective_from_tick
        )
    raise ScheduleShapeError("schedule requires a template reference or an entries list")


def _bounded_diagnostic(message: str, limit: int = 200) -> str:
    """Truncate a diagnostic so a corrupted stored value cannot flood the log."""
    return message if len(message) <= limit else f"{message[:limit]}..."


def _stored_schedule_error(npc: Any) -> str | None:
    """Return a bounded diagnostic for one NPC's stored schedule unit, or ``None``.

    The stored unit is the ``db.schedule`` value plus its freshness metadata
    ``db.schedule_effective_from_tick``; both must come from the validated
    assignment API. A ``None`` schedule is valid. Otherwise the schedule
    shape is validated with the same parser as the API and the effective tick
    must be a non-boolean integer; any deviation returns the diagnostic.
    """
    raw = npc.db.schedule
    if raw is None:
        return None
    try:
        resolve_schedule(raw)
    except ScheduleError as exc:
        return _bounded_diagnostic(str(exc))
    effective = npc.db.schedule_effective_from_tick
    if isinstance(effective, bool) or not isinstance(effective, int):
        return "schedule_effective_from_tick must be an integer recorded by set_npc_schedule"
    return None


def set_npc_schedule(npc: Any, schedule: Any) -> None:
    """Assign or clear an NPC's schedule -- the sole writer of ``npc.db.schedule``.

    ``schedule`` must be ``None`` (clear) or one of the two validated storage
    shapes; anything else raises a named :class:`ScheduleError` subclass
    before any state is written. A successful assignment records
    ``npc.db.schedule_effective_from_tick`` as the current world tick and
    adds the persistent ``schedule`` tag; ``None`` clears the attribute, the
    recorded tick, and the tag.
    """
    if schedule is None:
        npc.db.schedule = None
        npc.db.schedule_effective_from_tick = None
        npc.tags.remove(SCHEDULE_TAG)
        return
    resolve_schedule(schedule)
    npc.db.schedule = schedule
    npc.db.schedule_effective_from_tick = get_world_clock().tick
    npc.tags.add(SCHEDULE_TAG)


def parse_stored_schedule(npc: Any) -> ParsedSchedule | None:
    """Parse one NPC's stored schedule; a malformed value resolves to ``None``.

    This is the consumer-side entry point: settlement and any other reader
    validates with the same parser as the assignment API, plus the effective
    tick recorded at assignment. A malformed stored unit logs a bounded
    diagnostic and returns ``None`` (the canonical no-schedule marker)
    instead of raising.
    """
    raw = npc.db.schedule
    if raw is None:
        return None
    diagnostic = _stored_schedule_error(npc)
    if diagnostic is not None:
        log_warn(
            f"npc_schedules: {npc.key or '?'} has a malformed schedule "
            f"({diagnostic}); treating as no schedule"
        )
        return None
    return resolve_schedule(raw, effective_from_tick=npc.db.schedule_effective_from_tick)


def _clear_schedule(npc: Any, diagnostic: str) -> None:
    """Log and degrade one NPC to the canonical no-schedule state."""
    log_warn(
        f"npc_schedules: {npc.key or '?'} has a malformed schedule "
        f"({_bounded_diagnostic(diagnostic)}); treating as no schedule"
    )
    npc.db.schedule = None
    npc.db.schedule_effective_from_tick = None
    npc.tags.remove(SCHEDULE_TAG)


def _sync_npc_schedules() -> None:
    """The sync pass proper; the public wrapper guarantees startup is never blocked."""
    try:
        get_rulebook()
    except Exception as exc:
        # The rulebook is data; a failure deactivates the whole schedule
        # layer without touching stored data, so fixing the file and
        # restarting re-enables every schedule. The tags are the runtime's
        # index -- without them no NPC is found by settlement.
        log_err(
            f"npc_schedules: rulebook failed to load ({_bounded_diagnostic(str(exc))}); "
            "deactivating every NPC schedule until it loads"
        )
        for npc in NPC.objects.all_family():
            try:
                if npc.tags.has(SCHEDULE_TAG):
                    npc.tags.remove(SCHEDULE_TAG)
            except Exception:
                log_warn(
                    f"npc_schedules: could not clear the schedule tag on {npc.key or '?'}"
                )
        return
    for npc in NPC.objects.all_family():
        try:
            raw = npc.db.schedule
            if raw is None:
                if npc.tags.has(SCHEDULE_TAG):
                    log_warn(
                        f"npc_schedules: {npc.key or '?'} carries a stale schedule tag "
                        "without a schedule; removing it"
                    )
                    npc.tags.remove(SCHEDULE_TAG)
                continue
            diagnostic = _stored_schedule_error(npc)
            if diagnostic is not None:
                _clear_schedule(npc, diagnostic)
                continue
            if not npc.tags.has(SCHEDULE_TAG):
                npc.tags.add(SCHEDULE_TAG)
        except Exception as exc:
            # One NPC's persistence failure must never stall the pass.
            log_warn(
                f"npc_schedules: could not synchronize {npc.key or '?'} "
                f"({_bounded_diagnostic(str(exc))}); leaving it unchanged"
            )


def sync_npc_schedules() -> None:
    """Idempotently confirm the rulebook, every NPC's schedule, and the tag.

    Loads and validates the rulebook once; a failure deactivates the whole
    layer (every ``schedule`` tag is removed, stored data is preserved and
    re-enabled by the next successful load). Otherwise every NPC is walked:

    - a ``None`` schedule with a stale ``schedule`` tag loses the tag;
    - a valid stored schedule unit (shape plus recorded effective tick) gains
      or keeps the ``schedule`` tag;
    - a malformed stored schedule unit logs a bounded diagnostic and degrades
      to the canonical no-schedule state (``db.schedule = None``, no tag).

    The pass never raises and never blocks startup -- a failure at any level
    is bounded, logged, and skipped; re-running it over valid data is a no-op.
    """
    try:
        _sync_npc_schedules()
    except Exception as exc:
        log_err(
            f"npc_schedules: startup sync aborted "
            f"({_bounded_diagnostic(str(exc))}); startup continues"
        )
