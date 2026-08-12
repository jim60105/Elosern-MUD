# event-log-compression Delta Specification

## REMOVED Requirements

### Requirement: compress_event_logs drops redundant hit rolls and preserves miss and damage records
**Reason**: Dropping successful `"roll"` entries removed the visible attack line for every hit in a
compressed overwhelm log, so a damage entry could appear to belong to a different attack than the one
that produced it — e.g. a commanded self-attack's miss roll followed by an auto-attack's damage on an
enemy read as a wrong target. The noise reduction was not worth breaking per-attack attribution.
**Migration**: Compressed logs now preserve every entry; consumers must not rely on successful hit
rolls being absent. The project has no released users, so no data migration is needed.

## MODIFIED Requirements

### Requirement: A full record of who hit whom, for how much, is preserved alongside the summary
The tuple `compress_event_logs()` returns SHALL contain, in addition to the summary entry, every
non-empty per-action `EventLog` from the input with every entry preserved — compression SHALL NOT
reduce the individually attributable hit/miss/damage record to only the aggregate summary, and SHALL
NOT remove any `"roll"` entry, including successful hits.

#### Scenario: Every individual hit remains attributable to its actor and target after compression
- **WHEN** `compress_event_logs()`'s output is inspected for an encounter where entity `elosia` hit
  entity `violet` twice
- **THEN** two `"damage"`-kind `EventEntry` instances with `actor="elosia"` and `target="violet"` are
  present in the output, in addition to the aggregate summary entry, and each damage entry is
  preceded in its parent `EventLog` by the matching successful `"roll"` entry, in original order

#### Scenario: The output size is the input size plus the summary and optional marker
- **WHEN** the total `EventEntry` count across `compress_event_logs()`'s returned tuple is compared
  against the total `EventEntry` count across its `raw_logs` input
- **THEN** the compressed count equals the input count plus exactly one (the summary entry), plus
  exactly one more when a commanded-action marker is applied

## ADDED Requirements

### Requirement: compress_event_logs preserves every attack record without kind-based filtering
`compress_event_logs(raw_logs, overwhelming_team, overwhelmed_team, rounds, commanded_actor=None,
commanded_skill=None, commanded_window=None) -> tuple[EventLog, ...]` SHALL preserve every
`EventEntry` of every input
`EventLog`, in its original order, via `dataclasses.replace()` on the parent `EventLog` (never a live
mutation of a frozen instance). No `EventEntry` SHALL be removed because of its `kind` or its
`data["hit"]` value. An input `EventLog` with zero entries SHALL NOT appear in the returned tuple.
`world/rules/event_log.py`'s `EventEntry`/`EventLog` dataclass definitions SHALL NOT be modified.

#### Scenario: A successful roll entry survives compression unchanged
- **WHEN** `compress_event_logs()` processes an `EventLog` containing an `EventEntry` with
  `kind="roll"` and `data["hit"] is True` followed by a paired `"damage"` entry
- **THEN** the returned, corresponding `EventLog`'s `entries` contain both entries, in the same
  order, byte-identical

#### Scenario: A miss roll survives unchanged
- **WHEN** `compress_event_logs()` processes an `EventLog` containing a `kind="roll"` entry with
  `data["hit"] is False`
- **THEN** the returned `EventLog`'s `entries` contains that exact entry, unchanged

#### Scenario: An EventLog with no entries is dropped from the result
- **WHEN** a given input `EventLog` has zero `EventEntry` instances
- **THEN** that `EventLog` does not appear in `compress_event_logs()`'s returned tuple

#### Scenario: No edit to event_log.py's dataclasses
- **WHEN** `world/rules/event_log.py`'s source is inspected before and after this change lands
- **THEN** the file is byte-identical — `compress_event_logs()` constructs and transforms `EventEntry`/
  `EventLog` instances entirely through their existing public constructors and `dataclasses.replace()`

### Requirement: compress_event_logs marks the player's commanded action with a commanded_action entry
When `commanded_actor`, `commanded_skill`, and `commanded_window` are all provided,
`compress_event_logs()` SHALL prepend exactly one `EventEntry` with `kind="commanded_action"` to the
first `EventLog` **within `commanded_window`** (the encounter's round-1 log slice) whose `actor`
equals `commanded_actor` and whose `skill_key` equals `commanded_skill`, in window order. The entry's
`actor` SHALL be `commanded_actor`, its `target` SHALL be `None`, and its `data` SHALL carry the
skill's display label under the `"skill"` key, resolved from `SKILL_REGISTRY` and falling back to the
raw key when the skill is unknown (never raising for a pure-presentation entry). Its `text_template`
SHALL render as `你施展了「{data[skill]}」。`. The marker SHALL be applied at most once; when no
`EventLog` in the window matches, no marker SHALL be added; when any of the three keyword arguments is
omitted, no marker SHALL be added. The marker SHALL NOT alter any other entry, the parent
`EventLog`'s `time_cost_seconds`, or the summary aggregation.

#### Scenario: The commanded action's EventLog carries the marker
- **WHEN** `compress_event_logs()` processes an encounter where the player commanded `fire_ball`
  and later auto `basic_attack` logs follow, with `commanded_actor`, `commanded_skill`, and a
  `commanded_window` covering the encounter's first round
- **THEN** the first `EventLog` in the window with `actor == commanded_actor` and
  `skill_key == "fire_ball"` has a `commanded_action` entry prepended to its entries, and no later
  log is marked

#### Scenario: An invalidated round-1 command produces no marker
- **WHEN** the player commanded `basic_attack` but its round-1 execution produced no `EventLog`
  (in-round invalidation), so the only matching `(actor, skill_key)` log is a round-2 auto basic
  attack outside `commanded_window`
- **THEN** no `commanded_action` entry appears anywhere in the returned tuple

#### Scenario: Default calls add no marker
- **WHEN** `compress_event_logs()` is called without `commanded_actor`, `commanded_skill`, or
  `commanded_window`
- **THEN** the returned tuple contains no `commanded_action` entry

#### Scenario: The marker renders as a player-perspective line
- **WHEN** `render_plain_text()` is called on the marked `EventLog` of a `basic_attack` command
- **THEN** the rendered text opens with `你施展了「基本攻擊」。` followed by the commanded action's own
  roll and damage lines
