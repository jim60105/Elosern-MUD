## ADDED Requirements

### Requirement: EventLog and EventEntry are frozen, serializable, entity-key-only records
`world/rules/event_log.py` SHALL define `EventEntry` and `EventLog` as frozen dataclasses whose fields
are plain JSON-compatible data (strings, dicts, tuples of the same) and entity **keys**, never live
entity references. `EventLog` SHALL only ever be constructed for a successfully committed
`ActionResolver.resolve()` call; a rejected action SHALL NOT produce an `EventLog`.

#### Scenario: EventLog round-trips through JSON with no live reference
- **WHEN** an `EventLog` produced by a successful `resolve()` call is serialized to JSON and
  deserialized back
- **THEN** the reconstructed object's fields are equal to the original, and no field anywhere in the
  structure holds a live entity object

#### Scenario: A rejected action never produces an EventLog
- **WHEN** `ActionResolver.resolve()` rejects at any pipeline step
- **THEN** the returned `ActionResult.event_log` is `None`

### Requirement: EventEntry.kind is an open convention, not a closed enum
`EventEntry.kind` SHALL be a plain string, not a fixed enum, so that later changes (combat rolls,
damage, overwhelm compression) can introduce new kind values without modifying `EventLog`'s or
`EventEntry`'s dataclass definitions. This change SHALL define and use at least: `resource_spend`,
`trait_delta`, `sexual_transition`, `buff_applied`, `skill_granted`, `disguise_set`.

#### Scenario: A new kind value requires no dataclass change
- **WHEN** a test constructs an `EventEntry` with a kind value this change does not itself use (e.g.
  `overwhelm_resolution`, standing in for change 10's future usage)
- **THEN** construction succeeds and `render_plain_text()` renders it using the same generic
  `text_template.format()` mechanism as every built-in kind

### Requirement: render_plain_text() renders an EventLog to prose with no LLM involvement
`world/rules/event_log.py` SHALL provide `render_plain_text(event_log: EventLog) -> str`, a pure
function that formats every `EventEntry.text_template` against that entry's own `actor`/`target`/`data`
fields and joins the results, with no network call, no prompt construction, and no dependency on any
`world/ai/` module.

#### Scenario: A conferral cast renders directly to prose with zero model calls
- **WHEN** `render_plain_text()` is called on an `EventLog` containing one `EventEntry(kind=
  "skill_granted", actor="elosia", target="violet", data={"skill_key": "dominion_art", "scale": 0.1},
  text_template="{actor} 對 {target} 施展了「統御術」的部分效果。")`
- **THEN** it returns exactly `"elosia 對 violet 施展了「統御術」的部分效果。"` with no import of, or
  call into, any `world/ai/` module

#### Scenario: Multiple entries render as multiple lines in order
- **WHEN** `render_plain_text()` is called on an `EventLog` with three ordered entries
- **THEN** the returned string contains each entry's rendered text on its own line, in the same order
  as `EventLog.entries`

### Requirement: EventLog is structured for combat compression and pure-function narration
`EventLog.entries` SHALL be a flat, ordered tuple, mergeable by simple concatenation across multiple
`resolve()` calls from the same encounter, so that a later change can summarize several EventLogs
(e.g. under an overwhelm resolution) into fewer, coarser entries without altering `EventLog`'s shape.
Nothing in `EventLog`'s construction SHALL require, or provide, a write API back into game state.

#### Scenario: Concatenating entries from two resolve() calls produces one valid, orderable sequence
- **WHEN** two successful `resolve()` calls each produce an `EventLog`, and their `entries` tuples are
  concatenated
- **THEN** the combined tuple is a valid, ordered sequence `render_plain_text()`-compatible logic can
  render identically to rendering each `EventLog` separately and joining the results

#### Scenario: EventLog exposes no method that mutates entity state
- **WHEN** every public method and property on `EventLog` and `EventEntry` is inspected
- **THEN** none of them accepts a live entity reference or performs an attribute write
