# event-log-compression delta

## MODIFIED Requirements

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
