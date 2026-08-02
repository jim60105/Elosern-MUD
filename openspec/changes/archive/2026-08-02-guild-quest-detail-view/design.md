## Context

Quest definitions are immutable, registry-backed `QuestDefinition` values
(`world/quests/definitions.py`); per-character records live as JSON-safe dicts
in `PlayerCharacter.db.quest_log` parsed by `world/quests/runtime.py`. The
player-facing guild commands (`commands/guild.py`) already expose registration,
board listing, acceptance, quest-log listing, abandonment, turn-in, and merit.
Today `guild log` prints only `quest_id [state] 階段 N`, and `guild list` prints
only `definition_key — display_name (銅 / 功績)`. Nothing shows what a quest
requires the player to do, so after accepting a quest the player cannot discover
its completion conditions. The deterministic introductory hunt
(`introductory_hunt`, DEFEAT 1× `low` tier) is invisible in-game as a goal.

## Goals / Non-Goals

**Goals:**

- Let a player inspect the full detail of one of their own quests from inside
  the game: display name, state, current stage, the current objective's
  Traditional Chinese description, progress, deadline (when present), and
  reward (when an offer exists for their branch).
- Let a player see, on the board, a one-line summary of each offer's objective
  before accepting.
- Keep the rendering read-only and unit-testable as pure logic, honoring the
  single-writer invariant (no module writes quest state here).

**Non-Goals:**

- No new quest-runtime or lifecycle APIs; `guild show` is pure presentation
  over existing `read_records`/definitions data.
- No support for change 20's generative `QuestBlueprint` proposals; rendering
  targets the deterministic `QuestDefinition` vocabulary only.
- No guild rank, reward-band, or examination changes.
- No multi-account or UI work.

## Decisions

**D1 — A new pure rendering module `world/quests/describe.py`.**
It renders `QuestObjective` and `RoomLocator` values into Traditional Chinese
prose and assembles a full detail text from a `QuestRecord` + `QuestDefinition`
+ optional offer + the current world tick. The tick is an explicit parameter
(`describe_quest_detail(record, definition, offer, current_tick)`), injected by
the command from `get_world_clock().tick`, so the renderer never reads the
clock itself and remains purely unit-testable with fixed ticks. It imports only
immutable registries (`world/quests/definitions.py`, `world/lore/*`,
`world/rules/clock.py` for `CLOCK_YAML` ratios) and performs no writes.

Deadline display is specified exactly: remaining seconds =
`deadline_tick - current_tick`, floored to whole hours when positive and not
expired; a non-positive remaining value renders an expired line ("已逾期");
`deadline_tick = None` omits the line entirely.

*Why over in-command f-strings:* the objective vocabulary
(`ObjectiveKind.DEFEAT/REACH/ESCORT/ACQUIRE`, `DestinationKind.ANCHOR/GRID/
BOUND_INSTANCE`) is a closed enum; an exhaustive pure function is directly
unit-testable per kind and keeps `commands/guild.py` thin. It also guarantees
the board one-liner and `guild show` render through the same code path.

**D2 — A new command `guild show <quest_id>` (aliases `guild 詳情`,
`guild detail`, `任務詳情`).**
It resolves the record through `world.quests.runtime.read_records` and the
definition through `definition_for` — the same read APIs `guild log` already
uses — and requires no local `GuildStaff` host, because the player is inspecting
their own log, not a service. The reward lookup uses exactly
`parse_guild_registration(actor)["branch_key"]` then
`get_guild_offer(definition_key, branch)`:
- unregistered actor (`parse_guild_registration` returns `None`) → reward
  section omitted;
- malformed `guild_registration` (raises `GuildDataError`) → Traditional
  Chinese error, no state change;
- `GuildOfferNotFound` → reward section omitted (never an error).
Error handling catches exactly `QuestNotFound`, `QuestDataError`, and the
`GuildDataError` case above — never a broad `except Exception` (unlike the
existing `CmdGuildLog`), so programming errors surface through the normal
logging path.

**D3 — Board and log output reuse the renderer.**
`guild list` appends a one-line objective summary for the offered definition's
stage-zero objective. `guild log` appends a hint (`用 guild show <quest_id>
查看詳情`) so the new surface is discoverable.

**D4 — Progress and deadline presentation.**
The detail text shows `stage_progress / quantity` for the current stage and the
deadline line per D1 (injected `current_tick`, floor-to-hours, expired line for
non-positive remaining, omitted for `None`).

## Risks / Trade-offs

- [Renderer drifts out of sync with the objective enum] → The renderer is
  exhaustive over `ObjectiveKind`/`DestinationKind` and covered by one pure test
  per kind; an unknown kind raises so tests surface drift loudly.
- [Deadline math depends on the world clock] → The clock is injected as a
  parameter, so every display rule (remaining, expired, floored hours, omitted)
  is a fixed-tick pure test with no hidden timing.
- [Reward lookup depends on the offer registry being loaded at runtime] → The
  reward section is omitted gracefully when no offer is registered; the command
  never fails because of it.
- [A long board line for future multi-stage quests] → The board one-liner
  renders only the first-stage objective; full detail stays in `guild show`.
- [Broad error handling hides real bugs] → `guild show` catches exactly the
  documented exceptions (`QuestNotFound`, `QuestDataError`, `GuildDataError`)
  instead of the broad `except Exception` pattern used by the current
  `CmdGuildLog`.
