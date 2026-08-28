# event-log-compression Specification

## Purpose
TBD - created by archiving change overwhelm-resolution. Update Purpose after archive.
## Requirements
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
When `commanded_actor`, `commanded_action_kind` (`"skill"` or `"item"`), `commanded_action_key`,
and `commanded_window` are all provided, `compress_event_logs()` SHALL prepend exactly one
`EventEntry` with `kind="commanded_action"` to the first `EventLog` **within `commanded_window`**
(the encounter's round-1 log slice) whose `actor` equals `commanded_actor` and whose `skill_key`
equals `commanded_action_key`, in window order. An `"item"` marker additionally requires the
candidate `EventLog` to carry an `item_used` entry for the commanded actor; a `"skill"` marker
matches any skill-produced log. The entry's `actor` SHALL be `commanded_actor`, its `target` SHALL
be `None`, and its `data` SHALL carry the resolved display label — under `"skill"` for skill
markers (from `SKILL_REGISTRY`) or `"item"` for item markers (from the item registry's
`display_name_zh`) — falling back to the raw key when the registry entry is unknown (never raising
for a pure-presentation entry). Its `text_template` SHALL render as `你施展了「{data[skill]}」。`
for skill markers and `你使用了「{data[item]}」。` for item markers. The marker SHALL be applied at
most once; when no `EventLog` in the window matches, no marker SHALL be added; when any of the four
keyword arguments is omitted or `commanded_action_kind` is not `skill` or `item`, no marker SHALL be
added. The marker SHALL NOT alter any other entry, the parent `EventLog`'s `time_cost_seconds`, or
the summary aggregation, and it SHALL NOT replace the commanded action's own entries.

#### Scenario: The commanded action's EventLog carries the marker
- **WHEN** `compress_event_logs()` processes an encounter where the player commanded `fire_ball`
  and later auto `basic_attack` logs follow, with `commanded_actor`,
  `commanded_action_kind="skill"`, `commanded_action_key`, and a `commanded_window` covering the
  encounter's first round
- **THEN** the first `EventLog` in the window with `actor == commanded_actor` and
  `skill_key == "fire_ball"` has a `commanded_action` entry prepended to its entries, and no later
  log is marked

#### Scenario: A commanded item use carries a separate item marker
- **WHEN** `compress_event_logs()` processes a compressed encounter whose round-1 window contains
  the player's `item_used` `EventLog` and the command identity is
  `commanded_action_kind="item"`, `commanded_action_key="healing_potion"`
- **THEN** exactly one `commanded_action` entry with `data["item"]` set to the item's display name
  is prepended to that `EventLog`, the `item_used` entry itself is unchanged, and no other log is
  marked

#### Scenario: An invalidated round-1 command produces no marker
- **WHEN** the player commanded `basic_attack` but its round-1 execution produced no `EventLog`
  (in-round invalidation), so the only matching `(actor, skill_key)` log is a round-2 auto basic
  attack outside `commanded_window`
- **THEN** no `commanded_action` entry appears anywhere in the returned tuple

#### Scenario: Default calls add no marker
- **WHEN** `compress_event_logs()` is called without `commanded_actor`, `commanded_action_kind`,
  `commanded_action_key`, or `commanded_window`
- **THEN** the returned tuple contains no `commanded_action` entry

#### Scenario: The marker renders as a player-perspective line
- **WHEN** `render_plain_text()` is called on the marked `EventLog` of a `basic_attack` command
- **THEN** the rendered text opens with `你施展了「基本攻擊」。` followed by the commanded action's
  own roll and damage lines

### Requirement: compress_event_logs prepends one overwhelm_resolution summary entry aggregating the
compressed encounter
`compress_event_logs()` SHALL prepend exactly one new `EventLog` whose single `EventEntry` has
`kind="overwhelm_resolution"`, `actor` equal to `overwhelming_team`, `target` equal to
`overwhelmed_team`, and `data` containing at least `rounds`, `hits` (count of `"damage"`-kind entries
across the filtered input), and `total_damage` (sum of those entries' `amount` fields).

#### Scenario: The summary entry's data reflects the actual filtered hits and damage
- **WHEN** `compress_event_logs()` processes input logs containing three `"damage"`-kind entries with
  amounts 10, 15, and 5, plus one retained miss-roll entry
- **THEN** the summary entry's `data["hits"] == 3` and `data["total_damage"] == 30`

#### Scenario: The summary entry carries no additional time cost
- **WHEN** the summary `EventLog`'s `time_cost_seconds` is inspected
- **THEN** it is `0` — the real elapsed time is already accounted for by the constituent per-action
  `EventLog`s this change did not alter

#### Scenario: The summary entry's actor and target are team keys, not entity keys
- **WHEN** the summary `EventLog`'s `entries[0].actor` and `.target` are inspected
- **THEN** they equal the `overwhelming_team` and `overwhelmed_team` arguments exactly, which are
  `Battlefield.teams` keys, not individual entity keys — distinguishing this entry from every other
  `EventEntry` this project's `EventLog` consumers have seen so far

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

### Requirement: A compressed EventLog renders through render_plain_text with no LLM involvement
Every `EventLog` `compress_event_logs()` returns, including the summary entry, SHALL render correctly
through change 8's existing `event_log.render_plain_text()` with zero network calls and zero imports
from any `world/ai/` module.

#### Scenario: The summary entry's text_template renders with dict-key data access
- **WHEN** `render_plain_text()` is called on the summary `EventLog`
- **THEN** it returns a string with every `{data[...]}` placeholder in the entry's `text_template`
  resolved to the corresponding `data` value, with no unresolved `{...}` remaining and no import of any
  `world/ai/` module

#### Scenario: Joining every returned EventLog reproduces the whole compressed encounter as prose
- **WHEN** `render_plain_text()` is called on each `EventLog` in `compress_event_logs()`'s returned
  tuple and the results are joined with newlines, in tuple order
- **THEN** the joined string opens with the aggregate summary sentence followed by the individual
  per-hit sentences, with no model call anywhere in the process

#### Scenario: Rendering is a pure, repeatable function of the compressed log
- **WHEN** `render_plain_text()` is called twice on the same compressed `EventLog`
- **THEN** both calls return byte-identical output

