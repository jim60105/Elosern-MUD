# event-log-compression Specification

## Purpose
TBD - created by archiving change overwhelm-resolution. Update Purpose after archive.
## Requirements
### Requirement: compress_event_logs drops redundant hit rolls and preserves miss and damage records
`world/rules/overwhelm.py` SHALL provide `compress_event_logs(raw_logs, overwhelming_team,
overwhelmed_team, rounds) -> tuple[EventLog, ...]`. For every input `EventLog`, every `EventEntry`
whose `kind` equals `"roll"` and whose `data["hit"]` is truthy SHALL be removed because its successful
outcome is duplicated by a paired `"damage"` entry. A `"roll"` entry whose `data["hit"]` is false
SHALL be retained because the landed action pipeline emits no damage entry for a miss. Every other
`EventEntry` SHALL be preserved unchanged, in its original order, via `dataclasses.replace()` on the
parent `EventLog` (never a live mutation of a frozen instance). `world/rules/event_log.py`'s
`EventEntry`/`EventLog` dataclass definitions SHALL NOT be modified.

#### Scenario: A successful roll-kind entry is removed
- **WHEN** `compress_event_logs()` processes an `EventLog` containing an `EventEntry` with
  `kind="roll"` and `data["hit"] is True`
- **THEN** the returned, corresponding `EventLog`'s `entries` does not contain that entry

#### Scenario: A miss roll survives unchanged
- **WHEN** `compress_event_logs()` processes an `EventLog` containing a `kind="roll"` entry with
  `data["hit"] is False`
- **THEN** the returned `EventLog`'s `entries` contains that exact entry, unchanged

#### Scenario: An EventLog left with no entries after filtering is dropped from the result
- **WHEN** every `EventEntry` in a given input `EventLog` is a successful `kind == "roll"` entry
- **THEN** that `EventLog` does not appear in `compress_event_logs()`'s returned tuple

#### Scenario: No edit to event_log.py's dataclasses
- **WHEN** `world/rules/event_log.py`'s source is inspected before and after this change lands
- **THEN** the file is byte-identical — `compress_event_logs()` constructs and transforms `EventEntry`/
  `EventLog` instances entirely through their existing public constructors and `dataclasses.replace()`

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
filtered per-action `EventLog` from the input — compression SHALL NOT reduce the individually
attributable hit/miss/damage record to only the aggregate summary.

#### Scenario: Every individual hit remains attributable to its actor and target after compression
- **WHEN** `compress_event_logs()`'s output is inspected for an encounter where entity `elosia` hit
  entity `violet` twice
- **THEN** two `"damage"`-kind `EventEntry` instances with `actor="elosia"` and `target="violet"` are
  present in the output, in addition to the aggregate summary entry

#### Scenario: The output is strictly no larger, and typically smaller, than the uncompressed input
- **WHEN** the total `EventEntry` count across `compress_event_logs()`'s returned tuple is compared
  against the total `EventEntry` count across its `raw_logs` input
- **THEN** the compressed count is less than or equal to the input count minus the number of
  redundant successful `"roll"`-kind entries removed, plus exactly one (the summary entry)

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

